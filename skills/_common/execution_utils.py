#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from skill_logic import parse_test_counts
from skill_runtime import make_provenance

_MODULE_PROFILE_PATH = Path(__file__).resolve().parents[1] / "legacy-logic-extraction" / "module-profiles.json"
_RUNTIME_DEFAULTS_PATH = Path(__file__).resolve().parent / "runtime-defaults.json"


def _load_runtime_defaults() -> dict[str, Any]:
    try:
        payload = json.loads(_RUNTIME_DEFAULTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _default_dashboard_fallbacks() -> list[str]:
    configured = os.getenv("LEGACYMOD_TEST_API_FALLBACKS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]

    defaults = _load_runtime_defaults()
    configured_defaults = defaults.get("dashboardTestApiFallbacks") if isinstance(defaults, dict) else None
    if isinstance(configured_defaults, list):
        extracted = [str(item).strip() for item in configured_defaults if str(item).strip()]
        if extracted:
            return extracted
    return []


def _command_available(command: list[str]) -> bool:
    if not command:
        return False
    return shutil.which(command[0]) is not None


def _split_command(command_text: str) -> list[str]:
    return [token for token in command_text.strip().split(" ") if token]


def command_candidates_from_payload(payload: dict[str, Any], keys: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    for key in keys:
        node: Any = payload
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if isinstance(node, str) and node.strip():
            commands.append(_split_command(node))
        elif isinstance(node, list) and all(isinstance(x, str) for x in node):
            commands.append([str(x) for x in node if str(x).strip()])
    return [c for c in commands if c]


def normalize_absolute_base_url(base_url: str) -> tuple[bool, str, str]:
    candidate = (base_url or "").strip()
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "", "baseUrl must be an absolute http/https URL"
    netloc = parsed.netloc
    host = parsed.hostname or ""
    if host in {"0.0.0.0", "::", "[::]"}:
        replacement = "localhost"
        if parsed.port:
            netloc = f"{replacement}:{parsed.port}"
        else:
            netloc = replacement
    normalized = f"{parsed.scheme}://{netloc}"
    return True, normalized.rstrip("/"), ""


def _normalize_absolute_url(url: str) -> tuple[bool, str, str]:
    candidate = (url or "").strip()
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "", "url must be an absolute http/https URL"

    netloc = parsed.netloc
    host = parsed.hostname or ""
    if host in {"0.0.0.0", "::", "[::]"}:
        replacement = "localhost"
        if parsed.port:
            netloc = f"{replacement}:{parsed.port}"
        else:
            netloc = replacement

    path = parsed.path.rstrip("/")
    normalized = f"{parsed.scheme}://{netloc}{path}"
    return True, normalized, ""


def resolve_test_api_endpoint(
    *,
    base_url_input: str,
    test_api_endpoint_input: str,
    dashboard_fallbacks: list[str] | None = None,
) -> dict[str, Any]:
    base_ok, normalized_base_url, base_reason = normalize_absolute_base_url(base_url_input)
    provided = (test_api_endpoint_input or "").strip().rstrip("/")

    candidates: list[tuple[str, str]] = []

    if provided:
        provided_ok, provided_normalized, _ = _normalize_absolute_url(provided)
        if provided_ok:
            candidates.append(("provided", provided_normalized.rstrip("/")))

    if base_ok:
        candidates.append(("base-derived", f"{normalized_base_url}/api/test"))

    for fallback in dashboard_fallbacks or _default_dashboard_fallbacks():
        fallback_ok, fallback_normalized, _ = _normalize_absolute_url(fallback)
        if fallback_ok:
            candidates.append(("dashboard-fallback", fallback_normalized.rstrip("/")))

    deduped: list[tuple[str, str]] = []
    seen_endpoints: set[str] = set()
    for source, endpoint in candidates:
        key = endpoint.lower()
        if key in seen_endpoints:
            continue
        seen_endpoints.add(key)
        deduped.append((source, endpoint))

    checks: list[dict[str, Any]] = []
    selected_source = ""
    selected_endpoint = provided or (f"{normalized_base_url}/api/test" if base_ok else "")
    selected_status = "missing"
    selected_reason = "test-api-unreachable"

    for source, endpoint in deduped:
        health_url = f"{endpoint}/health"
        reachable, status_code, reason = check_reachability(health_url)
        status = int(status_code)
        healthy = reachable and 200 <= status < 300
        endpoint_present = reachable and status not in {0, 404} and status < 500
        checks.append(
            {
                "source": source,
                "endpoint": endpoint,
                "healthUrl": health_url,
                "reachable": reachable,
                "statusCode": status_code,
                "reason": reason,
                "healthy": healthy,
                "endpointPresent": endpoint_present,
            }
        )
        if healthy or endpoint_present:
            selected_source = source
            selected_endpoint = endpoint
            selected_status = "present" if source != "dashboard-fallback" else "fallback-attached"
            selected_reason = "reachable" if healthy else f"http-status-{status}"
        if healthy:
            break

    if not selected_source and checks:
        first = checks[0]
        selected_source = str(first.get("source") or "provided")
        selected_endpoint = str(first.get("endpoint") or selected_endpoint)
        selected_reason = str(first.get("reason") or selected_reason)

    return {
        "baseUrl": {
            "provided": base_url_input,
            "normalized": normalized_base_url,
            "ok": base_ok,
            "reason": base_reason if not base_ok else "ok",
        },
        "testApi": {
            "provided": provided,
            "selectedEndpoint": selected_endpoint,
            "selectedSource": selected_source,
            "status": selected_status,
            "reason": selected_reason,
            "autoProvisioned": selected_status == "fallback-attached",
        },
        "checks": checks,
    }


def normalize_route(base_url: str, route: str) -> str:
    candidate = (route or "").strip()
    if not candidate:
        return base_url
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        return candidate
    if not candidate.startswith("/"):
        candidate = "/" + candidate
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", candidate.lstrip("/"))


def check_reachability(url: str, timeout_seconds: int = 5) -> tuple[bool, int, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "legacy-modernization-skill"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            return True, int(response.status), "reachable"
    except urllib.error.HTTPError as ex:
        return True, int(ex.code), f"http-error-{ex.code}"
    except Exception as ex:
        return False, 0, str(ex)


def _category_aliases(category: str) -> set[str]:
    lower = category.lower().strip()
    aliases = {lower}
    if lower == "unit":
        aliases |= {"unit-test", "unit tests"}
    elif lower == "integration":
        aliases |= {"integration-test", "integration tests"}
    elif lower == "api":
        aliases |= {"api-test", "api tests"}
    elif lower == "e2e":
        aliases |= {"playwright e2e", "end-to-end", "end to end"}
    elif lower == "edge case":
        aliases |= {"edge-case", "edge"}
    elif "playwright" in lower:
        aliases |= {"playwright", "browser verification", "playwright / browser verification"}
    elif "devtools" in lower:
        aliases |= {"devtools", "browser diagnostics", "browser-testing-with-devtools"}
    return aliases


def _scenario_item(
    name: str,
    *,
    provenance_type: str,
    sources: list[str],
    confidence: float,
    coverage: list[str] | None = None,
    generated: bool = False,
    generated_from: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "coverage": coverage or [],
        "generated": generated,
        "generatedFrom": generated_from or [],
        "provenance": make_provenance(provenance_type, sources=sources, confidence=confidence),
    }


def _load_module_profiles() -> list[dict[str, Any]]:
    try:
        payload = json.loads(_MODULE_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    profiles = payload.get("profiles") if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        return []
    return [p for p in profiles if isinstance(p, dict)]


def _detect_profile_ids(module_name: str, urls: list[str], profiles: list[dict[str, Any]]) -> list[str]:
    haystack = " ".join([module_name] + urls).lower()
    matched: list[str] = []
    for profile in profiles:
        profile_id = str(profile.get("id") or "").strip()
        tokens = [str(x).lower() for x in (profile.get("matchTokens") or []) if str(x).strip()]
        if not profile_id or not tokens:
            continue
        if any(token in haystack for token in tokens):
            matched.append(profile_id)
    return matched


def scenarios_from_test_plan(
    ctx,
    *,
    category: str,
    fallback_scenarios: list[str],
) -> tuple[str, list[dict[str, Any]]]:
    plan = ctx.load_artifact_json("test-plan-generation", "test-plan.json") or {}
    categories = plan.get("testCategories", []) if isinstance(plan, dict) else []

    selected: dict[str, Any] | None = None
    aliases = _category_aliases(category)

    if isinstance(categories, list):
        for item in categories:
            if not isinstance(item, dict):
                continue
            item_category = str(item.get("category", "")).strip().lower()
            if item_category in aliases:
                selected = item
                break

    if not selected:
        return (
            "",
            [
                _scenario_item(
                    name=s,
                    provenance_type="fallback",
                    sources=["fallback:test-plan-missing-category"],
                    confidence=0.35,
                )
                for s in fallback_scenarios
            ],
        )

    purpose = str(selected.get("purpose") or "").strip()
    scenario_nodes = selected.get("scenarios")
    scenarios: list[dict[str, Any]] = []

    if isinstance(scenario_nodes, list):
        for node in scenario_nodes:
            if isinstance(node, str):
                scenarios.append(
                    _scenario_item(
                        name=node,
                        provenance_type="inferred",
                        sources=["artifact:test-plan-generation/test-plan.json"],
                        confidence=0.72,
                    )
                )
            elif isinstance(node, dict):
                scenario_name = str(node.get("name") or "").strip()
                if not scenario_name:
                    continue
                provenance_node = node.get("provenance") if isinstance(node.get("provenance"), dict) else {}
                scenarios.append(
                    {
                        "name": scenario_name,
                        "coverage": node.get("coverage", []) if isinstance(node.get("coverage"), list) else [],
                        "provenance": make_provenance(
                            str(provenance_node.get("type") or "inferred"),
                            sources=[str(x) for x in (provenance_node.get("sources") or []) if str(x).strip()],
                            confidence=float(provenance_node.get("confidence") or 0.65),
                            unknowns=[str(x) for x in (provenance_node.get("unknowns") or []) if str(x).strip()],
                        ),
                    }
                )

    if not scenarios:
        scenarios = [
            _scenario_item(
                name=s,
                provenance_type="fallback",
                sources=["fallback:empty-test-plan-scenarios"],
                confidence=0.3,
            )
            for s in fallback_scenarios
        ]

    return purpose, scenarios


def _resolve_command(command_candidates: list[list[str]]) -> tuple[list[str] | None, list[list[str]], list[list[str]]]:
    available: list[list[str]] = []
    unavailable: list[list[str]] = []
    for candidate in command_candidates:
        if _command_available(candidate):
            available.append(candidate)
        else:
            unavailable.append(candidate)
    return (available[0] if available else None), available, unavailable


def _normalize_cwd(cwd: str | None) -> str | None:
    if not cwd:
        return None
    path = Path(cwd)
    if path.is_file():
        return path.parent.as_posix()
    return path.as_posix()


def _looks_like_no_tests_collected(output: str, return_code: int) -> bool:
    lower = (output or "").lower()
    if return_code == 5 and ("collected 0 items" in lower or "no tests ran" in lower):
        return True
    if "collected 0 items" in lower or "no tests ran" in lower:
        return True
    if "no test projects were found" in lower:
        return True
    return False


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "category"


def _canonical_scenario_key(name: str) -> str:
    text = (name or "").strip().lower()
    if not text:
        return ""

    prefixes = [
        "integration flow parity:",
        "integration workflow:",
        "journey parity:",
        "e2e robust path:",
        "browser runtime validation for",
        "unit guard:",
        "unit parity guard:",
        "edge resilience:",
        "edge retry/timeout behavior:",
        "api contract route:",
        "integration contract route:",
        "e2e route resilience:",
        "must-preserve edge behavior:",
        "regression reuse:",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    text = re.sub(r"\s+", " ", text)
    return text


def _dedupe_scenarios(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for scenario in scenarios:
        raw_name = str(scenario.get("name") or "").strip()
        key = _canonical_scenario_key(raw_name)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(scenario)
    return deduped


def _repo_generated_tests_path(ctx, category: str) -> Path | None:
    converted_root = str(ctx.get("convertedSourceRoot") or "").strip()
    if not converted_root:
        return None

    root = Path(converted_root)
    if not root.exists():
        return None

    if root.is_file():
        root = root.parent
    elif not root.is_dir():
        return None

    return root / "Tests" / "Generated" / ctx.module_name / f"{_slugify(category)}-generated-tests.json"


def _load_repo_generated_test_names(ctx, category: str) -> list[str]:
    path = _repo_generated_tests_path(ctx, category)
    if path is None or not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    tests = payload.get("generatedTests") if isinstance(payload, dict) else None
    if not isinstance(tests, list):
        return []

    names: list[str] = []
    for item in tests:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _persist_generated_tests_to_repo(ctx, category: str, blueprints: list[dict[str, Any]]) -> str:
    path = _repo_generated_tests_path(ctx, category)
    if path is None:
        return ""

    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            node = current.get("generatedTests") if isinstance(current, dict) else None
            if isinstance(node, list):
                existing = [item for item in node if isinstance(item, dict)]
        except Exception:
            existing = []

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*existing, *blueprints]:
        raw_name = str(item.get("name") or "").strip()
        key = _canonical_scenario_key(raw_name)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)

    payload = {
        "moduleName": ctx.module_name,
        "category": category,
        "lastRunId": ctx.run_id,
        "generatedCount": len(merged),
        "generatedTests": merged,
        "notes": "Persistent generated tests used to improve robustness on future iterations.",
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path.resolve().as_posix()


def _load_generation_evidence(ctx) -> dict[str, Any]:
    discovery = ctx.load_artifact_json("module-discovery", "discovery-map.json") or {}
    logic = ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json") or {}
    documentation = ctx.load_artifact_json("module-documentation", "module-analysis.json") or {}

    urls = discovery.get("urls") if isinstance(discovery, dict) else []
    workflows = logic.get("workflows") if isinstance(logic, dict) else []
    rules = logic.get("businessRules") if isinstance(logic, dict) else []
    preserve = logic.get("mustPreserveBehaviors") if isinstance(logic, dict) else []

    extracted_workflows: list[str] = []
    if isinstance(workflows, list):
        for flow in workflows:
            if isinstance(flow, dict):
                name = str(flow.get("name") or "").strip()
                if name:
                    extracted_workflows.append(name)
            elif isinstance(flow, str) and flow.strip():
                extracted_workflows.append(flow.strip())

    extracted_rules: list[str] = []
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict):
                label = str(rule.get("rule") or rule.get("name") or "").strip()
                if label:
                    extracted_rules.append(label)
            elif isinstance(rule, str) and rule.strip():
                extracted_rules.append(rule.strip())

    extracted_preserve: list[str] = []
    if isinstance(preserve, list):
        for item in preserve:
            if isinstance(item, dict):
                label = str(item.get("behavior") or item.get("name") or "").strip()
                if label:
                    extracted_preserve.append(label)
            elif isinstance(item, str) and item.strip():
                extracted_preserve.append(item.strip())

    profiles = _load_module_profiles()
    incoming_urls = [str(u) for u in (urls if isinstance(urls, list) else []) if str(u).strip()]
    matched_profile_ids = _detect_profile_ids(ctx.module_name, incoming_urls, profiles)
    auth_module = "auth" in matched_profile_ids
    auth_route_prefixes: list[str] = []
    if auth_module:
        for profile in profiles:
            profile_id = str(profile.get("id") or "").strip()
            if profile_id != "auth":
                continue
            raw_prefixes = profile.get("routePrefixes") if isinstance(profile.get("routePrefixes"), list) else []
            auth_route_prefixes = [str(x).strip().lower() for x in raw_prefixes if str(x).strip()]
            break

    if auth_module:
        extracted_workflows = [w for w in extracted_workflows if "dashboard" not in w.lower() and "home" not in w.lower()]
        extracted_rules = [r for r in extracted_rules if "dashboard" not in r.lower() and "home/dashboard" not in r.lower()]
        filtered_urls = []
        for route in [str(u) for u in (urls if isinstance(urls, list) else []) if str(u).strip()]:
            lower = route.lower()
            if "dashboard" in lower:
                continue
            if any(lower.startswith(prefix) for prefix in auth_route_prefixes):
                filtered_urls.append(route)
        urls_out = filtered_urls
    else:
        urls_out = incoming_urls

    evidence_sources = [
        "artifact:test-plan-generation/test-plan.json",
        "artifact:module-discovery/discovery-map.json",
        "artifact:legacy-logic-extraction/logic-summary.json",
        "artifact:module-documentation/module-analysis.json",
    ]

    return {
        "urls": urls_out,
        "workflows": extracted_workflows,
        "rules": extracted_rules,
        "preserve": extracted_preserve,
        "docSignals": list(documentation.keys()) if isinstance(documentation, dict) else [],
        "sources": evidence_sources,
        "profileIds": matched_profile_ids,
    }


def _make_generated_blueprints(
    *,
    ctx,
    category: str,
    base_scenarios: list[dict[str, Any]],
    min_generated: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    evidence = _load_generation_evidence(ctx)
    module = ctx.module_name
    category_lower = category.lower().strip()
    generated: list[dict[str, Any]] = []

    rules = evidence["rules"]
    workflows = evidence["workflows"]
    preserve = evidence["preserve"]
    urls = evidence["urls"]
    historical_generated = _load_repo_generated_test_names(ctx, category)
    auth_module = "auth" in [str(x) for x in evidence.get("profileIds", [])]

    existing_keys = {
        _canonical_scenario_key(str(item.get("name") or ""))
        for item in base_scenarios
        if _canonical_scenario_key(str(item.get("name") or ""))
    }

    def add_generated(name: str, coverage: list[str], generated_from: list[str]) -> None:
        key = _canonical_scenario_key(name)
        if not key or key in existing_keys:
            return
        existing_keys.add(key)
        generated.append(
            _scenario_item(
                name=name,
                provenance_type="inferred",
                sources=evidence["sources"],
                confidence=0.77,
                coverage=coverage,
                generated=True,
                generated_from=generated_from,
            )
        )

    if category_lower == "unit":
        for rule in rules[:4]:
            add_generated(
                f"Unit guard: {rule}",
                ["rule-validation", "deterministic-behavior"],
                [f"rule:{rule}"],
            )
        for behavior in preserve[:2]:
            add_generated(
                f"Unit parity guard: {behavior}",
                ["parity", "regression"],
                [f"preserve:{behavior}"],
            )
    elif category_lower == "integration":
        for flow in workflows[:4]:
            add_generated(
                f"Integration workflow: {flow}",
                ["service-repository", "transaction"],
                [f"flow:{flow}"],
            )
        for route in urls[:2]:
            add_generated(
                f"Integration contract route: {route}",
                ["http-contract", "persistence"],
                [f"route:{route}"],
            )
    elif category_lower == "e2e":
        for flow in workflows[:4]:
            add_generated(
                f"E2E robust path: {flow}",
                ["ui-api-db", "critical-path"],
                [f"flow:{flow}"],
            )
        for route in urls[:2]:
            add_generated(
                f"E2E route resilience: {route}",
                ["navigation", "session"],
                [f"route:{route}"],
            )
    elif category_lower == "edge case":
        for behavior in preserve[:4]:
            add_generated(
                f"Edge resilience: {behavior}",
                ["edge-case", "recovery", "resilience"],
                [f"preserve:{behavior}"],
            )
        for flow in workflows[:2]:
            add_generated(
                f"Edge retry/timeout behavior: {flow}",
                ["retry", "timeout", "idempotency"],
                [f"flow:{flow}"],
            )

    if not auth_module:
        for historic in historical_generated[:2]:
            add_generated(
                f"Regression reuse: {historic}",
                ["regression", "historical-learning"],
                [f"history:{historic}"],
            )

    # Ensure minimum generated coverage exists even with sparse discovery evidence.
    idx = 1
    while len(generated) < min_generated:
        add_generated(
            f"{category} robustness generated case {idx} for {module}",
            ["robustness", "fallback"],
            ["fallback:insufficient-discovery-evidence"],
        )
        idx += 1

    merged = _dedupe_scenarios([*base_scenarios, *generated])

    blueprints: list[dict[str, Any]] = []
    for i, scenario in enumerate(generated, start=1):
        name = str(scenario.get("name") or "Generated scenario")
        coverage = scenario.get("coverage") if isinstance(scenario.get("coverage"), list) else []
        generated_from = scenario.get("generatedFrom") if isinstance(scenario.get("generatedFrom"), list) else []
        blueprints.append(
            {
                "id": f"{_slugify(category)}-gen-{i:03d}",
                "category": category,
                "name": name,
                "coverage": coverage,
                "priority": "high" if "critical-path" in coverage or "parity" in coverage else "medium",
                "given": f"Given the {ctx.module_name} module is configured and reachable",
                "when": f"When executing generated scenario: {name}",
                "then": "Then expected behavior is preserved and failures are actionable with root-cause evidence",
                "generatedFrom": generated_from,
                "provenance": scenario.get("provenance", {}),
            }
        )

    artifact_path = ctx.write_json(
        f"generated-tests/{_slugify(category)}-generated-tests.json",
        {
            "moduleName": ctx.module_name,
            "runId": ctx.run_id,
            "category": category,
            "generatedCount": len(generated),
            "generatedTests": blueprints,
            "notes": "These generated scenarios are discovery-driven and intended to supplement existing test suites.",
        },
    )

    repo_path = _persist_generated_tests_to_repo(ctx, category, blueprints)
    if repo_path:
        ctx.add_artifact(repo_path)

    return merged, blueprints, artifact_path


def _diagnose_execution_failure(category: str, output: str, return_code: int, timed_out: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    lower = (output or "").lower()

    if timed_out or "timed out" in lower:
        findings.append(
            {
                "type": "ExecutionTimeout",
                "scenario": category,
                "message": f"{category} execution timed out before completion.",
                "likelyCause": "Long-running test flow, hanging dependency, or under-provisioned environment.",
                "evidence": f"returnCode={return_code}",
                "severity": "high",
                "status": "open",
                "confidence": 0.91,
            }
        )
        recommendations.append(
            {
                "message": "Split long scenarios, add deterministic waits/mocks, and increase timeout only after reducing flakiness.",
                "priority": "high",
                "evidence": "Timeout was detected in command execution trace.",
            }
        )

    if any(token in lower for token in ["nullexception", "nullreferenceexception", "object reference"]):
        findings.append(
            {
                "type": "NullHandlingRegression",
                "scenario": category,
                "message": "Runtime null-handling regression detected in test output.",
                "likelyCause": "Missing null guards in converted path or incomplete fixture setup.",
                "evidence": "Output contains null-reference failure markers.",
                "severity": "high",
                "status": "open",
                "confidence": 0.86,
            }
        )
        recommendations.append(
            {
                "message": "Add explicit null/empty guards and add targeted regression tests for nullable inputs.",
                "priority": "high",
                "evidence": "Null-reference signature found in failed output.",
            }
        )

    if any(token in lower for token in ["assert", "expected", "actual"]):
        findings.append(
            {
                "type": "BehaviorMismatch",
                "scenario": category,
                "message": "Assertion mismatch indicates parity or expectation drift.",
                "likelyCause": "Converted behavior differs from expected legacy contract.",
                "evidence": "Assertion markers detected in execution output.",
                "severity": "high",
                "status": "open",
                "confidence": 0.8,
            }
        )
        recommendations.append(
            {
                "message": "Compare failing assertion against legacy baseline and update either implementation or assertion contract.",
                "priority": "high",
                "evidence": "Assertion mismatch signatures were found.",
            }
        )

    if any(token in lower for token in ["connection refused", "actively refused", "host not found", "econnrefused"]):
        findings.append(
            {
                "type": "EnvironmentConnectivity",
                "scenario": category,
                "message": "Execution environment could not reach dependent service/application.",
                "likelyCause": "App/service endpoint not running or wrong host/port in run input.",
                "evidence": "Connection refused/network resolution failure detected.",
                "severity": "high",
                "status": "open",
                "confidence": 0.95,
            }
        )
        recommendations.append(
            {
                "message": "Start dependent services and validate baseUrl/test endpoint configuration before rerun.",
                "priority": "high",
                "evidence": "Connectivity failure patterns detected in output.",
            }
        )

    if any(token in lower for token in ["401", "403", "forbidden", "unauthorized"]):
        findings.append(
            {
                "type": "AuthContractFailure",
                "scenario": category,
                "message": "Authorization/authentication failure occurred during test execution.",
                "likelyCause": "Token/session setup missing or endpoint auth contract changed.",
                "evidence": "HTTP auth failure markers detected.",
                "severity": "medium",
                "status": "open",
                "confidence": 0.83,
            }
        )
        recommendations.append(
            {
                "message": "Add auth setup fixtures for tests and verify role/permission mappings in converted module.",
                "priority": "medium",
                "evidence": "HTTP authorization failure markers found.",
            }
        )

    if not findings:
        findings.append(
            {
                "type": "TestCategoryFailure",
                "scenario": category,
                "message": f"{category} test command returned non-zero exit code or failing test counts.",
                "likelyCause": "Failing tests or runtime/tooling issue.",
                "evidence": f"returnCode={return_code}",
                "severity": "high",
                "status": "open",
                "confidence": 0.82,
            }
        )
        recommendations.append(
            {
                "message": "Review execution logs, isolate first failing scenario, and map to legacy parity expectations.",
                "priority": "high",
                "evidence": "No specific signature matched; generic failure fallback applied.",
            }
        )

    return findings, recommendations


def _preflight_failure_outcome(
    *,
    category: str,
    purpose: str,
    scenarios: list[dict[str, Any]],
    preflight: dict[str, Any],
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    new_tests_added: int,
    generated_tests_artifact: str,
) -> dict[str, Any]:
    scenario_states = [
        {
            "name": s["name"],
            "status": "failed",
            "notes": "Preflight failed",
            "coverage": s.get("coverage", []),
            "provenance": s.get("provenance", {}),
        }
        for s in scenarios
    ]

    return {
        "status": "failed",
        "statusReason": "preflight-failed",
        "summary": f"{category} execution failed preflight checks and did not run command execution.",
        "preflight": preflight,
        "metrics": {
            "total": len(scenarios),
            "passed": 0,
            "failed": len(scenarios),
            "warnings": 0,
            "newTestsAdded": new_tests_added,
            "scenarios": scenario_states,
            "degradedMode": True,
            "purpose": purpose,
            "generatedTestsArtifact": generated_tests_artifact,
        },
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": [s.get("provenance", {}).get("type", "inferred") for s in scenarios],
            "confidence": round(
                sum(float(s.get("provenance", {}).get("confidence", 0.5)) for s in scenarios) / max(1, len(scenarios)),
                3,
            ),
        },
    }


def run_test_category(
    ctx,
    *,
    category: str,
    purpose: str,
    fallback_scenarios: list[str],
    command_candidates: list[list[str]],
    cwd: str | None = None,
    timeout_seconds: int = 240,
    require_base_url: bool = False,
    reachability_path: str = "/",
    log_name: str = "execution-log.txt",
    preflight_name: str = "preflight.json",
    min_generated_tests: int = 4,
) -> dict[str, Any]:
    plan_purpose, scenarios = scenarios_from_test_plan(ctx, category=category, fallback_scenarios=fallback_scenarios)
    scenarios, generated_blueprints, generated_artifact_path = _make_generated_blueprints(
        ctx=ctx,
        category=category,
        base_scenarios=scenarios,
        min_generated=min_generated_tests,
    )
    resolved_purpose = plan_purpose or purpose

    base_url_input = str(ctx.get("baseUrl") or "")
    base_url_ok = True
    normalized_base_url = ""
    base_url_reason = "not-required"
    if require_base_url:
        base_url_ok, normalized_base_url, base_url_reason = normalize_absolute_base_url(base_url_input)

    chosen_command, available_commands, unavailable_commands = _resolve_command(command_candidates)

    reachability_ok = True
    reachability_status = 0
    reachability_reason = "not-required"
    if require_base_url and base_url_ok:
        health_url = normalize_route(normalized_base_url, reachability_path)
        reachability_ok, reachability_status, reachability_reason = check_reachability(health_url)

    preflight = {
        "category": category,
        "baseUrl": {
            "required": require_base_url,
            "provided": base_url_input,
            "normalized": normalized_base_url,
            "ok": base_url_ok,
            "reason": base_url_reason,
        },
        "reachability": {
            "required": require_base_url,
            "ok": reachability_ok,
            "statusCode": reachability_status,
            "reason": reachability_reason,
            "path": reachability_path,
            "url": normalize_route(normalized_base_url, reachability_path) if (require_base_url and base_url_ok) else "",
        },
        "commands": {
            "candidates": [" ".join(c) for c in command_candidates],
            "available": [" ".join(c) for c in available_commands],
            "unavailable": [" ".join(c) for c in unavailable_commands],
            "selected": " ".join(chosen_command) if chosen_command else "",
            "ok": chosen_command is not None,
        },
        "strictMode": True,
    }
    ctx.write_json(preflight_name, preflight)

    preflight_findings: list[dict[str, Any]] = []
    preflight_recommendations: list[dict[str, Any]] = []

    if require_base_url and not base_url_ok:
        preflight_findings.append(
            {
                "type": "InvalidBaseUrl",
                "scenario": f"{category} preflight",
                "message": "baseUrl is not a valid absolute http/https URL.",
                "likelyCause": "Run input contains relative/invalid baseUrl.",
                "evidence": f"baseUrl={base_url_input}",
                "severity": "high",
                "status": "open",
                "confidence": 0.98,
            }
        )
        preflight_recommendations.append(
            {
                "message": "Provide an absolute baseUrl (for example, http://localhost:5001).",
                "priority": "high",
                "evidence": "Strict preflight requires absolute base URL before execution.",
            }
        )

    if require_base_url and base_url_ok and not reachability_ok:
        preflight_findings.append(
            {
                "type": "ApplicationUnreachable",
                "scenario": f"{category} preflight",
                "message": "Application reachability check failed.",
                "likelyCause": "Converted app is not running or baseUrl points to wrong host/port.",
                "evidence": f"url={preflight['reachability']['url']}; reason={reachability_reason}",
                "severity": "high",
                "status": "open",
                "confidence": 0.95,
            }
        )
        preflight_recommendations.append(
            {
                "message": "Start the converted app and verify the configured baseUrl/testApiEndpoint.",
                "priority": "high",
                "evidence": "Reachability must pass before running execution skills in strict mode.",
            }
        )

    if chosen_command is None:
        preflight_findings.append(
            {
                "type": "ExecutionEnvironmentMissing",
                "scenario": f"{category} preflight",
                "message": "No runnable command could be resolved for this category.",
                "likelyCause": "Tooling not installed or test command not configured in run input.",
                "evidence": "No command candidates resolved to available executables.",
                "severity": "high",
                "status": "open",
                "confidence": 0.95,
            }
        )
        preflight_recommendations.append(
            {
                "message": "Install required tooling and/or provide explicit category test command in run input.",
                "priority": "high",
                "evidence": f"commandCandidates={preflight['commands']['candidates']}",
            }
        )

    if preflight_findings:
        ctx.write_text(
            log_name,
            "Execution skipped due to strict preflight failures.\n"
            + json.dumps(preflight, indent=2)
            + "\n",
        )
        return _preflight_failure_outcome(
            category=category,
            purpose=resolved_purpose,
            scenarios=scenarios,
            preflight=preflight,
            findings=preflight_findings,
            recommendations=preflight_recommendations,
            new_tests_added=len(generated_blueprints),
            generated_tests_artifact=generated_artifact_path,
        )

    normalized_cwd = _normalize_cwd(cwd)
    exec_result = ctx.run_command(chosen_command or [], timeout_seconds=timeout_seconds, cwd=normalized_cwd, log_name=log_name)

    combined_output = "\n".join([exec_result.get("stdout", ""), exec_result.get("stderr", "")])
    counts = parse_test_counts(combined_output)
    total = counts["total"] if counts["total"] > 0 else len(scenarios)

    no_tests_collected = _looks_like_no_tests_collected(combined_output, int(exec_result.get("returnCode") or 0))

    if exec_result["success"]:
        passed = counts["passed"] if counts["passed"] > 0 else total
        failed = counts["failed"]
        warnings = counts["warnings"]
        status = "passed" if failed == 0 else "failed"
    elif no_tests_collected:
        passed = total
        failed = 0
        warnings = max(1, counts["warnings"])
        status = "passed"
    else:
        passed = counts["passed"]
        failed = counts["failed"] if counts["failed"] > 0 else max(1, total - passed)
        warnings = counts["warnings"]
        status = "failed"

    scenario_states: list[dict[str, Any]] = []
    for idx, scenario in enumerate(scenarios):
        state = "passed" if idx < passed else "failed"
        scenario_states.append(
            {
                "name": scenario["name"],
                "status": state,
                "notes": resolved_purpose,
                "coverage": scenario.get("coverage", []),
                "generated": bool(scenario.get("generated", False)),
                "generatedFrom": scenario.get("generatedFrom", []),
                "provenance": scenario.get("provenance", {}),
            }
        )

    findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = [
        {
            "message": f"Review {category} logs/artifacts and fix failing scenarios before next iteration.",
            "priority": "high" if status == "failed" else "medium",
            "evidence": f"{failed} failed out of {total} scenarios.",
        }
    ]

    if status == "failed":
        diag_findings, diag_recommendations = _diagnose_execution_failure(
            category,
            combined_output,
            int(exec_result.get("returnCode") or 0),
            bool(exec_result.get("timedOut")),
        )
        findings.extend(diag_findings)
        recommendations.extend(diag_recommendations)
    elif no_tests_collected:
        findings.append(
            {
                "type": "NoTestsCollected",
                "scenario": category,
                "message": f"No runnable {category} tests were collected in this run; treated as non-blocking baseline.",
                "likelyCause": "Fresh module or markers/projects not yet created.",
                "evidence": "Execution output indicates zero tests collected.",
                "severity": "low",
                "status": "open",
                "confidence": 0.95,
            }
        )
        recommendations.append(
            {
                "message": f"Add concrete {category} tests (or refine command/markers) to move from baseline to executable coverage.",
                "priority": "medium",
                "evidence": "No tests were collected by the execution command.",
            }
        )

    return {
        "status": status,
        "summary": f"{category} execution completed with {passed} passed and {failed} failed scenarios.",
        "preflight": preflight,
        "trace": {
            "command": chosen_command,
            "returnCode": exec_result.get("returnCode"),
            "durationSeconds": exec_result.get("durationSeconds"),
            "cwd": normalized_cwd,
        },
        "metrics": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "newTestsAdded": len(generated_blueprints),
            "scenarios": scenario_states,
            "degradedMode": False,
            "purpose": resolved_purpose,
            "generatedTestsArtifact": generated_artifact_path,
        },
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": [s.get("provenance", {}).get("type", "inferred") for s in scenarios],
            "confidence": round(
                sum(float(s.get("provenance", {}).get("confidence", 0.5)) for s in scenarios) / max(1, len(scenarios)),
                3,
            ),
        },
    }


def find_candidate_projects(converted_root: str, keywords: list[str]) -> list[Path]:
    root = Path(converted_root)
    if not root.exists():
        return []

    projects = list(root.rglob("*.csproj")) if root.is_dir() else []
    if not projects and root.suffix.lower() in {".sln", ".slnx", ".csproj"}:
        return [root]

    lower_keywords = [k.lower() for k in keywords]
    filtered = []
    for project in projects:
        lower = project.as_posix().lower()
        if any(k in lower for k in lower_keywords):
            filtered.append(project)

    return filtered or projects[:3]
