#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def title_case_module(module_name: str) -> str:
    text = module_name.replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Module"
    return " ".join(part.capitalize() for part in text.split())


def to_module_slug(module_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", module_name.strip().lower()).strip("-")
    return slug or "module"


def sample(values: list[str], max_items: int = 25) -> list[str]:
    return values[:max_items]


def infer_flows_from_urls(urls: list[str]) -> list[str]:
    flows: list[str] = []
    for url in urls:
        lower = url.lower()
        if "load" in lower:
            flows.append("Load module data")
        elif "view" in lower or "list" in lower:
            flows.append("View module records")
        elif "save" in lower or "update" in lower:
            flows.append("Save or update module data")
        elif "submit" in lower:
            flows.append("Submit workflow for downstream processing")
        elif "validate" in lower:
            flows.append("Validate input and business rules")
        elif "delete" in lower:
            flows.append("Delete module records")
    if not flows:
        flows = ["Load module data", "Edit module data", "Submit module workflow"]
    return dedupe(flows)


def infer_rules_from_touchpoints(db_touchpoints: list[str], has_js: bool) -> list[str]:
    rules: list[str] = []
    if db_touchpoints:
        rules.append("Persistence contracts and field mappings must preserve legacy behavior")
    if has_js:
        rules.append("Client-side validation and state transitions must remain consistent")
    rules.append("Error handling and response contracts must preserve user-visible behavior")
    rules.append("Security/session behavior must remain compatible with legacy expectations")
    return dedupe(rules)


def build_dependencies(scope: dict[str, Any]) -> list[str]:
    deps: list[str] = []
    for db in scope.get("dbTouchpoints", [])[:6]:
        if "." in db:
            deps.append(f"Database package/table: {db}")
    for path in scope.get("csharpFiles", [])[:8]:
        p = path.lower()
        if "controller" in p:
            deps.append("Converted web controllers")
        if "service" in p:
            deps.append("Converted services")
        if "repository" in p:
            deps.append("Converted repositories")
    return dedupe(deps)[:12]


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def parse_test_counts(text: str) -> dict[str, int]:
    content = text or ""

    total = _extract_int(content, [r"Total tests:\s*(\d+)", r"total\s*=\s*(\d+)"])
    passed = _extract_int(content, [r"Passed:\s*(\d+)", r"passed\s*=\s*(\d+)"])
    failed = _extract_int(content, [r"Failed:\s*(\d+)", r"failed\s*=\s*(\d+)"])
    skipped = _extract_int(content, [r"Skipped:\s*(\d+)", r"warnings\s*=\s*(\d+)"])

    # Pytest summary support (example: "2 failed, 5 passed, 1 skipped in 0.52s")
    if passed == 0:
        passed = _extract_int(content, [r"(\d+)\s+passed"])
    if failed == 0:
        failed = _extract_int(content, [r"(\d+)\s+failed", r"(\d+)\s+errors?"])
    if skipped == 0:
        skipped = _extract_int(content, [r"(\d+)\s+skipped", r"(\d+)\s+warnings?"])

    if total == 0:
        collected = _extract_int(content, [r"collected\s+(\d+)\s+items?"])
        if collected > 0:
            total = collected

    if total == 0 and (passed or failed):
        total = passed + failed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "warnings": skipped,
    }


def _extract_int(content: str, patterns: list[str]) -> int:
    for pattern in patterns:
        m = re.search(pattern, content, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                continue
    return 0


def previous_run_id(artifacts_root: Path, module_name: str, run_id: str) -> str:
    module_root = artifacts_root / module_name
    if not module_root.exists():
        return ""

    run_dirs = sorted([d.name for d in module_root.iterdir() if d.is_dir()])
    prefix_match = re.match(r"^([A-Za-z]+)-", run_id or "")
    if prefix_match:
        prefix = prefix_match.group(1).lower() + "-"
        same_prefix = [r for r in run_dirs if r.lower().startswith(prefix)]
        if same_prefix:
            run_dirs = same_prefix

    if run_id not in run_dirs:
        return run_dirs[-1] if run_dirs else ""
    idx = run_dirs.index(run_id)
    if idx <= 0:
        return ""
    return run_dirs[idx - 1]


def aggregate_run_failures(run_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in run_results:
        status = str(result.get("status", "")).lower()
        if status == "passed":
            continue
        skill = str(result.get("skillName") or result.get("skill") or "unknown-skill")
        summary = str(result.get("summary", ""))
        findings.append(
            {
                "type": "SkillFailure",
                "scenario": skill,
                "message": f"{skill} reported non-passing status.",
                "likelyCause": summary or "Skill execution reported failures.",
                "evidence": f"skill={skill}; status={status}",
                "severity": "high" if status == "failed" else "medium",
                "status": "open",
                "confidence": 0.8,
            }
        )
    return findings
