#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, find_candidate_projects, run_test_category

SPEC = {
    "name": "unit-test-execution",
    "stage": "execution",
    "requiredInputs": ["moduleName", "convertedSourceRoot"],
}


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")
    projects = find_candidate_projects(converted_root, [ctx.module_name, "unit", "test"])

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.unit", "commands.unit"])
    for project in projects[:2]:
        commands.append(["dotnet", "test", project.as_posix(), "--nologo", "--verbosity", "minimal"])

    fallback_scenarios = [
        f"{ctx.module_name} business-rule validator coverage",
        f"{ctx.module_name} mapping and transformation guards",
        f"{ctx.module_name} command/query guard behavior",
    ]

    result = run_test_category(
        ctx,
        category="Unit",
        purpose="Validate domain logic and validators in isolation.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=Path(converted_root).as_posix() if converted_root else None,
        timeout_seconds=240,
        log_name="execution-log.txt",
    )
    return result


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
