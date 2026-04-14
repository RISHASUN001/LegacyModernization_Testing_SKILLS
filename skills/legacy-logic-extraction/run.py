#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill
from skill_logic import build_dependencies, infer_flows_from_urls, infer_rules_from_touchpoints, title_case_module

SPEC = {
    "name": "legacy-logic-extraction",
    "stage": "logic-understanding",
    "requiredInputs": ["moduleName", "legacySourceRoot"],
}

PROFILE_PATH = Path(__file__).with_name("module-profiles.json")


def _workflow(flow_name: str, trigger_sources: list[str], module_name: str) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "-", flow_name.lower()).strip("-") or "flow"
    return {
        "id": f"{module_name.lower()}-{slug}",
        "name": flow_name,
        "steps": [
            {"name": "Trigger route/view", "expectedOutcome": "User enters module flow"},
            {"name": "Validation and rule checks", "expectedOutcome": "Invalid states are rejected"},
            {"name": "Persistence/service action", "expectedOutcome": "State is persisted consistently"},
            {"name": "Response/UI transition", "expectedOutcome": "User-visible behavior matches legacy"},
        ],
        "preserveCriticality": "high",
        "provenance": make_provenance("inferred", sources=trigger_sources, confidence=0.72),
    }


def _load_profiles() -> list[dict]:
    try:
        payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    profiles = payload.get("profiles") if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        return []
    return [p for p in profiles if isinstance(p, dict)]


def _detect_context(module_name: str, discovery: dict, profiles: list[dict]) -> list[str]:
    haystack = " ".join(
        [module_name]
        + [str(x) for x in (discovery.get("urls") or [])]
        + [str(x) for x in (discovery.get("javaFiles") or [])]
        + [str(x) for x in (discovery.get("jspFiles") or [])]
    ).lower()

    tags: list[str] = []
    for profile in profiles:
        profile_id = str(profile.get("id") or "").strip()
        tokens = [str(x).lower() for x in (profile.get("matchTokens") or []) if str(x).strip()]
        if not profile_id or not tokens:
            continue
        if any(token in haystack for token in tokens):
            tags.append(profile_id)
    return tags


def _profile_by_id(profile_id: str, profiles: list[dict]) -> dict:
    for profile in profiles:
        if str(profile.get("id") or "").strip().lower() == profile_id.lower():
            return profile
    return {}


def _module_specific_flows(context_profile: dict) -> list[str]:
    flows = context_profile.get("flows")
    if not isinstance(flows, list):
        return []
    return [str(x).strip() for x in flows if str(x).strip()]


def _module_specific_rules(context_profile: dict) -> list[str]:
    rules = context_profile.get("rules")
    if not isinstance(rules, list):
        return []
    return [str(x).strip() for x in rules if str(x).strip()]


def _scope_terms(ctx, discovery: dict) -> list[str]:
    scope = ctx.resolve_scope().get("scopeContext", {}) if isinstance(ctx.resolve_scope().get("scopeContext"), dict) else {}
    terms = [str(x).lower() for x in (scope.get("scopeTokens") or []) if str(x).strip()]

    target_url = str(ctx.get("targetUrl") or "").strip().lower()
    terms.extend([p for p in re.split(r"[^a-z0-9]+", target_url) if len(p) >= 2])

    hint = str(ctx.get("moduleHints.scopeHint") or "").strip().lower()
    terms.extend([p for p in re.split(r"[^a-z0-9]+", hint) if len(p) >= 2])

    known_urls = discovery.get("urls") if isinstance(discovery.get("urls"), list) else []
    terms.extend([p for u in known_urls for p in re.split(r"[^a-z0-9]+", str(u).lower()) if len(p) >= 2])
    return sorted(set(terms))


def _filter_by_scope(items: list[str], terms: list[str]) -> list[str]:
    if not terms:
        return items
    filtered = [item for item in items if any(term in item.lower() for term in terms)]
    return filtered or items


def execute(ctx):
    discovery = ctx.load_artifact_json("module-discovery", "discovery-map.json") or {}
    if not discovery:
        scope = ctx.resolve_scope()
        discovery = {
            "urls": scope.get("urls", []),
            "dbTouchpoints": scope.get("dbTouchpoints", []),
            "javaFiles": scope.get("javaFiles", []),
            "jspFiles": scope.get("jspFiles", []),
            "jsFiles": scope.get("jsFiles", []),
            "entrypointHints": [],
        }

    profiles = _load_profiles()
    urls = discovery.get("urls", []) if isinstance(discovery.get("urls"), list) else []
    db_touchpoints = discovery.get("dbTouchpoints", []) if isinstance(discovery.get("dbTouchpoints"), list) else []
    has_js = bool(discovery.get("jsFiles", []))
    context_tags = _detect_context(ctx.module_name, discovery, profiles)
    context_profile = _profile_by_id(context_tags[0], profiles) if context_tags else {}

    module_title = title_case_module(ctx.module_name)
    scope_terms = _scope_terms(ctx, discovery)
    inferred_flows = _module_specific_flows(context_profile) or infer_flows_from_urls(urls)
    inferred_flows = _filter_by_scope(inferred_flows, scope_terms)
    dependencies = build_dependencies(ctx.resolve_scope())

    workflows = [_workflow(flow, urls[:6], ctx.module_name) for flow in inferred_flows]
    if not workflows:
        workflows = [
            {
                "id": f"{ctx.module_name.lower()}-fallback-critical-flow",
                "name": f"{ctx.module_name} core workflow",
                "steps": [
                    {"name": "Open module", "expectedOutcome": "Module entry loads"},
                    {"name": "Perform operation", "expectedOutcome": "Business action executes"},
                    {"name": "Persist and return", "expectedOutcome": "State change is durable"},
                ],
                "preserveCriticality": "high",
                "provenance": make_provenance(
                    "fallback",
                    sources=["fallback:no-url-derived-workflows"],
                    confidence=0.42,
                    unknowns=["No route evidence found in discovery stage"],
                ),
            }
        ]

    raw_rules = _module_specific_rules(context_profile) or infer_rules_from_touchpoints(db_touchpoints, has_js)
    raw_rules = _filter_by_scope(raw_rules, scope_terms)
    business_rules = []
    for idx, rule in enumerate(raw_rules, start=1):
        business_rules.append(
            {
                "id": f"R-{idx:03d}",
                "rule": rule,
                "rationale": "Derived from discovered module assets and persistence/client-side signals.",
                "provenance": make_provenance(
                    "inferred",
                    sources=(db_touchpoints[:4] if db_touchpoints else urls[:4]) or ["artifact:module-discovery/discovery-map.json"],
                    confidence=0.74,
                ),
            }
        )

    must_preserve = [
        {
            "behavior": "Route and URL behavior parity for user-visible flows",
            "criticality": "high",
            "provenance": make_provenance("code-evidence", sources=urls[:8], confidence=0.8),
        },
        {
            "behavior": "Validation/error message semantics from legacy behavior",
            "criticality": "high",
            "provenance": make_provenance("code-evidence", sources=discovery.get("javaFiles", [])[:8], confidence=0.78),
        },
        {
            "behavior": "Data mapping compatibility for persistence operations (Dapper case-sensitivity, ViewModel binding)",
            "criticality": "high",
            "provenance": make_provenance("code-evidence", sources=db_touchpoints[:8] or discovery.get("csharpFiles", [])[:8], confidence=0.82),
        },
        {
            "behavior": "Session/cookie handling and user context preservation across requests",
            "criticality": "high",
            "provenance": make_provenance("inferred", sources=discovery.get("javaFiles", [])[:4], confidence=0.75),
        },
    ]
    if db_touchpoints:
        must_preserve.append(
            {
                "behavior": "SQL query parameter ordering and table interaction sequencing",
                "criticality": "medium",
                "provenance": make_provenance("code-evidence", sources=db_touchpoints[:6], confidence=0.76),
            }
        )
    profile_preserve = context_profile.get("mustPreserve") if isinstance(context_profile.get("mustPreserve"), list) else []
    for behavior in profile_preserve:
        text = str(behavior).strip()
        if not text:
            continue
        must_preserve.append(
            {
                "behavior": text,
                "criticality": "high",
                "provenance": make_provenance("inferred", sources=urls[:4], confidence=0.79),
            }
        )

    unknowns = []
    if not urls:
        unknowns.append("No route/URL evidence discovered; workflow trigger confidence is reduced.")
    if not db_touchpoints:
        unknowns.append("No DB touchpoint extracted; persistence parity must be confirmed with runtime logs.")

    confidence = 0.86 if urls and (db_touchpoints or has_js) else 0.63

    java_files_sample = discovery.get("javaFiles", [])[:12]
    csharp_files_sample = ctx.resolve_scope().get("csharpFiles", [])[:12]
    
    logic_summary = {
        "moduleName": ctx.module_name,
        "discoveredJavaFiles": java_files_sample,
        "convertedCSharpFiles": csharp_files_sample,
        "discoveredUrls": urls[:8],
        "discoveredDbTouchpoints": db_touchpoints[:8],
        "modulePurpose": {
            "text": (
                str(context_profile.get("purposeTemplate") or "")
                .replace("{moduleTitle}", module_title)
                .replace("{javaCount}", str(len(java_files_sample)))
                .replace("{topRoutes}", ', '.join(urls[:3]) if urls else 'none')
                .replace("{topDbTouchpoints}", ', '.join(db_touchpoints[:3]) if db_touchpoints else 'none')
                if context_profile
                else f"{module_title} module orchestrates legacy-compatible business workflows. "
                f"Java assets: {len(java_files_sample)}, Routes: {len(urls)}, DB: {len(db_touchpoints)}.  Converted to C#: {len(csharp_files_sample)} files."
            ),
            "provenance": make_provenance(
                "code-evidence",
                sources=java_files_sample[:8] + ["artifact:module-discovery/discovery-map.json"],
                confidence=0.78,
            ),
        },
        "workflows": workflows,
        "businessRules": business_rules,
        "dependencies": [
            {
                "name": dep,
                "provenance": make_provenance("code-evidence", sources=["file-path-patterns"], confidence=0.68),
            }
            for dep in dependencies
        ],
        "mustPreserveBehaviors": must_preserve,
        "unknowns": unknowns,
        "confidence": confidence,
        "sourceEvidence": {
            "urls": urls[:30],
            "dbTouchpoints": db_touchpoints[:30],
            "legacyFiles": (discovery.get("javaFiles", []) + discovery.get("jspFiles", []) + discovery.get("jsFiles", []))[:80],
        },
        "scopeApplied": {
            "scopeTerms": scope_terms[:30],
            "targetUrl": str(ctx.get("targetUrl") or ""),
            "scopeHint": str(ctx.get("moduleHints.scopeHint") or ""),
        },
        # Backward-compatible keys for existing readers.
        "importantFlows": [w["name"] for w in workflows],
        "rules": [r["rule"] for r in business_rules],
        "dependenciesText": dependencies,
        "mustPreserve": [m["behavior"] for m in must_preserve],
    }

    ctx.write_json("logic-summary.json", logic_summary)

    recommendations = [
        {
            "message": "Use workflow and must-preserve behavior items as the source-of-truth for test scenario generation.",
            "priority": "high",
            "evidence": "Logic extraction now emits evidence-scoped workflows and rule artifacts.",
        }
    ]

    return {
        "status": "passed",
        "summary": (
            f"Logic extraction completed for {ctx.module_name}: workflows={len(workflows)}, "
            f"rules={len(business_rules)}, unknowns={len(unknowns)}."
        ),
        "metrics": {
            "flows": len(workflows),
            "rules": len(business_rules),
            "dependencies": len(dependencies),
            "preserveItems": len(must_preserve),
            "unknowns": len(unknowns),
            "confidence": confidence,
        },
        "findings": [],
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "inferred"],
            "confidence": confidence,
            "unknowns": unknowns,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
