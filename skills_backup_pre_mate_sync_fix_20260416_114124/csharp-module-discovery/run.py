#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


SKILL_NAME = "csharp-module-discovery"


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
    payload.setdefault("convertedRoots", [])
    payload.setdefault("controllerHints", [])
    payload.setdefault("viewHints", [])
    payload.setdefault("keywords", [])
    payload.setdefault("startUrl", "")
    payload.setdefault("strictModuleOnly", True)
    return payload


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("moduleName"):
        errors.append("moduleName is required")
    if not payload.get("convertedRoots"):
        errors.append("convertedRoots is required")
    return errors


def make_context(payload: dict[str, Any], artifacts_root: Path) -> Context:
    module_name = str(payload["moduleName"])
    run_id = str(payload["runId"])
    out_dir = artifacts_root / module_name / run_id / SKILL_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    return Context(module_name=module_name, run_id=run_id, out_dir=out_dir)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_controller_actions(text: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []

    class_match = re.search(r"class\s+([A-Za-z0-9_]+Controller)\b", text)
    controller_name = class_match.group(1) if class_match else ""

    route_attrs = re.findall(r'\[Http(Get|Post|Put|Delete|Patch)(?:\("([^"]*)"\))?\]', text)
    method_matches = re.findall(
        r'(?:public|private|protected)\s+(?:async\s+)?(?:Task<[^>]+>|Task|IActionResult|ActionResult|JsonResult|ViewResult)\s+([A-Za-z0-9_]+)\s*\(',
        text
    )

    for idx, method_name in enumerate(method_matches):
        route = ""
        verb = ""
        if idx < len(route_attrs):
            verb = route_attrs[idx][0].upper()
            route = route_attrs[idx][1]
        actions.append({
            "controller": controller_name,
            "action": method_name,
            "verb": verb,
            "route": route
        })

    return actions


def extract_sql_blocks(text: str) -> list[str]:
    blocks: list[str] = []

    # verbatim strings with SELECT/INSERT/UPDATE/DELETE
    verbatim = re.findall(r'@"(.*?)"', text, flags=re.DOTALL)
    normal = re.findall(r'"(.*?)"', text, flags=re.DOTALL)

    candidates = verbatim + normal
    for block in candidates:
        cleaned = block.replace("\\r", " ").replace("\\n", " ").strip()
        upper = cleaned.upper()
        if any(k in upper for k in ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "FROM ", "JOIN "]):
            if len(cleaned) > 20:
                blocks.append(cleaned)

    return list(dict.fromkeys(blocks))


def extract_tables(sql_blocks: list[str]) -> list[str]:
    tables: list[str] = []
    pattern = re.compile(r'\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Za-z0-9_.$]+)', re.IGNORECASE)
    for sql in sql_blocks:
        for match in pattern.findall(sql):
            tables.append(match.strip())
    return list(dict.fromkeys(tables))


def score_file(
    path: Path,
    text: str,
    module_name: str,
    workflow_names: list[str],
    controller_hints: list[str],
    view_hints: list[str],
    keywords: list[str],
    start_url: str,
) -> tuple[int, list[str], str]:
    score = 0
    reasons: list[str] = []
    lower_text = text.lower()
    lower_name = path.name.lower()

    module_tokens = [t for t in re.split(r'[^a-zA-Z0-9]+', module_name.lower()) if t]
    workflow_tokens = [
        tok
        for wf in workflow_names
        for tok in re.split(r'[^a-zA-Z0-9]+', str(wf).lower())
        if tok and len(tok) >= 3
    ]
    hint_tokens = [h.lower() for h in controller_hints + view_hints + keywords if h]
    url_tokens = [tok for tok in re.split(r'[^a-zA-Z0-9]+', start_url.lower()) if len(tok) >= 3]

    for token in module_tokens + workflow_tokens + hint_tokens + url_tokens:
        if token in lower_name:
            score += 3
            reasons.append(f"name matched token '{token}'")
        if token in lower_text:
            score += 2
            reasons.append(f"content matched token '{token}'")

    if lower_name.endswith("controller.cs"):
        score += 2
        reasons.append("controller file")
    if lower_name.endswith(".cshtml"):
        score += 2
        reasons.append("view file")
    if "service" in lower_name:
        score += 1
        reasons.append("service-like file")
    if "repo" in lower_name or "repository" in lower_name:
        score += 1
        reasons.append("repository-like file")

    if score >= 8:
        confidence = "high"
    elif score >= 4:
        confidence = "medium"
    elif score >= 1:
        confidence = "low"
    else:
        confidence = "exclude"

    return score, list(dict.fromkeys(reasons)), confidence


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
            summary="Input validation failed for C# module discovery.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
            metrics={"validationErrors": len(errors)}
        )
        print(result_path)
        return 1

    module_name = str(payload["moduleName"])
    workflow_names = list(payload["workflowNames"])
    controller_hints = list(payload["controllerHints"])
    view_hints = list(payload["viewHints"])
    keywords = list(payload["keywords"])
    start_url = str(payload["startUrl"])
    strict_module_only = bool(payload["strictModuleOnly"])

    candidate_files: list[Path] = []
    for root_str in payload["convertedRoots"]:
        root = Path(root_str)
        if root.is_dir():
            candidate_files.extend(root.rglob("*.cs"))
            candidate_files.extend(root.rglob("*.cshtml"))

    candidate_files = sorted({p.resolve() for p in candidate_files if p.is_file()}, key=lambda p: p.as_posix())

    included_files: list[Path] = []
    scoped_relevance: list[dict[str, Any]] = []

    route_items: list[dict[str, Any]] = []
    sql_items: list[dict[str, Any]] = []
    all_tables: list[str] = []

    controllers: list[str] = []
    views: list[str] = []
    services: list[str] = []
    repositories: list[str] = []

    for file_path in candidate_files:
        text = read_text(file_path)
        score, reasons, confidence = score_file(
            file_path,
            text,
            module_name,
            workflow_names,
            controller_hints,
            view_hints,
            keywords,
            start_url,
        )

        include = confidence != "exclude" if strict_module_only else score >= 1

        role = "other"
        lower_name = file_path.name.lower()
        if lower_name.endswith("controller.cs"):
            role = "controller"
            controllers.append(file_path.name)
        elif lower_name.endswith(".cshtml"):
            role = "view"
            views.append(file_path.name)
        elif "service" in lower_name:
            role = "service"
            services.append(file_path.name)
        elif "repo" in lower_name or "repository" in lower_name:
            role = "repository"
            repositories.append(file_path.name)

        scoped_relevance.append({
            "file": file_path.as_posix(),
            "basename": file_path.name,
            "role": role,
            "score": score,
            "confidence": confidence,
            "included": include,
            "reasons": reasons
        })

        if not include:
            continue

        included_files.append(file_path)

        actions = extract_controller_actions(text)
        if actions:
            route_items.append({
                "file": file_path.as_posix(),
                "controller": actions[0]["controller"] if actions else "",
                "actions": actions
            })

        sql_blocks = extract_sql_blocks(text)
        if sql_blocks:
            tables = extract_tables(sql_blocks)
            all_tables.extend(tables)
            sql_items.append({
                "file": file_path.as_posix(),
                "queries": sql_blocks,
                "tables": tables
            })

    unique_tables = list(dict.fromkeys(all_tables))
    controllers = list(dict.fromkeys(controllers))
    views = list(dict.fromkeys(views))
    services = list(dict.fromkeys(services))
    repositories = list(dict.fromkeys(repositories))

    workflows: list[dict[str, Any]] = []
    for workflow in workflow_names:
        wf_lower = str(workflow).lower()
        related_routes: list[str] = []
        related_files: list[str] = []

        for route_item in route_items:
            file_match = wf_lower in route_item["file"].lower()
            action_match = any(
                wf_lower in (a.get("action", "").lower() + " " + a.get("route", "").lower())
                for a in route_item["actions"]
            )
            if file_match or action_match:
                related_files.append(route_item["file"])
                for action in route_item["actions"]:
                    if action.get("route"):
                        related_routes.append(action["route"])
                    elif action.get("action"):
                        related_routes.append(action["action"])

        workflows.append({
            "workflowName": workflow,
            "entryRoutes": list(dict.fromkeys(related_routes)),
            "relatedFiles": list(dict.fromkeys(related_files)),
            "controllers": controllers,
            "views": views
        })

    map_path = write_json(ctx.out_dir / "csharp-module-map.json", {
        "moduleName": module_name,
        "workflowNames": workflow_names,
        "convertedRoots": payload["convertedRoots"],
        "controllers": controllers,
        "views": views,
        "services": services,
        "repositories": repositories,
        "includedFiles": [p.as_posix() for p in included_files],
        "workflows": workflows,
        "strictModuleOnly": strict_module_only
    })

    route_path = write_json(ctx.out_dir / "controller-route-map.json", {
        "items": route_items
    })

    sql_path = write_json(ctx.out_dir / "csharp-sql-map.json", {
        "items": sql_items
    })

    table_path = write_json(ctx.out_dir / "csharp-table-usage.json", {
        "tables": unique_tables
    })

    scope_path = write_json(ctx.out_dir / "scoped-file-relevance.json", {
        "items": scoped_relevance
    })

    artifacts = [map_path, route_path, sql_path, table_path, scope_path]

    result_path = write_result(
        ctx,
        status="passed",
        summary=f"Scoped {len(included_files)} C# files for module '{module_name}' and mapped routes, SQL, and tables.",
        artifacts=artifacts,
        metrics={
            "candidateFiles": len(candidate_files),
            "includedFiles": len(included_files),
            "controllers": len(controllers),
            "views": len(views),
            "services": len(services),
            "repositories": len(repositories),
            "routeFiles": len(route_items),
            "sqlFiles": len(sql_items),
            "tables": len(unique_tables),
            "workflowCount": len(workflow_names)
        }
    )

    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())