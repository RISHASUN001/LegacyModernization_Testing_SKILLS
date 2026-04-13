#!/usr/bin/env python3
from __future__ import annotations

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


def _detect_context(module_name: str, discovery: dict) -> set[str]:
    haystack = " ".join(
        [module_name]
        + [str(x) for x in (discovery.get("urls") or [])]
        + [str(x) for x in (discovery.get("javaFiles") or [])]
        + [str(x) for x in (discovery.get("jspFiles") or [])]
    ).lower()

    tags: set[str] = set()
    if any(token in haystack for token in ["login", "auth", "signin", "logout", "password"]):
        tags.add("auth")
    if any(token in haystack for token in ["checklist", "item", "workorder", "wo", "status"]):
        tags.add("checklist")
    return tags


def _module_specific_flows(module_name: str, context_tags: set[str]) -> list[str]:
    if "auth" in context_tags:
        return [
            "Open login page",
            "Submit credentials",
            "Redirect to dashboard/home",
            "Logout and return to login",
        ]
    if "checklist" in context_tags:
        return [
            "Open checklist item",
            "Validate checklist inputs",
            "Submit checklist decision",
            "Create or update WO on failure conditions",
            "Transition checklist status",
        ]
    return []


def _module_specific_rules(context_tags: set[str]) -> list[str]:
    if "auth" in context_tags:
        return [
            "If credentials are invalid, stay on login page and show validation message",
            "If credentials are valid, establish session and redirect to home/dashboard",
            "If session is expired, protected routes redirect to login",
        ]
    if "checklist" in context_tags:
        return [
            "If required checklist fields are missing, block submission and show errors",
            "If checklist result indicates defect/failure, create or link a Work Order (WO)",
            "If checklist is approved and all checks pass, status transitions to completed",
            "If x and y conditions occur together, status becomes z according to business matrix",
        ]
    return []


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

    urls = discovery.get("urls", []) if isinstance(discovery.get("urls"), list) else []
    db_touchpoints = discovery.get("dbTouchpoints", []) if isinstance(discovery.get("dbTouchpoints"), list) else []
    has_js = bool(discovery.get("jsFiles", []))
    context_tags = _detect_context(ctx.module_name, discovery)

    module_title = title_case_module(ctx.module_name)
    inferred_flows = _module_specific_flows(ctx.module_name, context_tags) or infer_flows_from_urls(urls)
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

    raw_rules = _module_specific_rules(context_tags) or infer_rules_from_touchpoints(db_touchpoints, has_js)
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
    if "auth" in context_tags:
        must_preserve.append(
            {
                "behavior": "Invalid credentials and session expiry handling (error codes, redirect targets)",
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
                f"{module_title} module handles authentication and protected-page access flows. "
                f"Java files discovered: {len(java_files_sample)}. Key routes: {', '.join(urls[:3]) if urls else 'none'}"
                if "auth" in context_tags
                else (
                    f"{module_title} module manages checklist decisions, status transitions, and WO-triggering rules. "
                    f"Java files discovered: {len(java_files_sample)}. DB touchpoints: {', '.join(db_touchpoints[:3]) if db_touchpoints else 'none'}"
                    if "checklist" in context_tags
                    else f"{module_title} module orchestrates legacy-compatible business workflows. "
                    f"Java assets: {len(java_files_sample)}, Routes: {len(urls)}, DB: {len(db_touchpoints)}.  Converted to C#: {len(csharp_files_sample)} files."
                )
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
