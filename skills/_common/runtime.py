from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_INPUT_FIELDS = [
    "moduleName",
    "workflowNames",
    "convertedRoots",
    "legacyBackendRoots",
    "legacyFrontendRoots",
    "baseUrl",
    "startUrl",
]


@dataclass
class SkillContext:
    payload: dict[str, Any]
    module_name: str
    run_id: str
    artifacts_root: Path
    out_dir: Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_payload(input_path: str) -> dict[str, Any]:
    return json.loads(Path(input_path).read_text(encoding="utf-8"))


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("runId", f"run-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}")
    normalized.setdefault("strictModuleOnly", True)
    normalized.setdefault("strictAIGeneration", True)
    if "strictAiGeneration" not in normalized and "strictAIGeneration" in normalized:
        normalized["strictAiGeneration"] = normalized["strictAIGeneration"]
    if "strictAIGeneration" not in normalized and "strictAiGeneration" in normalized:
        normalized["strictAIGeneration"] = normalized["strictAiGeneration"]
    normalized.setdefault("enableUserInputPrompting", True)

    for key in ["workflowNames", "convertedRoots", "legacyBackendRoots", "legacyFrontendRoots", "expectedEndUrls", "controllerHints", "viewHints", "keywords"]:
        val = normalized.get(key)
        if val is None:
            normalized[key] = []
        elif isinstance(val, str):
            normalized[key] = [x.strip() for x in val.split(",") if x.strip()]

    return normalized


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_INPUT_FIELDS:
        val = payload.get(key)
        if val is None:
            errors.append(f"Missing required field: {key}")
            continue
        if isinstance(val, str) and not val.strip():
            errors.append(f"Empty required field: {key}")
        if isinstance(val, list) and len(val) == 0:
            errors.append(f"Empty required list: {key}")

    for root_key in ["convertedRoots", "legacyBackendRoots", "legacyFrontendRoots"]:
        for root in payload.get(root_key, []):
            if not Path(str(root)).exists():
                errors.append(f"Path does not exist in {root_key}: {root}")

    return errors


def make_context(payload: dict[str, Any], artifacts_root: str, skill_name: str) -> SkillContext:
    module_name = str(payload.get("moduleName") or "__missing-module__")
    run_id = str(payload.get("runId") or "__missing-run__")
    out_dir = Path(artifacts_root) / module_name / run_id / skill_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return SkillContext(
        payload=payload,
        module_name=module_name,
        run_id=run_id,
        artifacts_root=Path(artifacts_root),
        out_dir=out_dir,
    )


def write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path.as_posix()


def write_result(
    ctx: SkillContext,
    skill_name: str,
    status: str,
    summary: str,
    artifacts: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
    recommendations: list[dict[str, Any]] | None = None,
) -> str:
    result = {
        "skillName": skill_name,
        "status": status,
        "startedAt": now_iso(),
        "endedAt": now_iso(),
        "summary": summary,
        "metrics": metrics or {},
        "artifacts": artifacts or [],
        "findings": findings or [],
        "recommendations": recommendations or [],
        "resultContractVersion": "1.0",
    }
    result_path = ctx.out_dir / "result.json"
    write_json(result_path, result)
    return result_path.as_posix()
