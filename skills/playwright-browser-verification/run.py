#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
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


def _fetch_json(url: str, timeout: int = 5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def execute(ctx):
    converted_root = str(ctx.get("convertedSourceRoot") or "")
    base_url = str(ctx.get("baseUrl") or "").rstrip("/")
    test_api_endpoint = str(ctx.get("testApiEndpoint") or f"{base_url}/api/test").rstrip("/")

    commands = command_candidates_from_payload(ctx.payload, ["testCommands.playwright", "commands.playwright"])

    candidate_root = Path(converted_root) if converted_root else Path.cwd()
    if shutil.which("python3"):
        commands.append(["python3", "-m", "pytest", "-m", "playwright"])
    if shutil.which("npx") and (candidate_root / "playwright.config.ts").exists():
        commands.append(["npx", "playwright", "test"])

    fallback_scenarios = [
        f"{ctx.module_name} browser journey: load + edit + submit",
        f"{ctx.module_name} browser validation/error rendering",
        f"{ctx.module_name} browser interaction under navigation transitions",
    ]

    test_api_health_payload = _fetch_json(f"{test_api_endpoint}/health")
    test_api_present = isinstance(test_api_health_payload, dict)
    test_api_reason = "reachable" if test_api_present else "missing-or-unreachable"

    ctx.write_json(
        "test-api-status.json",
        {
            "endpoint": test_api_endpoint,
            "healthUrl": f"{test_api_endpoint}/health",
            "status": "present" if test_api_present else "missing",
            "reason": test_api_reason,
            "payload": test_api_health_payload if isinstance(test_api_health_payload, dict) else {},
        },
    )

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
    )

    if str(result.get("statusReason", "")).lower() == "preflight-failed":
        ctx.write_json("console-logs.json", [])
        ctx.write_json("network-failures.json", [])
        ctx.write_json("dom-state.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_json("runtime-issues.json", [])
        ctx.write_json("performance-observations.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_placeholder_png("screenshots/browser-overview.png")
        if not test_api_present:
            result.setdefault("findings", []).append(
                {
                    "type": "TestApiMissing",
                    "scenario": "Playwright evidence collection",
                    "message": f"Test API endpoint is missing/unreachable: {test_api_endpoint}",
                    "likelyCause": "Application under test does not expose /api/test diagnostics endpoints.",
                    "evidence": f"healthUrl={test_api_endpoint}/health",
                    "severity": "medium",
                    "status": "open",
                    "confidence": 0.9,
                }
            )
        return result

    console_payload = _fetch_json(f"{test_api_endpoint}/console-logs") or {}
    network_payload = _fetch_json(f"{test_api_endpoint}/network-requests") or {}
    dom_payload = _fetch_json(f"{test_api_endpoint}/dom-structure") or {}
    perf_payload = _fetch_json(f"{test_api_endpoint}/performance-metrics") or {}

    console_messages = console_payload.get("messages", []) if isinstance(console_payload, dict) else []
    network_requests = network_payload.get("requests", []) if isinstance(network_payload, dict) else []
    failed_requests = [r for r in network_requests if int(r.get("status", 200)) >= 400]

    ctx.write_json("console-logs.json", console_messages)
    ctx.write_json("network-failures.json", failed_requests)
    ctx.write_json("dom-state.json", dom_payload if isinstance(dom_payload, dict) else {"data": dom_payload})
    ctx.write_json("runtime-issues.json", [m for m in console_messages if str(m.get("level", "")).lower() == "error"])
    ctx.write_json("performance-observations.json", perf_payload if isinstance(perf_payload, dict) else {"data": perf_payload})
    ctx.write_placeholder_png("screenshots/browser-overview.png")

    if not console_messages and not network_requests:
        result.setdefault("findings", []).append(
            {
                "type": "BrowserEvidenceUnavailable",
                "scenario": "Playwright evidence collection",
                "message": f"No browser evidence returned from {test_api_endpoint} endpoints.",
                "likelyCause": "Test API endpoints are unavailable or not instrumented.",
                "evidence": "console/network payloads were empty or unavailable.",
                "severity": "medium",
                "status": "open",
                "confidence": 0.8,
            }
        )
        result.setdefault("recommendations", []).append(
            {
                "message": "Enable test API evidence endpoints to enrich Playwright diagnostics.",
                "priority": "medium",
                "evidence": "Playwright skill depends on evidence endpoint data for console/network/runtime context.",
            }
        )

    failed = int(result.get("metrics", {}).get("failed", 0))
    failed += len([m for m in console_messages if str(m.get("level", "")).lower() == "error"])
    failed += len(failed_requests)
    total = int(result.get("metrics", {}).get("total", len(fallback_scenarios)))
    passed = max(0, total - failed)

    result["metrics"].update(
        {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": int(result.get("metrics", {}).get("warnings", 0)) + len([m for m in console_messages if str(m.get("level", "")).lower() == "warn"]),
            "newTestsAdded": int(result.get("metrics", {}).get("newTestsAdded", 0)),
        }
    )
    if failed > 0:
        result["status"] = "failed"

    result["summary"] = (
        f"Playwright/browser verification for {ctx.module_name}: "
        f"{result['metrics']['passed']} passed, {result['metrics']['failed']} failed, "
        f"consoleErrors={len([m for m in console_messages if str(m.get('level', '')).lower() == 'error'])}, "
        f"networkFailures={len(failed_requests)}."
    )

    result["provenanceSummary"] = {
        "scenarioSources": [s.get("provenance", {}).get("type", "inferred") for s in result.get("metrics", {}).get("scenarios", []) if isinstance(s, dict)],
        "evidenceSources": [
            f"{test_api_endpoint}/console-logs",
            f"{test_api_endpoint}/network-requests",
            f"{test_api_endpoint}/dom-structure",
            f"{test_api_endpoint}/performance-metrics",
        ],
        "confidence": 0.76 if console_messages or network_requests else 0.45,
    }

    return result


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
