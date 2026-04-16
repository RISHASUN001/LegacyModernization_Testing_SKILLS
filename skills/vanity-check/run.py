#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result

SKILL_NAME = "vanity-check"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def artifact_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


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
            "Input validation failed.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
        )
        print(result_path)
        return 1

    run_root = Path(args.artifacts_root) / ctx.module_name / ctx.run_id

    checks = [
        {
            "name": "csharp-discovery",
            "required": True,
            "path": run_root / "csharp-module-discovery" / "csharp-module-map.json"
        },
        {
            "name": "csharp-logic",
            "required": True,
            "path": run_root / "csharp-logic-understanding" / "csharp-logic-summary.json"
        },
        {
            "name": "legacy-discovery",
            "required": True,
            "path": run_root / "legacy-module-discovery" / "legacy-module-map.json"
        },
        {
            "name": "legacy-logic",
            "required": True,
            "path": run_root / "legacy-logic-understanding" / "legacy-logic-summary.json"
        },
        {
            "name": "diagram-index",
            "required": True,
            "path": run_root / "diagram-generation" / "diagram-index.json"
        },
        {
            "name": "parity-diff",
            "required": True,
            "path": run_root / "parity-analysis" / "parity-diff.json"
        },
        {
            "name": "preservation-score",
            "required": True,
            "path": run_root / "parity-analysis" / "preservation-score.json"
        },
        {
            "name": "unit-tests-generated",
            "required": True,
            "path": run_root / "unit-test-generation" / "unit-tests.generated.json"
        },
        {
            "name": "integration-tests-generated",
            "required": True,
            "path": run_root / "integration-test-generation" / "integration-tests.generated.json"
        },
        {
            "name": "playwright-tests-generated",
            "required": True,
            "path": run_root / "playwright-test-generation" / "playwright-tests.generated.json"
        },
        {
            "name": "unit-execution-results",
            "required": True,
            "path": run_root / "test-execution-unit" / "unit-test-results.json"
        },
        {
            "name": "integration-execution-results",
            "required": True,
            "path": run_root / "test-execution-integration" / "integration-test-results.json"
        },
        {
            "name": "playwright-execution-results",
            "required": True,
            "path": run_root / "test-execution-playwright" / "playwright-results.json"
        },
        {
            "name": "clean-architecture-report",
            "required": True,
            "path": run_root / "clean-architecture-assessment" / "clean-architecture-report.json"
        },
        {
            "name": "findings-synthesis",
            "required": True,
            "path": run_root / "findings-synthesis" / "findings-synthesis.json"
        }
    ]

    evaluated_checks = []
    missing_required = []
    present_count = 0

    for item in checks:
        exists = artifact_exists(item["path"])
        evaluated = {
            "name": item["name"],
            "required": item["required"],
            "exists": exists,
            "path": str(item["path"].as_posix())
        }
        evaluated_checks.append(evaluated)
        if exists:
            present_count += 1
        elif item["required"]:
            missing_required.append(item["name"])

    findings_data = read_json(run_root / "findings-synthesis" / "findings-synthesis.json")
    overall_status = str(findings_data.get("overallStatus", "")).lower()
    failed_areas = findings_data.get("failedAreas", []) if isinstance(findings_data, dict) else []
    key_findings = findings_data.get("keyFindings", []) if isinstance(findings_data, dict) else []

    unit_results = read_json(run_root / "test-execution-unit" / "unit-test-results.json")
    integration_results = read_json(run_root / "test-execution-integration" / "integration-test-results.json")
    playwright_results = read_json(run_root / "test-execution-playwright" / "playwright-results.json")

    execution_failures = []
    for category, data in [
        ("unit", unit_results),
        ("integration", integration_results),
        ("playwright", playwright_results),
    ]:
        if data and str(data.get("status", "")).lower() == "failed":
            execution_failures.append(category)

    if missing_required:
        recommendation = "hold"
        summary = "Critical pipeline artifacts are missing."
    elif execution_failures:
        recommendation = "needs-review"
        summary = "All required artifacts exist, but one or more execution stages failed."
    elif overall_status in {"failed", "hold"} or failed_areas:
        recommendation = "needs-review"
        summary = "Pipeline completed, but findings indicate important issues still need review."
    else:
        recommendation = "ship-with-confidence"
        summary = "Required artifacts exist, execution outputs are present, and no major blockers were detected."

    completeness_report = {
        "moduleName": ctx.module_name,
        "totalChecks": len(evaluated_checks),
        "presentChecks": present_count,
        "missingRequired": missing_required,
        "executionFailures": execution_failures,
        "checks": evaluated_checks
    }

    completeness_path = write_json(
        ctx.out_dir / "pipeline-completeness-report.json",
        completeness_report
    )

    gate_path = write_json(
        ctx.out_dir / "vanity-gate.json",
        {
            "moduleName": ctx.module_name,
            "recommendation": recommendation,
            "summary": summary,
            "missingRequiredCount": len(missing_required),
            "executionFailureCount": len(execution_failures),
            "failedAreasCount": len(failed_areas),
            "keyFindingsCount": len(key_findings)
        }
    )

    severity = "high" if recommendation == "hold" else "medium" if recommendation == "needs-review" else "low"

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Vanity check completed. Recommendation: {recommendation}.",
        artifacts=[gate_path, completeness_path],
        metrics={
            "checks": len(evaluated_checks),
            "presentChecks": present_count,
            "missingRequired": len(missing_required),
            "executionFailures": len(execution_failures)
        },
        findings=[
            {
                "type": "VanityGate",
                "message": f"Recommendation is {recommendation}.",
                "severity": severity
            }
        ]
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())