#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, run_test_category

SPEC = {
    "name": "e2e-test-execution",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl"],
}


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.e2e", "commands.e2e"])

    # Python Playwright/pytest fallback first; Node Playwright remains a compatibility fallback.
    candidate_root = Path(converted_root) if converted_root else Path.cwd()
    if shutil.which("python3"):
        commands.append(["python3", "-m", "pytest", "-m", "e2e"])
    if shutil.which("npx") and (candidate_root / "playwright.config.ts").exists():
        commands.append(["npx", "playwright", "test"])

    fallback_scenarios = [
        f"{ctx.module_name} load/edit/submit critical journey",
        f"{ctx.module_name} session timeout and redirect behavior",
        f"{ctx.module_name} concurrent update conflict handling",
    ]

    result = run_test_category(
        ctx,
        category="E2E",
        purpose="Validate full module journey behavior across UI/API/persistence boundaries.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=candidate_root.as_posix(),
        timeout_seconds=360,
        require_base_url=True,
        reachability_path="/",
        log_name="execution-log.txt",
    )

    scenarios = result.get("metrics", {}).get("scenarios", [])
    ctx.write_json("e2e-scenarios.json", scenarios if isinstance(scenarios, list) else [])

    if result.get("status") == "passed":
        ctx.write_placeholder_png("screenshots/e2e-success.png")
    else:
        ctx.write_placeholder_png("screenshots/e2e-failure.png")

    return result


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
