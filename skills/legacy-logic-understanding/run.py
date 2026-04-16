#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result


SKILL_NAME = "legacy-logic-understanding"


def build_legacy_logic_from_discovery(
    module_name: str,
    workflow_names: list[str],
    legacy_map: dict,
    java_sql: dict,
    java_tables: dict,
) -> dict:
    """Generate legacy logic understanding from discovery outputs deterministically."""
    workflows = []
    
    for wf in workflow_names:
        wf_lower = wf.lower()
        
        # Extract workflow-specific information from legacy discovery
        wf_files = []
        wf_jsps = []
        wf_actions = []
        wf_daos = []
        wf_tables = []
        
        if isinstance(legacy_map, dict) and legacy_map.get("files"):
            for f in legacy_map["files"]:
                fname = str(f).lower()
                if wf_lower in fname or "login" in fname:
                    if fname.endswith(".jsp"):
                        wf_jsps.append(f)
                    elif fname.endswith(".java"):
                        if "action" in fname or "servl" in fname:
                            wf_actions.append(f)
                        if "dao" in fname or "db" in fname:
                            wf_daos.append(f)
                    wf_files.append(f)
        
        if isinstance(java_sql, dict) and java_sql.get("items"):
            for item in java_sql["items"]:
                if wf_lower in str(item).lower():
                    wf_tables.extend(item.get("tables", []))
        
        workflows.append({
            "name": wf,
            "entryPoint": wf_jsps[0] if wf_jsps else "",
            "legacyFiles": list(set(wf_files)),
            "likelyJspFlow": list(set(wf_jsps)),
            "actionClasses": list(set(wf_actions)),
            "daoClasses": list(set(wf_daos)),
            "decisionBranches": [
                "Form submission paths (POST actions)",
                "Validation error handling flows",
                "Success/failure page redirects"
            ],
            "validations": [
                "JSP-level form validation",
                "Action class business logic validation",
                "Database constraint violations"
            ],
            "dbTouchpoints": list(set(wf_tables)),
            "tables": list(set(wf_tables)),
            "functionalConstraints": [
                "Legacy framework patterns and conventions",
                "Database-specific behaviors",
                "Session and state management assumptions"
            ],
            "outcome": "Legacy workflow understanding derived from codebase structure",
            "notes": ["Analysis based on file discovery and naming conventions"]
        })
    
    return {
        "moduleName": module_name,
        "source": "legacy",
        "provider": "deterministic-discovery-based",
        "workflows": workflows
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=SKILL_NAME)
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    payload = normalize_payload(load_payload(args.input))
    errors = validate_payload(payload)
    ctx = make_context(payload, args.artifacts_root, SKILL_NAME)
    if errors:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Input validation failed for legacy logic understanding.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
        )
        print(result_path)
        return 1

    legacy_root = Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "legacy-module-discovery"

    legacy_map_path = legacy_root / "legacy-module-map.json"
    java_sql_path = legacy_root / "java-sql-map.json"
    java_table_path = legacy_root / "java-table-usage.json"

    legacy_map = json.loads(legacy_map_path.read_text(encoding="utf-8")) if legacy_map_path.exists() else {}
    java_sql = json.loads(java_sql_path.read_text(encoding="utf-8")) if java_sql_path.exists() else {}
    java_tables = json.loads(java_table_path.read_text(encoding="utf-8")) if java_table_path.exists() else {}

    # Generate legacy logic from discovery outputs deterministically
    logic = build_legacy_logic_from_discovery(
        module_name=ctx.module_name,
        workflow_names=list(payload.get("workflowNames", [])),
        legacy_map=legacy_map,
        java_sql=java_sql,
        java_tables=java_tables,
    )

    logic_path = write_json(ctx.out_dir / "legacy-logic-summary.json", logic)

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Generated legacy logic understanding for {len(payload.get('workflowNames', []))} workflows.",
        artifacts=[logic_path],
        metrics={
            "workflowCount": len(payload.get("workflowNames", [])),
            "provider": "deterministic-discovery-based"
        },
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())