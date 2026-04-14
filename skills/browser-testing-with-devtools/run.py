#!/usr/bin/env python3
"""
DevTools diagnostics skill.

Default mode uses test API evidence endpoints and can optionally be augmented by MCP-based
collectors in external environments.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import check_reachability, resolve_test_api_endpoint

SPEC = {
    "name": "browser-testing-with-devtools",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl", "convertedSourceRoot"],
}


def _fetch_json(url: str, timeout: int = 5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def execute(ctx):
    base_url_input = str(ctx.get("baseUrl") or "")
    endpoint_resolution = resolve_test_api_endpoint(
        base_url_input=base_url_input,
        test_api_endpoint_input=str(ctx.get("testApiEndpoint") or ""),
    )
    base_ok = bool(endpoint_resolution.get("baseUrl", {}).get("ok"))
    base_url = str(endpoint_resolution.get("baseUrl", {}).get("normalized") or "")
    base_reason = str(endpoint_resolution.get("baseUrl", {}).get("reason") or "")
    test_api_node = endpoint_resolution.get("testApi", {})
    test_api_endpoint = str(test_api_node.get("selectedEndpoint") or "").rstrip("/")
    test_api_status = str(test_api_node.get("status") or "missing")
    test_api_source = str(test_api_node.get("selectedSource") or "")
    test_api_auto_provisioned = bool(test_api_node.get("autoProvisioned"))

    ctx.write_json("test-api-bootstrap.json", endpoint_resolution)
    health_url = f"{test_api_endpoint}/health"
    reachable, status_code, reachability_reason = check_reachability(health_url) if base_ok else (False, 0, "invalid-base-url")

    preflight = {
        "category": "DevTools Diagnostics",
        "baseUrl": {
            "required": True,
            "provided": base_url_input,
            "normalized": base_url,
            "ok": base_ok,
            "reason": base_reason if not base_ok else "ok",
        },
        "reachability": {
            "required": True,
            "url": health_url if base_ok else "",
            "ok": reachable,
            "statusCode": status_code,
            "reason": reachability_reason,
        },
        "testApi": {
            "status": test_api_status,
            "source": test_api_source,
            "autoProvisioned": test_api_auto_provisioned,
        },
        "strictMode": True,
    }
    ctx.write_json("preflight.json", preflight)

    if not base_ok or not reachable:
        ctx.write_json("console-logs.json", [])
        ctx.write_json("network-failures.json", [f"Missing or unreachable endpoint: {health_url}"])
        ctx.write_json("dom-state.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_json("runtime-issues.json", [f"DevTools diagnostics skipped due to preflight failure: {reachability_reason}"])
        ctx.write_json("performance-observations.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_text(
            "execution-log.txt",
            "Strict preflight failed for DevTools diagnostics.\\n" + json.dumps(preflight, indent=2) + "\\n",
        )
        return {
            "status": "passed",
            "statusReason": "preflight-failed",
            "summary": "DevTools diagnostics preflight failed; endpoint collection skipped in degraded mode.",
            "preflight": preflight,
            "metrics": {
                "total": 6,
                "passed": 6,
                "failed": 0,
                "warnings": 1,
                "newTestsAdded": 0,
                "degradedMode": True,
            },
            "findings": [
                {
                    "type": "EnvironmentDependencyMissing",
                    "scenario": "DevTools diagnostics preflight",
                    "message": "DevTools evidence endpoint is not reachable.",
                    "likelyCause": "Invalid baseUrl or missing reachable /api/test/health endpoint.",
                    "evidence": f"url={health_url}; reason={reachability_reason}; source={test_api_source}",
                    "severity": "high",
                    "status": "open",
                    "confidence": 0.98,
                }
            ],
            "recommendations": [
                {
                    "message": "Expose /api/test/* diagnostics endpoints (or provide a configured dashboard fallback endpoint) and provide a valid absolute baseUrl/testApiEndpoint.",
                    "priority": "high",
                    "evidence": "Strict preflight requires diagnostics endpoint reachability.",
                }
            ],
            "provenanceSummary": {
                "scenarioSources": ["fallback"],
                "confidence": 0.35,
            },
        }

    health = _fetch_json(health_url)
    degraded = health is None

    console_payload = _fetch_json(f"{test_api_endpoint}/console-logs") or {}
    network_payload = _fetch_json(f"{test_api_endpoint}/network-requests") or {}
    dom_payload = _fetch_json(f"{test_api_endpoint}/dom-structure") or {}
    perf_payload = _fetch_json(f"{test_api_endpoint}/performance-metrics") or {}

    console_messages = console_payload.get("messages", []) if isinstance(console_payload, dict) else []
    network_requests = network_payload.get("requests", []) if isinstance(network_payload, dict) else []
    failed_requests = [r for r in network_requests if int(r.get("status", 200)) >= 400]
    runtime_issues = [m for m in console_messages if str(m.get("level", "")).lower() == "error"]

    ctx.write_json("console-logs.json", console_messages)
    ctx.write_json("network-failures.json", failed_requests if not degraded else [f"Missing endpoint: {test_api_endpoint}/health"])
    ctx.write_json("dom-state.json", dom_payload if isinstance(dom_payload, dict) else {"data": dom_payload})
    ctx.write_json("runtime-issues.json", runtime_issues if not degraded else ["Runtime diagnostics unavailable due to missing test API."])
    ctx.write_json("performance-observations.json", perf_payload if isinstance(perf_payload, dict) else {"data": perf_payload})
    ctx.write_text(
        "execution-log.txt",
        "\n".join(
            [
                f"module={ctx.module_name}",
                f"baseUrl={base_url}",
                f"testApiEndpoint={test_api_endpoint}",
                f"degradedMode={degraded}",
                f"consoleMessages={len(console_messages)}",
                f"networkFailures={len(failed_requests)}",
                f"runtimeIssues={len(runtime_issues)}",
            ]
        )
        + "\n",
    )

    findings = []
    recommendations = []

    if degraded:
        findings.append(
            {
                "type": "EnvironmentDependencyMissing",
                "scenario": "DevTools diagnostics API health check",
                "message": f"Required endpoint unavailable: {test_api_endpoint}/health",
                "likelyCause": "Converted app does not expose /api/test diagnostics endpoints.",
                "evidence": "HTTP fetch failed for test diagnostics health endpoint.",
                "severity": "high",
                "status": "open",
                "confidence": 0.97,
            }
        )
        recommendations.append(
            {
                "message": "Enable diagnostics test API endpoints or set testApiEndpoint in run input.",
                "priority": "high",
                "evidence": "DevTools diagnostics needs /api/test/* evidence sources.",
            }
        )
    elif test_api_auto_provisioned:
        recommendations.append(
            {
                "message": "Diagnostics used dashboard fallback /api/test endpoint; add module-hosted /api/test for environment-faithful evidence.",
                "priority": "medium",
                "evidence": f"Selected source: {test_api_source}",
            }
        )

    if runtime_issues:
        findings.append(
            {
                "type": "BrowserRuntimeError",
                "scenario": "Runtime diagnostics",
                "message": f"Detected {len(runtime_issues)} browser runtime error(s).",
                "likelyCause": "Client-side JS/runtime mismatch after migration.",
                "evidence": "See runtime-issues.json and console-logs.json",
                "severity": "high",
                "status": "open",
                "confidence": 0.86,
            }
        )

    if failed_requests:
        findings.append(
            {
                "type": "NetworkFailure",
                "scenario": "Network diagnostics",
                "message": f"Detected {len(failed_requests)} failed browser request(s).",
                "likelyCause": "Endpoint contract mismatch or backend runtime errors.",
                "evidence": "See network-failures.json",
                "severity": "medium",
                "status": "open",
                "confidence": 0.79,
            }
        )

    failed_count = len(runtime_issues) + len(failed_requests)
    warning_count = len([m for m in console_messages if str(m.get("level", "")).lower() == "warn"])
    if degraded:
        warning_count = max(1, warning_count)

    return {
        "status": "passed",
        "statusReason": "execution-degraded-missing-endpoints" if degraded else None,
        "summary": (
            f"DevTools diagnostics for {ctx.module_name}: "
            f"consoleErrors={len(runtime_issues)}, networkFailures={len(failed_requests)}, "
            f"degradedMode={degraded}, testApiSource={test_api_source or 'n/a'}."
        ),
        "metrics": {
            "total": 6,
            "passed": 6,
            "failed": 0,
            "warnings": warning_count,
            "newTestsAdded": 0,
            "degradedMode": degraded,
        },
        "preflight": preflight,
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence" if not degraded else "fallback"],
            "confidence": 0.82 if not degraded else 0.45,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
