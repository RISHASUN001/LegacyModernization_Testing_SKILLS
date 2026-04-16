#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from ai_provider import AIProvider, StrictAIUnavailableError
from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result


SKILL_NAME = "legacy-logic-understanding"


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

    strict = bool(payload.get("strictAIGeneration", True))
    provider = AIProvider(strict_mode=strict)

    legacy_root = Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "legacy-module-discovery"

    legacy_map_path = legacy_root / "legacy-module-map.json"
    java_sql_path = legacy_root / "java-sql-map.json"
    java_table_path = legacy_root / "java-table-usage.json"
    legacy_scope_path = legacy_root / "legacy-scoped-file-relevance.json"

    context = {
        "moduleName": ctx.module_name,
        "workflowNames": payload.get("workflowNames", []),
        "startUrl": payload.get("startUrl", ""),
        "expectedEndUrls": payload.get("expectedEndUrls", []),
        "legacyDiscovery": {
            "moduleMap": json.loads(legacy_map_path.read_text(encoding="utf-8")) if legacy_map_path.exists() else {},
            "sqlMap": json.loads(java_sql_path.read_text(encoding="utf-8")) if java_sql_path.exists() else {},
            "tableUsage": json.loads(java_table_path.read_text(encoding="utf-8")) if java_table_path.exists() else {},
            "scope": json.loads(legacy_scope_path.read_text(encoding="utf-8")) if legacy_scope_path.exists() else {},
        },
    }

    schema_hint = {
        "modulePurpose": "string",
        "workflows": [
            {
                "name": "string",
                "entryPoint": "string",
                "legacyFiles": ["string"],
                "likelyRoutes": ["string"],
                "likelyJspFlow": ["string"],
                "decisionBranches": ["string"],
                "validations": ["string"],
                "dbTouchpoints": ["string"],
                "tables": ["string"],
                "functionalConstraints": ["string"],
                "outcome": "string",
                "notes": ["string"]
            }
        ]
    }

    prompt = (
        "Generate legacy Java/JSP workflow understanding from the scoped legacy discovery outputs. "
        "Be strict to the selected workflows only. "
        "Explain likely legacy behavior, JSP/action/DAO flow, validations, DB touchpoints, "
        "and functional constraints implied by the selected legacy files and SQL."
    )

    try:
        ai = provider.generate_json(
            prompt,
            context=context,
            schema_hint=schema_hint,
        )
    except StrictAIUnavailableError as ex:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            str(ex),
            artifacts=[],
            findings=[{"type": "StrictAIUnavailable", "message": str(ex)}],
        )
        print(result_path)
        return 1

    logic = {
        "moduleName": ctx.module_name,
        "source": "legacy",
        "provider": ai.provider,
        "payload": ai.content,
    }
    logic_path = write_json(ctx.out_dir / "legacy-logic-summary.json", logic)

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Generated legacy logic understanding for {len(payload.get('workflowNames', []))} workflows.",
        artifacts=[logic_path],
        metrics={
            "workflowCount": len(payload.get("workflowNames", [])),
            "provider": ai.provider
        },
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())