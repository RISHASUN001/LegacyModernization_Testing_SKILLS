#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from skill_logic import previous_run_id

SPEC = {
    "name": "iteration-comparison",
    "stage": "iteration-comparison",
    "requiredInputs": ["moduleName", "runId"],
}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _collect_run_metrics(run_root: Path) -> dict:
    if not run_root.exists():
        return {
            "testsAdded": 0,
            "totalFailed": 0,
            "findingSignatures": set(),
            "resolvedFindings": 0,
            "categoryFailures": {},
        }

    tests_added = 0
    total_failed = 0
    finding_signatures: set[str] = set()
    resolved = 0
    category_failures: dict[str, int] = {}

    test_plan_path = run_root / "test-plan-generation" / "test-plan.json"
    if test_plan_path.exists():
        test_plan = _read_json(test_plan_path)
        suggested = test_plan.get("newTestsSuggested", []) if isinstance(test_plan.get("newTestsSuggested"), list) else []
        tests_added += len(suggested)

    for result_path in run_root.glob("*/result.json"):
        result = _read_json(result_path)
        metrics = result.get("metrics", {}) if isinstance(result.get("metrics", {}), dict) else {}

        total_failed += int(metrics.get("failed", 0) or 0)

        category = str(result.get("skillName") or result_path.parent.name)
        category_failures[category] = int(metrics.get("failed", 0) or 0)

        for finding in result.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            signature = f"{finding.get('type','General')}::{finding.get('scenario','')}::{finding.get('message','')}"
            finding_signatures.add(signature)
            if str(finding.get("status", "")).lower() == "resolved":
                resolved += 1

    return {
        "testsAdded": tests_added,
        "totalFailed": total_failed,
        "findingSignatures": finding_signatures,
        "resolvedFindings": resolved,
        "categoryFailures": category_failures,
    }


def execute(ctx):
    module_root = ctx.artifacts_root / ctx.module_name
    current_root = module_root / ctx.run_id
    prev_id = previous_run_id(ctx.artifacts_root, ctx.module_name, ctx.run_id)
    prev_root = module_root / prev_id if prev_id else None

    current = _collect_run_metrics(current_root)
    previous = _collect_run_metrics(prev_root) if prev_root and prev_root.exists() else {
        "testsAdded": 0,
        "totalFailed": 0,
        "findingSignatures": set(),
        "resolvedFindings": 0,
        "categoryFailures": {},
    }

    tests_added = max(0, current["testsAdded"] - previous["testsAdded"])
    tests_fixed = max(0, previous["totalFailed"] - current["totalFailed"])
    failures_reduced = tests_fixed
    new_findings = len(current["findingSignatures"] - previous["findingSignatures"])
    resolved_findings = len(previous["findingSignatures"] - current["findingSignatures"]) + int(current["resolvedFindings"])

    if not prev_id:
        trend = "baseline"
    elif failures_reduced > 0 and resolved_findings >= new_findings:
        trend = "improving"
    elif new_findings > resolved_findings:
        trend = "regressing"
    else:
        trend = "stable"

    category_delta = {}
    all_categories = sorted(set(previous["categoryFailures"].keys()) | set(current["categoryFailures"].keys()))
    for category in all_categories:
        prev_fail = int(previous["categoryFailures"].get(category, 0))
        curr_fail = int(current["categoryFailures"].get(category, 0))
        category_delta[category] = {
            "previousFailed": prev_fail,
            "currentFailed": curr_fail,
            "failuresReduced": max(0, prev_fail - curr_fail),
        }

    delta = {
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "previousRunId": prev_id,
        "testsAdded": tests_added,
        "testsFixed": tests_fixed,
        "failuresReduced": failures_reduced,
        "newFindingsIntroduced": new_findings,
        "resolvedFindings": resolved_findings,
        "progressionTrend": trend,
        "categoryDelta": category_delta,
    }
    ctx.write_json("iteration-delta.json", delta)

    return {
        "status": "passed",
        "summary": (
            f"Iteration comparison for {ctx.module_name}: prev={prev_id or 'none'}, trend={trend}, "
            f"failuresReduced={failures_reduced}, resolvedFindings={resolved_findings}."
        ),
        "metrics": delta,
        "findings": [],
        "recommendations": [
            {
                "message": "Use categoryDelta to target recurring failing categories first in next run.",
                "priority": "medium",
                "evidence": f"trend={trend}; categoryDeltaCount={len(category_delta)}",
            }
        ],
        "provenanceSummary": {
            "scenarioSources": ["code-evidence"],
            "confidence": 0.82 if prev_id else 0.65,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
