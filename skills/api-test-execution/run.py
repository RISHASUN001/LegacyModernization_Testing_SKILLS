#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, find_candidate_projects, run_test_category

SPEC = {
    "name": "api-test-execution",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl"],
}


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")
    projects = find_candidate_projects(converted_root, [ctx.module_name, "api", "test"])

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.api", "commands.api"])

    api_collection = str(ctx.get("apiTestCollection") or "").strip()
    if api_collection and shutil.which("newman"):
        commands.append(["newman", "run", api_collection])

    for project in projects[:2]:
        commands.append(["dotnet", "test", project.as_posix(), "--nologo", "--verbosity", "minimal"])

    fallback_scenarios = [
        f"{ctx.module_name} legacy endpoint compatibility",
        f"{ctx.module_name} request validation and status code behavior",
        f"{ctx.module_name} response contract/schema compatibility",
    ]

    return run_test_category(
        ctx,
        category="API",
        purpose="Validate API contracts and endpoint behavior against module expectations.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=Path(converted_root).as_posix() if converted_root else None,
        timeout_seconds=300,
        require_base_url=True,
        reachability_path="/",
        log_name="execution-log.txt",
    )


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
