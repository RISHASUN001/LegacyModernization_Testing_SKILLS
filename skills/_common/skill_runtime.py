#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

RESULT_CONTRACT_VERSION = "2.0"
_MAX_SCAN_FILES = 2000
_EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".vs",
    "node_modules",
    "bin",
    "obj",
    "__pycache__",
    "artifacts",
    "data",
    ".venv",
    "venv",
}
_TEXT_FILE_SUFFIXES = {
    ".java",
    ".jsp",
    ".jspx",
    ".js",
    ".ts",
    ".xml",
    ".properties",
    ".yml",
    ".yaml",
    ".json",
    ".config",
    ".ini",
    ".cs",
    ".cshtml",
    ".razor",
    ".sql",
    ".txt",
    ".md",
}
_URL_RE = re.compile(r"(/[-A-Za-z0-9_./]+(?:\.do|\.jsp|\.action|\.aspx|\.json|\.html|\.htm)?)")
_DB_TOUCHPOINT_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,}\.[A-Z][A-Z0-9_]{2,})\b")
_SQL_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Z_][A-Z0-9_]{2,})\b", re.IGNORECASE)
_ROUTE_PREFIX_RE = re.compile(r"\[\s*Route\s*\(\s*\"([^\"]+)\"\s*\)\s*\]", re.IGNORECASE)
_HTTP_ROUTE_RE = re.compile(r"\[\s*Http(?:Get|Post|Put|Delete|Patch|Head|Options)\s*\(\s*\"([^\"]*)\"\s*\)\s*\]", re.IGNORECASE)

PROVENANCE_TYPES = {
    "code-evidence",
    "inferred",
    "fallback",
    "lessons-learned",
    "flow-derived",
    "risk-derived",
    "lessons-derived",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def make_provenance(
    provenance_type: str,
    *,
    sources: list[str] | None = None,
    confidence: float = 0.5,
    unknowns: list[str] | None = None,
) -> dict[str, Any]:
    p_type = provenance_type if provenance_type in PROVENANCE_TYPES else "inferred"
    bounded_confidence = max(0.0, min(1.0, float(confidence)))
    return {
        "type": p_type,
        "sources": sources or [],
        "confidence": bounded_confidence,
        "unknowns": unknowns or [],
    }


def profile_for_run(run_id: str) -> str:
    m = re.search(r"(\d+)$", run_id or "")
    if m and int(m.group(1)) >= 2:
        return "improved"
    return "baseline"


def get_payload_value(payload: dict[str, Any], dotted_key: str) -> Any:
    current: Any = payload
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(text) and text.startswith("<") and text.endswith(">")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_read_text(path: Path, max_chars: int = 500_000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if len(content) > max_chars:
        return content[:max_chars]
    return content


def _load_required_inputs(spec: dict[str, Any], script_path: Path) -> list[str]:
    from_spec = spec.get("requiredInputs", [])
    if from_spec:
        return [str(x) for x in from_spec]

    config_path = script_path.parent / "config.json"
    if not config_path.exists():
        return []

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    return [str(x) for x in config.get("requiredInputs", [])]


def _build_terms(payload: dict[str, Any], module_name: str) -> list[str]:
    hints = payload.get("moduleHints") or {}
    keywords = hints.get("keywords") if isinstance(hints, dict) else []
    terms = [module_name] + [str(k) for k in (keywords or [])]
    term_parts: list[str] = []
    for term in terms:
        cleaned = term.strip().lower()
        if not cleaned:
            continue
        term_parts.append(cleaned)
        term_parts.extend([p for p in re.split(r"[^a-z0-9]+", cleaned) if p])
    return _dedupe([t for t in term_parts if len(t) >= 2])


def _classify_file(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".java"):
        return "java"
    if lower.endswith(".jsp") or lower.endswith(".jspx"):
        return "jsp"
    if lower.endswith(".js") or lower.endswith(".ts"):
        return "js"
    if any(lower.endswith(ext) for ext in [".xml", ".properties", ".yml", ".yaml", ".config", ".ini", ".json"]):
        return "config"
    if lower.endswith(".cs") or lower.endswith(".cshtml") or lower.endswith(".razor"):
        if "test" in lower or "spec" in lower:
            return "test"
        return "csharp"
    return "other"


def _iter_candidate_files(base: Path) -> list[Path]:
    files: list[Path] = []
    if not base.exists():
        return files

    if base.is_file():
        return [base]

    for root, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        for name in names:
            p = Path(root) / name
            try:
                if p.stat().st_size > 1_000_000:
                    continue
            except OSError:
                continue
            files.append(p)
            if len(files) >= _MAX_SCAN_FILES:
                return files
    return files


def _valid_url_candidate(value: str) -> bool:
    if not value.startswith("/"):
        return False
    if value.startswith("//"):
        return False
    if "/Users/" in value or value.startswith("/Users"):
        return False
    if value.startswith("/.") or value.startswith("/../"):
        return False
    if len(value) > 120:
        return False
    if not re.match(r"^/[A-Za-z0-9][A-Za-z0-9/_.-]*$", value):
        return False
    trimmed = value.strip("/")
    if len(trimmed) < 3:
        return False
    if not re.search(r"[A-Za-z]", trimmed):
        return False
    if trimmed.isupper() and "/" not in trimmed and "-" not in trimmed and "_" not in trimmed:
        return False
    return True


def _normalize_route_template(template: str) -> str:
    route = (template or "").strip()
    if not route:
        return ""
    route = route.replace("[controller]", "controller")
    route = route.replace("[action]", "action")
    route = route.replace("[area]", "area")
    route = route.strip("/")
    if not route:
        return "/"
    return f"/{route}"


def _extract_controller_routes(text: str) -> list[str]:
    if "Controller" not in text:
        return []

    prefixes = [_normalize_route_template(x) for x in _ROUTE_PREFIX_RE.findall(text)]
    prefixes = [p for p in prefixes if p]
    if not prefixes:
        prefixes = [""]

    routes: list[str] = []
    for http_route in _HTTP_ROUTE_RE.findall(text):
        normalized = _normalize_route_template(http_route)
        for prefix in prefixes:
            if normalized == "/":
                combined = prefix or "/"
            elif not normalized:
                combined = prefix or "/"
            elif prefix and prefix != "/":
                combined = f"{prefix.rstrip('/')}/{normalized.lstrip('/')}"
            else:
                combined = normalized
            routes.append(combined if combined.startswith("/") else f"/{combined}")

    return _dedupe([r for r in routes if _valid_url_candidate(r) or r == "/"])


def resolve_module_scope(payload: dict[str, Any], module_name: str) -> dict[str, Any]:
    roots: list[Path] = []
    for key in ("legacySourceRoot", "convertedSourceRoot"):
        raw = str(payload.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.exists():
            roots.append(p)
            if p.is_file() and p.suffix.lower() in {".sln", ".slnx", ".csproj", ".vbproj"}:
                roots.append(p.parent)

    hints = payload.get("moduleHints") if isinstance(payload.get("moduleHints"), dict) else {}
    related_folders = hints.get("relatedFolders") if isinstance(hints, dict) else []
    known_urls = [str(u).strip() for u in ((hints.get("knownUrls") if isinstance(hints, dict) else []) or []) if str(u).strip()]
    terms = _build_terms(payload, module_name)

    hint_paths: list[Path] = []
    for raw_hint in related_folders or []:
        hint = str(raw_hint).strip()
        if not hint:
            continue
        hint_path = Path(hint)
        if hint_path.is_absolute() and hint_path.exists():
            hint_paths.append(hint_path)
            continue
        for root in roots:
            candidate = root / hint
            if candidate.exists():
                hint_paths.append(candidate)

    hint_files: list[Path] = []
    for hint_path in hint_paths:
        hint_files.extend(_iter_candidate_files(hint_path))

    hint_set = {f.resolve().as_posix() for f in hint_files}

    heuristic_files: list[Path] = []
    for root in roots:
        for candidate in _iter_candidate_files(root):
            if len(hint_set) + len(heuristic_files) >= _MAX_SCAN_FILES:
                break
            full = candidate.resolve().as_posix()
            if full in hint_set:
                continue
            lower = full.lower()
            if any(term in lower for term in terms):
                heuristic_files.append(candidate)

    selected = hint_files + heuristic_files
    selected = selected[:_MAX_SCAN_FILES]

    classified: dict[str, list[str]] = {
        "javaFiles": [],
        "jspFiles": [],
        "jsFiles": [],
        "configFiles": [],
        "csharpFiles": [],
        "testFiles": [],
        "otherFiles": [],
    }

    urls: list[str] = []
    db_touchpoints: list[str] = []

    for file_path in selected:
        normalized = file_path.resolve().as_posix()
        kind = _classify_file(normalized)
        if kind == "java":
            classified["javaFiles"].append(normalized)
        elif kind == "jsp":
            classified["jspFiles"].append(normalized)
        elif kind == "js":
            classified["jsFiles"].append(normalized)
        elif kind == "config":
            classified["configFiles"].append(normalized)
        elif kind == "csharp":
            classified["csharpFiles"].append(normalized)
        elif kind == "test":
            classified["testFiles"].append(normalized)
        else:
            classified["otherFiles"].append(normalized)

        if file_path.suffix.lower() not in _TEXT_FILE_SUFFIXES:
            continue

        text = _safe_read_text(file_path)
        if not text:
            continue

        urls.extend(match.group(1) for match in _URL_RE.finditer(text))
        if kind == "csharp":
            urls.extend(_extract_controller_routes(text))
        db_touchpoints.extend(match.group(1) for match in _DB_TOUCHPOINT_RE.finditer(text))
        db_touchpoints.extend(
            match.group(1).upper()
            for match in _SQL_TABLE_RE.finditer(text)
            if "_" in match.group(1) or match.group(1).upper().startswith(("TBL", "PKG", "VW"))
        )

    urls.extend(known_urls)
    filtered_urls: list[str] = []
    for url in urls:
        if not _valid_url_candidate(url):
            continue
        lower = url.lower()
        if any(lower.endswith(ext) for ext in (".cs", ".java", ".dll", ".exe", ".pdb", ".json", ".css", ".js", ".ts", ".md")):
            continue
        if "password" in lower and url not in known_urls:
            continue
        if "legacymodernization" in lower:
            continue
        if any(lower.endswith(ext) for ext in (".do", ".action", ".jsp", ".html", ".htm", ".cshtml")):
            filtered_urls.append(url)
            continue
        if lower.startswith("/api/"):
            filtered_urls.append(url)
            continue
        if any(term in lower for term in terms):
            filtered_urls.append(url)
            continue
        if url in known_urls:
            filtered_urls.append(url)

    filtered_db = []
    for touchpoint in db_touchpoints:
        upper = touchpoint.upper()
        if "_" in upper and "." in upper:
            filtered_db.append(upper)
            continue
        if upper.startswith(("PKG", "SP_", "PROC_", "TBL_", "VW_")):
            filtered_db.append(upper)

    urls = _dedupe(sorted(filtered_urls))[:150]
    db_touchpoints = _dedupe(sorted(filtered_db))[:150]

    return {
        **classified,
        "urls": urls,
        "dbTouchpoints": db_touchpoints,
        "roots": [r.resolve().as_posix() for r in roots],
        "terms": terms,
        "hintPaths": [p.resolve().as_posix() for p in hint_paths],
        "totalSelectedFiles": len(selected),
    }


@dataclass
class SkillContext:
    spec: dict[str, Any]
    payload: dict[str, Any]
    module_name: str
    run_id: str
    artifacts_root: Path
    out_dir: Path
    result_path: Path
    started_at: str
    input_path: Path
    profile: str
    _artifacts: list[str] = field(default_factory=list)
    _scope_cache: dict[str, Any] | None = None

    def add_artifact(self, path: Path | str) -> str:
        artifact = Path(path).resolve().as_posix()
        if artifact not in self._artifacts:
            self._artifacts.append(artifact)
        return artifact

    @property
    def artifacts(self) -> list[str]:
        return list(self._artifacts)

    def write_json(self, rel_path: str, payload: Any) -> str:
        target = self.out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.add_artifact(target)

    def write_text(self, rel_path: str, content: str) -> str:
        target = self.out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return self.add_artifact(target)

    def write_placeholder_png(self, rel_path: str) -> str:
        target = self.out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AApMBgU8R4X0AAAAASUVORK5CYII="
        )
        target.write_bytes(raw)
        return self.add_artifact(target)

    def get(self, key: str, default: Any = None) -> Any:
        return get_payload_value(self.payload, key) if "." in key else self.payload.get(key, default)

    def resolve_scope(self) -> dict[str, Any]:
        if self._scope_cache is None:
            self._scope_cache = resolve_module_scope(self.payload, self.module_name)
        return self._scope_cache

    def load_artifact_json(self, skill_name: str, filename: str) -> dict[str, Any] | None:
        candidate = self.artifacts_root / self.module_name / self.run_id / skill_name / filename
        if not candidate.exists():
            return None
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            return None

    def iter_run_results(self) -> list[dict[str, Any]]:
        run_root = self.artifacts_root / self.module_name / self.run_id
        results: list[dict[str, Any]] = []
        if not run_root.exists():
            return results
        for path in run_root.glob("*/result.json"):
            if path.resolve() == self.result_path.resolve():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    results.append(data)
            except Exception:
                continue
        return results

    def run_command(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 180,
        cwd: str | None = None,
        log_name: str | None = None,
    ) -> dict[str, Any]:
        started = time.time()
        stdout = ""
        stderr = ""
        return_code = -1
        timed_out = False
        command_text = " ".join(command)
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return_code = completed.returncode
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except FileNotFoundError as ex:
            stderr = str(ex)
            return_code = 127
        except subprocess.TimeoutExpired as ex:
            timed_out = True
            stdout = ex.stdout or ""
            stderr = (ex.stderr or "") + "\nTimed out"
            return_code = 124
        except Exception as ex:  # pragma: no cover
            stderr = str(ex)
            return_code = 1

        duration = round(time.time() - started, 3)
        log_path = ""
        if log_name:
            log_lines = [
                f"command: {command_text}",
                f"returnCode: {return_code}",
                f"timedOut: {timed_out}",
                f"durationSeconds: {duration}",
                "",
                "--- stdout ---",
                stdout,
                "",
                "--- stderr ---",
                stderr,
            ]
            log_path = self.write_text(log_name, "\n".join(log_lines))

        return {
            "command": command,
            "returnCode": return_code,
            "success": return_code == 0 and not timed_out,
            "timedOut": timed_out,
            "durationSeconds": duration,
            "stdout": stdout,
            "stderr": stderr,
            "logPath": log_path,
        }


def _write_result(
    *,
    ctx: SkillContext,
    status: str,
    summary: str,
    metrics: dict[str, Any] | None,
    findings: list[dict[str, Any]] | list[Any] | None,
    recommendations: list[dict[str, Any]] | list[Any] | None,
    status_reason: str | None = None,
    preflight: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
    provenance_summary: dict[str, Any] | None = None,
) -> None:
    result: dict[str, Any] = {
        "skillName": ctx.spec["name"],
        "stage": ctx.spec["stage"],
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "status": status,
        "startedAt": ctx.started_at,
        "endedAt": now_iso(),
        "summary": summary,
        "metrics": metrics or {},
        "artifacts": [ctx.result_path.as_posix(), *ctx.artifacts],
        "findings": findings or [],
        "recommendations": recommendations or [],
        "resultContractVersion": RESULT_CONTRACT_VERSION,
    }
    if status_reason:
        result["statusReason"] = status_reason
    if preflight is not None:
        result["preflight"] = preflight
    if trace is not None:
        result["trace"] = trace
    if provenance_summary is not None:
        result["provenanceSummary"] = provenance_summary

    ctx.result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(ctx.result_path.as_posix())


ExecuteFn = Callable[[SkillContext], dict[str, Any]]


def run_python_skill(spec: dict[str, Any], execute_fn: ExecuteFn | None = None) -> None:
    parser = argparse.ArgumentParser(description=f"Run {spec['name']}")
    parser.add_argument("--input", default="module-run-input.json")
    parser.add_argument("--artifacts-root", default="artifacts")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--module", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    script_path = Path(sys.argv[0]).resolve()
    input_path = Path(args.input)
    payload = _read_json(input_path) if input_path.exists() else {}

    module_name = str(args.module or payload.get("moduleName") or payload.get("module") or "").strip()
    run_id = str(args.run_id or payload.get("runId") or payload.get("run_id") or "").strip()

    artifacts_root = Path(args.output_dir or args.artifacts_root)
    safe_module = module_name or "__missing-module__"
    safe_run = run_id or "__missing-run__"
    out_dir = artifacts_root / safe_module / safe_run / spec["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "result.json"

    started = now_iso()
    ctx = SkillContext(
        spec=spec,
        payload=payload,
        module_name=safe_module,
        run_id=safe_run,
        artifacts_root=artifacts_root,
        out_dir=out_dir,
        result_path=result_path,
        started_at=started,
        input_path=input_path,
        profile=profile_for_run(run_id or ""),
    )

    missing_required: list[str] = []
    if not module_name or _is_placeholder(module_name):
        missing_required.append("moduleName")
    if not run_id or _is_placeholder(run_id):
        missing_required.append("runId")

    required_inputs = _load_required_inputs(spec, script_path)
    for key in required_inputs:
        value = get_payload_value(payload, key)
        if not is_present(value) or _is_placeholder(value):
            missing_required.append(key)

    if missing_required:
        _write_result(
            ctx=ctx,
            status="failed",
            summary="Input validation failed. Required run-input fields are missing.",
            metrics={"missingRequiredInputs": len(_dedupe(missing_required))},
            findings=[
                {
                    "type": "InputValidationError",
                    "scenario": "Skill input validation",
                    "message": f"Missing required inputs: {', '.join(_dedupe(missing_required))}",
                    "likelyCause": "Run input JSON is incomplete for this skill.",
                    "evidence": f"requiredInputs={required_inputs}",
                    "severity": "high",
                    "status": "open",
                    "confidence": 0.98,
                }
            ],
            recommendations=[
                {
                    "message": "Populate required inputs in module-run-input.json before re-running.",
                    "priority": "high",
                    "evidence": "Skill contract validation failed before execution.",
                }
            ],
            status_reason="input-validation-failed",
        )
        return

    # swap strict values once validated
    ctx.module_name = module_name
    ctx.run_id = run_id
    ctx.out_dir = artifacts_root / module_name / run_id / spec["name"]
    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    ctx.result_path = ctx.out_dir / "result.json"

    try:
        if execute_fn is not None:
            outcome = execute_fn(ctx) or {}
        else:
            profiles = spec.get("profiles")
            if not isinstance(profiles, dict):
                raise ValueError("No execute_fn provided and spec.profiles missing")
            profile = profiles.get(ctx.profile, profiles.get("baseline", {}))
            outcome = {
                "status": profile.get("status", "passed"),
                "summary": profile.get("summary", "Skill completed."),
                "metrics": profile.get("metrics", {}),
                "findings": profile.get("findings", []),
                "recommendations": profile.get("recommendations", []),
            }
            for rel, content in (profile.get("extra") or {}).items():
                if content == "__PNG__":
                    ctx.write_placeholder_png(str(rel))
                elif isinstance(content, str):
                    ctx.write_text(str(rel), content)
                else:
                    ctx.write_json(str(rel), content)

        _write_result(
            ctx=ctx,
            status=str(outcome.get("status", "passed")),
            summary=str(outcome.get("summary", "Skill completed.")),
            metrics=outcome.get("metrics", {}),
            findings=outcome.get("findings", []),
            recommendations=outcome.get("recommendations", []),
            status_reason=outcome.get("statusReason"),
            preflight=outcome.get("preflight"),
            trace=outcome.get("trace"),
            provenance_summary=outcome.get("provenanceSummary"),
        )
    except Exception as ex:
        _write_result(
            ctx=ctx,
            status="failed",
            summary=f"Skill execution failed: {ex}",
            metrics={"degradedMode": False},
            findings=[
                {
                    "type": "SkillExecutionError",
                    "scenario": "Skill callback execution",
                    "message": str(ex),
                    "likelyCause": "Unhandled exception in skill script.",
                    "evidence": "Runtime exception captured by shared skill runtime.",
                    "severity": "high",
                    "status": "open",
                    "confidence": 0.9,
                }
            ],
            recommendations=[
                {
                    "message": "Inspect skill script and rerun with valid inputs.",
                    "priority": "high",
                    "evidence": "Shared runtime error handling path executed.",
                }
            ],
            status_reason="exception",
            trace={"exception": str(ex), "script": script_path.as_posix()},
        )
