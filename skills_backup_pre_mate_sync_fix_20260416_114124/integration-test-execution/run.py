#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, find_candidate_projects, run_test_category

SPEC = {
    "name": "integration-test-execution",
    "stage": "execution",
    "requiredInputs": ["moduleName", "convertedSourceRoot"],
}


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")
    projects = find_candidate_projects(converted_root, [ctx.module_name, "integration", "test"])

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.integration", "commands.integration"])
    for project in projects[:2]:
        commands.append(["dotnet", "test", project.as_posix(), "--nologo", "--verbosity", "minimal"])

    fallback_scenarios = [
        f"{ctx.module_name} repository mapping and persistence",
        f"{ctx.module_name} service orchestration across layers",
        f"{ctx.module_name} transaction and rollback behavior",
    ]

    return run_test_category(
        ctx,
        category="Integration",
        purpose="Validate cross-layer module behavior with infrastructure dependencies.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=Path(converted_root).as_posix() if converted_root else None,
        timeout_seconds=300,
        log_name="execution-log.txt",
    )


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
