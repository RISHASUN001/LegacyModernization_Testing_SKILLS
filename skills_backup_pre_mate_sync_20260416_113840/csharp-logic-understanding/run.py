#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SKILL_NAME = "csharp-logic-understanding"


@dataclass
class Context:
    module_name: str
    run_id: str
    out_dir: Path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path.as_posix()


def write_result(
    ctx: Context,
    status: str,
    summary: str,
    artifacts: list[str],
    metrics: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> str:
    result = {
        "skillName": SKILL_NAME,
        "status": status,
        "summary": summary,
        "metrics": metrics or {},
        "artifacts": artifacts,
        "findings": findings or []
    }
    result_path = ctx.out_dir / "result.json"
    write_json(result_path, result)
    return result_path.as_posix()


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("moduleName", "")
    payload.setdefault("runId", "run-001")
    payload.setdefault("workflowNames", [])
    payload.setdefault("startUrl", "")
    payload.setdefault("expectedEndUrls", [])
    payload.setdefault("strictAIGeneration", True)
    return payload


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("moduleName"):
        errors.append("moduleName is required")
    return errors


def make_context(payload: dict[str, Any], artifacts_root: Path) -> Context:
    module_name = str(payload["moduleName"])
    run_id = str(payload["runId"])
    out_dir = artifacts_root / module_name / run_id / SKILL_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    return Context(module_name=module_name, run_id=run_id, out_dir=out_dir)


def build_fallback_logic(
    module_name: str,
    workflow_names: list[str],
    discovery: dict[str, Any]
) -> dict[str, Any]:
    module_map = discovery.get("moduleMap", {})
    route_map = discovery.get("routeMap", {}).get("items", [])
    sql_map = discovery.get("sqlMap", {}).get("items", [])
    table_usage = discovery.get("tableUsage", {}).get("tables", [])

    workflows: list[dict[str, Any]] = []
    for wf in workflow_names:
        wf_lower = str(wf).lower()

        wf_routes: list[str] = []
        wf_controllers: list[str] = []
        wf_views = module_map.get("views", [])
        wf_tables: list[str] = []

        for item in route_map:
            for action in item.get("actions", []):
                joined = f"{action.get('action', '')} {action.get('route', '')}".lower()
                if wf_lower in joined or wf_lower in item.get("file", "").lower():
                    if action.get("route"):
                        wf_routes.append(action["route"])
                    elif action.get("action"):
                        wf_routes.append(action["action"])
                    if item.get("controller"):
                        wf_controllers.append(item["controller"])

        for item in sql_map:
            if wf_lower in item.get("file", "").lower():
                wf_tables.extend(item.get("tables", []))

        workflows.append({
            "name": wf,
            "entryPoint": wf_routes[0] if wf_routes else "",
            "likelyRoutes": list(dict.fromkeys(wf_routes)),
            "controllers": list(dict.fromkeys(wf_controllers)) or module_map.get("controllers", []),
            "views": wf_views,
            "decisionBranches": [
                "GET/POST split may exist based on controller actions",
                "Form submission and result rendering paths should be verified downstream"
            ],
            "validations": [
                "Model binding and criteria validation should be checked from controller/view flow"
            ],
            "dbTouchpoints": [item.get("file", "") for item in sql_map],
            "tables": list(dict.fromkeys(wf_tables)) or table_usage,
            "outcome": "Workflow understanding generated from discovery artifacts; refine with AI provider if configured.",
            "notes": [
                "This is a fallback summary structure.",
                "Use AI provider integration to improve narrative quality if available."
            ]
        })

    return {
        "moduleName": module_name,
        "source": "csharp",
        "modulePurpose": f"Modernized module analysis for {module_name}.",
        "workflows": workflows
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=SKILL_NAME)
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    payload = normalize_payload(load_json(Path(args.input)))
    errors = validate_payload(payload)
    ctx = make_context(payload, Path(args.artifacts_root))

    if errors:
        result_path = write_result(
            ctx,
            status="failed",
            summary="Input validation failed for C# logic understanding.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}]
        )
        print(result_path)
        return 1

    artifacts_root = Path(args.artifacts_root)
    base = artifacts_root / ctx.module_name / ctx.run_id / "csharp-module-discovery"

    discovery = {
        "moduleMap": load_json(base / "csharp-module-map.json") if (base / "csharp-module-map.json").exists() else {},
        "routeMap": load_json(base / "controller-route-map.json") if (base / "controller-route-map.json").exists() else {},
        "sqlMap": load_json(base / "csharp-sql-map.json") if (base / "csharp-sql-map.json").exists() else {},
        "tableUsage": load_json(base / "csharp-table-usage.json") if (base / "csharp-table-usage.json").exists() else {},
        "scope": load_json(base / "scoped-file-relevance.json") if (base / "scoped-file-relevance.json").exists() else {}
    }

    # Plug AI provider here later if desired.
    logic = build_fallback_logic(
        module_name=ctx.module_name,
        workflow_names=list(payload["workflowNames"]),
        discovery=discovery
    )

    output_path = write_json(ctx.out_dir / "csharp-logic-summary.json", logic)

    result_path = write_result(
        ctx,
        status="passed",
        summary=f"Built C# logic understanding for {len(payload['workflowNames'])} workflows.",
        artifacts=[output_path],
        metrics={
            "workflowCount": len(payload["workflowNames"]),
            "routesAnalyzed": len(discovery["routeMap"].get("items", [])),
            "sqlFilesAnalyzed": len(discovery["sqlMap"].get("items", [])),
            "tablesFound": len(discovery["tableUsage"].get("tables", []))
        }
    )

    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())