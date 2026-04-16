#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, run_test_category

SPEC = {
    "name": "edge-case-testing",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl"],
}


def execute(ctx):
    logic = ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json") or {}
    preserve = logic.get("mustPreserve", [])
    workflows = logic.get("workflows", []) if isinstance(logic.get("workflows"), list) else []

    fallback_scenarios = [
        f"{ctx.module_name} null and empty payload handling",
        f"{ctx.module_name} duplicate submit idempotency",
        f"{ctx.module_name} stale session and retry recovery",
    ]
    for flow in workflows[:2]:
        if isinstance(flow, dict):
            flow_name = str(flow.get("name") or "").strip()
            if flow_name:
                fallback_scenarios.append(f"{ctx.module_name} edge behavior for flow: {flow_name}")
    if preserve:
        fallback_scenarios.append(f"{ctx.module_name} preserve behavior: {preserve[0]}")

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.edgeCase", "commands.edgeCase"])

    converted_root = str(ctx.get("convertedSourceRoot") or "")
    cwd = Path(converted_root).as_posix() if converted_root else None

    result = run_test_category(
        ctx,
        category="Edge Case",
        purpose="Validate low-frequency, high-impact module behavior and resilience paths.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=cwd,
        timeout_seconds=240,
        require_base_url=True,
        reachability_path="/",
        log_name="execution-log.txt",
    )
    scenario_matrix = result.get("metrics", {}).get("scenarios", [])
    ctx.write_json("edge-case-matrix.json", scenario_matrix if isinstance(scenario_matrix, list) else [])
    return result


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
