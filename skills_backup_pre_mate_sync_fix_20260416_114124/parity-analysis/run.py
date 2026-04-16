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


SKILL_NAME = "parity-analysis"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_logic_payload(path: Path) -> dict:
    data = read_json(path)
    payload = data.get("payload", {})
    return payload if isinstance(payload, dict) else {}


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
            "Input validation failed for parity analysis.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
        )
        print(result_path)
        return 1

    strict = bool(payload.get("strictAIGeneration", True))
    provider = AIProvider(strict_mode=strict)

    root = Path(args.artifacts_root) / ctx.module_name / ctx.run_id

    csharp_logic = load_logic_payload(root / "csharp-logic-understanding" / "csharp-logic-summary.json")
    legacy_logic = load_logic_payload(root / "legacy-logic-understanding" / "legacy-logic-summary.json")

    csharp_sql = read_json(root / "csharp-module-discovery" / "csharp-sql-map.json")
    csharp_tables = read_json(root / "csharp-module-discovery" / "csharp-table-usage.json")
    legacy_sql = read_json(root / "legacy-module-discovery" / "java-sql-map.json")
    legacy_tables = read_json(root / "legacy-module-discovery" / "java-table-usage.json")

    context = {
        "moduleName": ctx.module_name,
        "workflowNames": payload.get("workflowNames", []),
        "csharp": {
            "logic": csharp_logic,
            "sqlMap": csharp_sql,
            "tableUsage": csharp_tables,
        },
        "legacy": {
            "logic": legacy_logic,
            "sqlMap": legacy_sql,
            "tableUsage": legacy_tables,
        },
    }

    schema_hint = {
        "overallParityScore": 0,
        "majorFindings": ["string"],
        "workflows": [
            {
                "workflowName": "string",
                "status": "matched|partial|missing|additional",
                "preservationScore": 0.0,
                "businessFlowParity": "string",
                "validationParity": "string",
                "sqlParity": "string",
                "tableParity": "string",
                "mismatches": ["string"],
                "missingInCsharp": ["string"],
                "additionalInCsharp": ["string"]
            }
        ],
        "sqlTableComparison": {
            "legacyTables": ["string"],
            "csharpTables": ["string"],
            "matchingTables": ["string"],
            "missingInCsharp": ["string"],
            "additionalInCsharp": ["string"],
            "sqlDifferences": ["string"]
        },
        "scoringRationale": ["string"]
    }

    prompt = (
        "Perform functional parity analysis between the selected legacy and C# workflows. "
        "Compare business flow, validations, SQL behavior, tables used, and functional constraints. "
        "Flag important mismatches such as changed date limits, missing dropdown/filter behavior, "
        "missing details flow, and SQL/table drift. "
        "Return dashboard-ready structured output."
    )

    try:
        ai = provider.generate_json(prompt, context=context, schema_hint=schema_hint)
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

    content = ai.content if isinstance(ai.content, dict) else {}

    parity_diff_path = write_json(
        ctx.out_dir / "parity-diff.json",
        {
            "moduleName": ctx.module_name,
            "provider": ai.provider,
            "overallParityScore": content.get("overallParityScore", 0),
            "majorFindings": content.get("majorFindings", []),
            "workflows": content.get("workflows", [])
        }
    )

    workflow_summary_path = write_json(
        ctx.out_dir / "workflow-parity-summary.json",
        {
            "moduleName": ctx.module_name,
            "items": content.get("workflows", [])
        }
    )

    sql_table_path = write_json(
        ctx.out_dir / "sql-table-parity.json",
        {
            "moduleName": ctx.module_name,
            "comparison": content.get("sqlTableComparison", {})
        }
    )

    preservation_score_path = write_json(
        ctx.out_dir / "preservation-score.json",
        {
            "moduleName": ctx.module_name,
            "overallParityScore": content.get("overallParityScore", 0),
            "workflowScores": [
                {
                    "workflowName": item.get("workflowName"),
                    "preservationScore": item.get("preservationScore", 0.0),
                    "status": item.get("status", "")
                }
                for item in content.get("workflows", [])
            ],
            "scoringRationale": content.get("scoringRationale", [])
        }
    )

    findings = []
    for finding in content.get("majorFindings", []):
        findings.append({"type": "ParityFinding", "message": finding})

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Functional parity analysis completed with score {content.get('overallParityScore', 0)}%.",
        artifacts=[
            parity_diff_path,
            workflow_summary_path,
            sql_table_path,
            preservation_score_path
        ],
        metrics={
            "provider": ai.provider,
            "overallParityScore": content.get("overallParityScore", 0),
            "workflowCount": len(content.get("workflows", []))
        },
        findings=findings,
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())