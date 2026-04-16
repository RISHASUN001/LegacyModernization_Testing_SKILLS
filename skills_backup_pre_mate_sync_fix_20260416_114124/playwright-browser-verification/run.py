#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import command_candidates_from_payload, run_test_category

SPEC = {
    "name": "playwright-browser-verification",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl"],
}


def _extract_runtime_signals(log_text: str) -> tuple[list[str], list[str]]:
    runtime_issues: list[str] = []
    network_failures: list[str] = []

    for line in (log_text or "").splitlines():
        lower = line.lower()
        if any(token in lower for token in ["uncaught", "exception", "javascript error", "console error", "traceback"]):
            runtime_issues.append(line.strip())
        if any(token in lower for token in [" 404 ", " 500 ", "err_", "net::", "request failed", "timed out"]):
            network_failures.append(line.strip())

    return runtime_issues[:120], network_failures[:120]


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")
    strict_mode = bool(ctx.payload.get("strictModuleOnly", True))

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.playwright", "commands.playwright"])
    commands = [c for c in commands if c and str(c[0]).lower() != "npx"]

    candidate_root = Path(converted_root) if converted_root else Path.cwd()
    if shutil.which("python3"):
        commands.append(["python3", "-m", "pytest", "-m", "playwright"])
        commands.append(["python3", "-m", "pytest"])
    if shutil.which("pytest"):
        commands.append(["pytest", "-m", "playwright"])
        commands.append(["pytest"])

    fallback_scenarios = [
        f"{ctx.module_name} browser journey: load + edit + submit",
        f"{ctx.module_name} browser validation/error rendering",
        f"{ctx.module_name} browser interaction under navigation transitions",
    ]

    result = run_test_category(
        ctx,
        category="Playwright / E2E Browser",
        purpose="Validate browser journeys with UI assertions and visual evidence.",
        fallback_scenarios=fallback_scenarios,
        command_candidates=commands,
        cwd=candidate_root.as_posix(),
        timeout_seconds=420,
        require_base_url=True,
        reachability_path="/",
        log_name="execution-log.txt",
        fail_on_no_tests_collected=True,
    )

    if str(result.get("statusReason", "")).lower() == "preflight-failed":
        ctx.write_json("console-logs.json", [])
        ctx.write_json("network-failures.json", [])
        ctx.write_json("dom-state.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_json("runtime-issues.json", [])
        ctx.write_json("performance-observations.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_placeholder_png("screenshots/browser-overview.png")
        return result

    log_path = ctx.out_dir / "execution-log.txt"
    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    runtime_issues, network_failures = _extract_runtime_signals(log_text)

    ctx.write_json("console-logs.json", [{"level": "error", "message": item} for item in runtime_issues])
    ctx.write_json("network-failures.json", [{"message": item} for item in network_failures])
    ctx.write_json("dom-state.json", {"status": "not-captured", "reason": "playwright-log-based-diagnostics"})
    ctx.write_json("runtime-issues.json", runtime_issues)
    ctx.write_json("performance-observations.json", {"status": "not-captured", "reason": "devtools-stage-captures-runtime-details"})
    ctx.write_placeholder_png("screenshots/browser-overview.png")

    if not runtime_issues and not network_failures:
        result.setdefault("findings", []).append(
            {
                "type": "BrowserEvidenceUnavailable",
                "scenario": "Playwright evidence collection",
                "message": "Playwright execution did not emit runtime/network issue signatures in execution logs.",
                "likelyCause": "No browser-side errors were emitted or tests did not include log capture hooks.",
                "evidence": "execution-log.txt had no console/network failure signatures.",
                "severity": "medium",
                "status": "open",
                "confidence": 0.8,
            }
        )
        result.setdefault("recommendations", []).append(
            {
                "message": "Enable explicit Playwright tracing/screenshot capture and structured reporter output for richer diagnostics.",
                "priority": "medium",
                "evidence": "No browser failure signatures extracted from execution logs.",
            }
        )

    failed = int(result.get("metrics", {}).get("failed", 0))
    failed += len(runtime_issues)
    failed += len(network_failures)
    if strict_mode and ("NoTestsCollected" in [str(f.get("type") or "") for f in result.get("findings", [])]):
        failed = max(failed, int(result.get("metrics", {}).get("total", 1)))

    total = int(result.get("metrics", {}).get("total", len(fallback_scenarios)))
    passed = max(0, total - failed)

    result["metrics"].update(
        {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": int(result.get("metrics", {}).get("warnings", 0)),
            "newTestsAdded": int(result.get("metrics", {}).get("newTestsAdded", 0)),
        }
    )
    if failed > 0:
        result["status"] = "failed"

    result["summary"] = (
        f"Playwright/browser verification for {ctx.module_name}: "
        f"{result['metrics']['passed']} passed, {result['metrics']['failed']} failed, "
        f"runtimeSignals={len(runtime_issues)}, "
        f"networkSignals={len(network_failures)}."
    )

    result["provenanceSummary"] = {
        "scenarioSources": [s.get("provenance", {}).get("type", "inferred") for s in result.get("metrics", {}).get("scenarios", []) if isinstance(s, dict)],
        "evidenceSources": ["execution-log.txt", "playwright-generated artifacts"],
        "confidence": 0.76 if runtime_issues or network_failures else 0.52,
    }

    return result


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
