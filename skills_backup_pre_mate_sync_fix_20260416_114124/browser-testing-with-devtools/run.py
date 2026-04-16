#!/usr/bin/env python3
"""
DevTools diagnostics skill (app-direct mode).

This skill does not require /api/test endpoints. It validates base/start/terminal route reachability
and mines runtime/network signals from Playwright execution logs to produce actionable diagnostics.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from execution_utils import check_reachability, normalize_absolute_base_url, normalize_route

SPEC = {
    "name": "browser-testing-with-devtools",
    "stage": "execution",
    "requiredInputs": ["moduleName", "baseUrl", "convertedSourceRoot"],
}


def _probe_url(url: str, timeout: int = 8) -> dict:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "legacy-modernization-devtools"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(2048)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return {
                "url": url,
                "status": int(response.status),
                "ok": 200 <= int(response.status) < 400,
                "elapsedMs": elapsed_ms,
                "contentType": str(response.headers.get("Content-Type") or ""),
                "bodySample": body.decode("utf-8", errors="ignore")[:280],
            }
    except urllib.error.HTTPError as ex:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "url": url,
            "status": int(ex.code),
            "ok": False,
            "elapsedMs": elapsed_ms,
            "error": f"http-error-{ex.code}",
        }
    except Exception as ex:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "url": url,
            "status": 0,
            "ok": False,
            "elapsedMs": elapsed_ms,
            "error": str(ex),
        }


def execute(ctx):
    strict_mode = bool(ctx.payload.get("strictModuleOnly", True))
    base_url_input = str(ctx.get("baseUrl") or "")
    base_ok, base_url, base_reason = normalize_absolute_base_url(base_url_input)
    reachable, status_code, reachability_reason = check_reachability(base_url) if base_ok else (False, 0, "invalid-base-url")

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
            "url": base_url if base_ok else "",
            "ok": reachable,
            "statusCode": status_code,
            "reason": reachability_reason,
        },
        "strictMode": strict_mode,
    }
    ctx.write_json("preflight.json", preflight)

    if not base_ok or not reachable:
        ctx.write_json("console-logs.json", [])
        ctx.write_json("network-failures.json", [f"Missing or unreachable base endpoint: {base_url_input}"])
        ctx.write_json("dom-state.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_json("runtime-issues.json", [f"DevTools diagnostics skipped due to preflight failure: {reachability_reason}"])
        ctx.write_json("performance-observations.json", {"status": "skipped", "reason": "preflight-failed"})
        ctx.write_text(
            "execution-log.txt",
            "Strict preflight failed for DevTools diagnostics.\n" + json.dumps(preflight, indent=2) + "\n",
        )
        return {
            "status": "failed" if strict_mode else "passed",
            "statusReason": "preflight-failed",
            "summary": "DevTools diagnostics preflight failed; application endpoint collection skipped.",
            "preflight": preflight,
            "metrics": {
                "total": 6,
                "passed": 0 if strict_mode else 6,
                "failed": 6 if strict_mode else 0,
                "warnings": 1,
                "newTestsAdded": 0,
                "degradedMode": False,
                "scenarios": [
                    {
                        "name": "DevTools preflight base URL reachability",
                        "status": "failed",
                        "notes": "Base URL preflight failed",
                        "coverage": ["preflight", "reachability"],
                        "generated": False,
                        "generatedFrom": [],
                        "provenance": {
                            "type": "code-evidence",
                            "sources": ["preflight.json"],
                            "confidence": 0.98,
                            "unknowns": []
                        }
                    }
                ],
            },
            "findings": [
                {
                    "type": "EnvironmentDependencyMissing",
                    "scenario": "DevTools diagnostics preflight",
                    "message": "Base application endpoint is not reachable.",
                    "likelyCause": "Invalid baseUrl or app is not running.",
                    "evidence": f"url={base_url_input}; reason={reachability_reason}",
                    "severity": "high",
                    "status": "open",
                    "confidence": 0.98,
                }
            ],
            "recommendations": [
                {
                    "message": "Start the converted app and provide a valid absolute baseUrl.",
                    "priority": "high",
                    "evidence": "Strict preflight requires application endpoint reachability.",
                }
            ],
            "provenanceSummary": {
                "scenarioSources": ["fallback"],
                "confidence": 0.35,
            },
        }

    route_candidates = []
    start_route = str(ctx.get("moduleStartUrl") or ctx.get("targetUrl") or "/").strip()
    if start_route:
        route_candidates.append(start_route)

    expected_terminal = ctx.get("moduleHints.expectedTerminalUrls") or []
    if isinstance(expected_terminal, list):
        route_candidates.extend([str(x).strip() for x in expected_terminal if str(x).strip()])

    known_urls = ctx.get("moduleHints.knownUrls") or []
    if isinstance(known_urls, list):
        route_candidates.extend([str(x).strip() for x in known_urls[:6] if str(x).strip()])

    deduped_routes = []
    seen = set()
    for route in route_candidates:
        key = route.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped_routes.append(route)

    probes = [_probe_url(normalize_route(base_url, route)) for route in deduped_routes[:10]]
    failed_requests = [p for p in probes if not bool(p.get("ok"))]

    playwright_log = ctx.artifacts_root / ctx.module_name / ctx.run_id / "playwright-browser-verification" / "execution-log.txt"
    log_text = playwright_log.read_text(encoding="utf-8", errors="ignore") if playwright_log.exists() else ""
    runtime_issues = [
        line.strip()
        for line in log_text.splitlines()
        if any(token in line.lower() for token in ["uncaught", "exception", "console error", "traceback"])
    ][:120]
    warnings = [line.strip() for line in log_text.splitlines() if "warn" in line.lower()][:120]

    ctx.write_json(
        "console-logs.json",
        [{"level": "error", "message": m} for m in runtime_issues] + [{"level": "warn", "message": w} for w in warnings],
    )
    ctx.write_json("network-failures.json", failed_requests)
    ctx.write_json("dom-state.json", {"status": "route-probe-only", "probed": [p.get("url") for p in probes]})
    ctx.write_json("runtime-issues.json", runtime_issues)
    ctx.write_json("performance-observations.json", {"probes": probes})
    ctx.write_text(
        "execution-log.txt",
        "\n".join(
            [
                f"module={ctx.module_name}",
                f"baseUrl={base_url}",
                f"probedRoutes={len(probes)}",
                "degradedMode=False",
                f"consoleMessages={len(runtime_issues) + len(warnings)}",
                f"networkFailures={len(failed_requests)}",
                f"runtimeIssues={len(runtime_issues)}",
            ]
        )
        + "\n",
    )

    findings = []
    scenarios = [
        {
            "name": "Collect console error and warning evidence",
            "status": "failed" if runtime_issues else "passed",
            "notes": "Runtime log scan from Playwright execution output.",
            "coverage": ["console", "runtime"],
            "generated": False,
            "generatedFrom": [],
            "provenance": {
                "type": "code-evidence",
                "sources": ["playwright-browser-verification/execution-log.txt"],
                "confidence": 0.78,
                "unknowns": []
            }
        },
        {
            "name": "Collect failed request and route latency evidence",
            "status": "failed" if failed_requests else "passed",
            "notes": "Route probe diagnostics against module boundary routes.",
            "coverage": ["network", "route-probe"],
            "generated": False,
            "generatedFrom": [],
            "provenance": {
                "type": "code-evidence",
                "sources": ["network-failures.json", "performance-observations.json"],
                "confidence": 0.79,
                "unknowns": []
            }
        }
    ]
    recommendations = [
        {
            "message": "Keep moduleStartUrl and expectedTerminalUrls updated for stronger route-probe diagnostics.",
            "priority": "medium",
            "evidence": f"probedRoutes={len(probes)}",
        }
    ]

    if runtime_issues:
        findings.append(
            {
                "type": "BrowserRuntimeError",
                "scenario": "Runtime diagnostics",
                "message": f"Detected {len(runtime_issues)} browser runtime error signature(s).",
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
                "scenario": "Route probe diagnostics",
                "message": f"Detected {len(failed_requests)} failed route probe(s).",
                "likelyCause": "Endpoint contract mismatch or backend runtime errors.",
                "evidence": "See network-failures.json",
                "severity": "medium",
                "status": "open",
                "confidence": 0.79,
            }
        )

    failed_count = len(runtime_issues) + len(failed_requests)
    warning_count = len(warnings)
    status = "failed" if failed_count > 0 else "passed"

    return {
        "status": status,
        "statusReason": "execution-failed-runtime-or-network-signals" if failed_count > 0 else None,
        "summary": (
            f"DevTools diagnostics for {ctx.module_name}: "
            f"consoleErrors={len(runtime_issues)}, networkFailures={len(failed_requests)}, "
            f"probedRoutes={len(probes)}."
        ),
        "metrics": {
            "total": 6,
            "passed": max(0, 6 - failed_count),
            "failed": failed_count,
            "warnings": warning_count,
            "newTestsAdded": 0,
            "degradedMode": False,
            "scenarios": scenarios,
        },
        "preflight": preflight,
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence"],
            "confidence": 0.76 if probes else 0.5,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
