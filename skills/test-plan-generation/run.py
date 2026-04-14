#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill
from skill_logic import infer_flows_from_urls

SPEC = {
    "name": "test-plan-generation",
    "stage": "test-plan",
    "requiredInputs": ["moduleName", "convertedSourceRoot"],
}

PROFILE_PATH = Path(__file__).resolve().parents[1] / "legacy-logic-extraction" / "module-profiles.json"


def _load_profiles() -> list[dict]:
    try:
        payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    profiles = payload.get("profiles") if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        return []
    return [p for p in profiles if isinstance(p, dict)]


def _detect_profile_ids(module_name: str, discovery: dict, profiles: list[dict]) -> list[str]:
    haystack = " ".join(
        [module_name]
        + [str(x) for x in (discovery.get("urls") or [])]
        + [str(x) for x in (discovery.get("javaFiles") or [])]
        + [str(x) for x in (discovery.get("jspFiles") or [])]
    ).lower()

    matched: list[str] = []
    for profile in profiles:
        profile_id = str(profile.get("id") or "").strip()
        tokens = [str(x).lower() for x in (profile.get("matchTokens") or []) if str(x).strip()]
        if not profile_id or not tokens:
            continue
        if any(token in haystack for token in tokens):
            matched.append(profile_id)
    return matched


def _load_lessons_kb(ctx) -> dict:
    kb_path = ctx.artifacts_root / ctx.module_name / "_knowledge-base" / "lessons-kb.json"
    if not kb_path.exists():
        return {}
    try:
        import json

        data = json.loads(kb_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _scenario(name: str, coverage: list[str], provenance_type: str, sources: list[str], confidence: float) -> dict:
    return {
        "name": name,
        "coverage": coverage,
        "provenance": make_provenance(provenance_type, sources=sources, confidence=confidence),
    }


def _category(name: str, purpose: str, scenarios: list[dict]) -> dict:
    return {"category": name, "purpose": purpose, "scenarios": scenarios}


def execute(ctx):
    scope = ctx.resolve_scope()
    discovery = ctx.load_artifact_json("module-discovery", "discovery-map.json") or {}
    logic = ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json") or {}
    architecture = ctx.load_artifact_json("clean-architecture-assessment", "architecture-review.json") or {}
    lessons_kb = _load_lessons_kb(ctx)
    profiles = _load_profiles()
    matched_profile_ids = _detect_profile_ids(ctx.module_name, discovery, profiles)

    module_tokens = [ctx.module_name.lower()]
    for profile in profiles:
        if str(profile.get("id") or "") not in matched_profile_ids:
            continue
        module_tokens.extend([str(x).lower() for x in (profile.get("matchTokens") or []) if str(x).strip()])
    module_tokens = list(dict.fromkeys([t for t in module_tokens if t]))

    raw_urls = discovery.get("urls", []) or scope.get("urls", [])
    urls = []
    for route in raw_urls:
        text = str(route).strip()
        lower = text.lower()
        if not text.startswith("/"):
            continue
        if lower.startswith("/views/") or lower.startswith("/wwwroot/"):
            continue
        if any(lower.endswith(ext) for ext in [".cshtml", ".jsp", ".java", ".js", ".ts", ".json", ".xml", ".md"]):
            continue
        if not any(token in lower for token in module_tokens):
            continue
        urls.append(text)
    workflows = logic.get("workflows", []) if isinstance(logic.get("workflows"), list) else []
    if not workflows:
        inferred = logic.get("importantFlows", []) or infer_flows_from_urls(urls)
        workflows = [
            {
                "name": flow,
                "provenance": make_provenance("inferred", sources=["artifact:legacy-logic-extraction/logic-summary.json"], confidence=0.64),
            }
            for flow in inferred
        ]

    rules = logic.get("businessRules", []) if isinstance(logic.get("businessRules"), list) else []
    must_preserve = logic.get("mustPreserveBehaviors", []) if isinstance(logic.get("mustPreserveBehaviors"), list) else []

    test_files = scope.get("testFiles", [])
    unit_tests = [p for p in test_files if "unit" in p.lower()]
    integration_tests = [p for p in test_files if "integration" in p.lower()]
    api_tests = [p for p in test_files if "api" in p.lower()]
    e2e_tests = [p for p in test_files if "e2e" in p.lower() or "playwright" in p.lower()]

    workflow_names = [str(w.get("name") or "") if isinstance(w, dict) else str(w) for w in workflows]
    workflow_names = [w for w in workflow_names if w]
    if matched_profile_ids:
        workflow_names = [
            w for w in workflow_names
            if any(token in w.lower() for token in module_tokens)
        ] or workflow_names
    preserve_names = [m.get("behavior", "") if isinstance(m, dict) else str(m) for m in must_preserve]
    preserve_names = [p for p in preserve_names if p]

    recurring_signatures = lessons_kb.get("recurringSignatures", []) if isinstance(lessons_kb.get("recurringSignatures"), list) else []

    categories = [
        _category(
            "Unit",
            "Validate module business rules and validators in isolation.",
            [
                _scenario(
                    f"Rule guard: {rule.get('rule', 'business-rule') if isinstance(rule, dict) else str(rule)}",
                    coverage=["rule-validation"],
                    provenance_type="flow-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json"],
                    confidence=0.78,
                )
                for rule in (rules[:3] or [{"rule": f"{ctx.module_name} rule coverage fallback"}])
            ],
        ),
        _category(
            "Integration",
            "Validate cross-layer orchestration, persistence contracts, and transaction behavior.",
            [
                _scenario(
                    f"Integration flow parity: {flow}",
                    coverage=["service-repository", "transaction"],
                    provenance_type="flow-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json"],
                    confidence=0.75,
                )
                for flow in (workflow_names[:3] or [f"{ctx.module_name} integration fallback scenario"])
            ],
        ),
        _category(
            "API",
            "Validate HTTP route compatibility, request/response contracts, and validation behavior.",
            [
                _scenario(
                    f"API contract route: {route}",
                    coverage=["http-contract"],
                    provenance_type="code-evidence",
                    sources=["artifact:module-discovery/discovery-map.json"],
                    confidence=0.81,
                )
                for route in (urls[:3] or [f"/{ctx.module_name.lower()}/fallback"])
            ],
        ),
        _category(
            "E2E",
            "Validate full critical journeys from browser entrypoint to backend persistence.",
            [
                _scenario(
                    f"Journey parity: {flow}",
                    coverage=["critical-path", "ui-api-db"],
                    provenance_type="flow-derived",
                    sources=["artifact:module-documentation/module-analysis.json"],
                    confidence=0.73,
                )
                for flow in (workflow_names[:3] or [f"{ctx.module_name} E2E fallback"])
            ],
        ),
        _category(
            "Edge Case",
            "Validate boundary conditions, Dapper case-sensitivity, ViewModel binding, retries, and low-frequency high-impact paths.",
            [
                _scenario(
                    f"Must-preserve edge behavior: {item}",
                    coverage=["edge-case", "resilience", "dapper-case-sensitivity", "viewmodel-binding"],
                    provenance_type="risk-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json"],
                    confidence=0.76,
                )
                for item in (preserve_names[:3] or [f"{ctx.module_name} edge fallback scenario"])
            ]
            + [
                _scenario(
                    "Dapper case-sensitivity and column mapping edge cases",
                    coverage=["dapper", "orm", "case-sensitivity"],
                    provenance_type="risk-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json"],
                    confidence=0.72,
                ),
                _scenario(
                    "ViewModel binding and property mapping validation",
                    coverage=["viewmodel", "binding", "dto-mapping"],
                    provenance_type="risk-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json"],
                    confidence=0.70,
                ),
            ],
        ),
        _category(
            "Playwright / E2E Browser",
            "Validate browser UX/runtime/network/DOM evidence for migrated module journeys.",
            [
                _scenario(
                    f"Browser runtime validation for {flow}",
                    coverage=["browser-runtime", "network", "dom"],
                    provenance_type="flow-derived",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json", "artifact:module-discovery/discovery-map.json"],
                    confidence=0.72,
                )
                for flow in (workflow_names[:2] or [f"{ctx.module_name} browser fallback"]) 
            ],
        ),
        _category(
            "DevTools Diagnostics",
            "Inspect console, network, runtime, DOM state, and performance evidence for root-cause diagnostics.",
            [
                _scenario(
                    "Collect console error/warning evidence",
                    coverage=["console"],
                    provenance_type="flow-derived",
                    sources=["artifact:playwright-browser-verification/result.json"],
                    confidence=0.68,
                ),
                _scenario(
                    "Collect failed request evidence and latency outliers",
                    coverage=["network", "performance"],
                    provenance_type="flow-derived",
                    sources=["artifact:playwright-browser-verification/result.json"],
                    confidence=0.68,
                ),
            ],
        ),
    ]

    if recurring_signatures:
        categories[4]["scenarios"].append(
            _scenario(
                f"Recurring risk regression guard: {recurring_signatures[0]}",
                coverage=["lessons-regression"],
                provenance_type="lessons-derived",
                sources=["artifact:_knowledge-base/lessons-kb.json"],
                confidence=0.8,
            )
        )

    # Mark fallback provenance explicitly if coverage source evidence is thin.
    if not urls:
        for scenario in categories[2]["scenarios"]:
            scenario["provenance"] = make_provenance(
                "fallback",
                sources=["fallback:no-url-evidence"],
                confidence=0.35,
                unknowns=["Discovery stage did not provide route candidates"],
            )

    existing_tests = len(test_files)
    covered_categories = sum(1 for bucket in [unit_tests, integration_tests, api_tests, e2e_tests] if bucket)

    architecture_risks = 0
    if isinstance(architecture, dict):
        for key in ["cleanArchitectureIssues", "namespaceFolderIssues", "diIssues", "couplingIssues"]:
            if isinstance(architecture.get(key), list):
                architecture_risks += len(architecture.get(key))

    coverage_percent = max(20, min(96, 35 + covered_categories * 12 + min(existing_tests, 50) // 2 - min(architecture_risks, 10)))

    new_tests_suggested = [
        f"Add parity scenario for workflow: {flow}" for flow in workflow_names[:6]
    ]
    for signature in recurring_signatures[:4]:
        new_tests_suggested.append(f"Add regression guard for recurring issue: {signature}")

    plan = {
        "moduleName": ctx.module_name,
        "existingTestsFound": {
            "totalFiles": existing_tests,
            "unit": len(unit_tests),
            "integration": len(integration_tests),
            "api": len(api_tests),
            "e2e": len(e2e_tests),
            "sampleFiles": test_files[:80],
            "provenance": make_provenance("code-evidence", sources=test_files[:30], confidence=0.85 if existing_tests else 0.4),
        },
        "newTestsSuggested": new_tests_suggested[:40],
        "testCategories": categories,
        "coverageSummary": f"Estimated coverage baseline for {ctx.module_name}: {coverage_percent}%.",
        "confidence": 0.82 if workflows and (rules or urls) else 0.55,
    }

    ctx.write_json("test-plan.json", plan)

    return {
        "status": "passed",
        "summary": (
            f"Test plan generated for {ctx.module_name} with categories={len(categories)} "
            f"and suggestedTests={len(new_tests_suggested[:40])}."
        ),
        "metrics": {
            "existingTests": existing_tests,
            "suggestedTests": len(new_tests_suggested[:40]),
            "coveragePercent": coverage_percent,
            "architectureRisks": architecture_risks,
        },
        "findings": [],
        "recommendations": [
            {
                "message": "Prioritize scenarios sourced from must-preserve behaviors and recurring lessons before parity signoff.",
                "priority": "high",
                "evidence": "Test categories now include provenance for flow/risk/fallback/lessons origins.",
            }
        ],
        "provenanceSummary": {
            "scenarioSources": ["flow-derived", "risk-derived", "lessons-derived", "fallback"],
            "confidence": plan["confidence"],
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
