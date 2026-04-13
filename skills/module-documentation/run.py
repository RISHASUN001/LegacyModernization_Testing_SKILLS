#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill
from skill_logic import title_case_module

SPEC = {
    "name": "module-documentation",
    "stage": "logic-understanding",
    "requiredInputs": ["moduleName", "runId"],
}


def _normalize_workflows(logic: dict, module_name: str) -> tuple[list[dict], list[str]]:
    workflows = logic.get("workflows", []) if isinstance(logic.get("workflows"), list) else []
    if workflows:
        return workflows, []
    return (
        [
            {
                "id": f"{module_name.lower()}-fallback-doc-workflow",
                "name": f"{module_name} core workflow (fallback)",
                "steps": [
                    {"name": "Open module", "expectedOutcome": "Entrypoint loads"},
                    {"name": "Perform action", "expectedOutcome": "Business transaction completes"},
                ],
                "preserveCriticality": "high",
                "provenance": make_provenance(
                    "fallback",
                    sources=["fallback:logic-workflows-missing"],
                    confidence=0.35,
                    unknowns=["No structured workflows found in logic-summary.json"],
                ),
            }
        ],
        ["Structured workflows missing from logic summary; fallback workflow used in documentation."],
    )


def execute(ctx):
    logic = ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json") or {}
    discovery = ctx.load_artifact_json("module-discovery", "discovery-map.json") or {}
    scope = ctx.resolve_scope()

    module_title = title_case_module(ctx.module_name)
    workflows, workflow_unknowns = _normalize_workflows(logic, ctx.module_name)

    business_rules = logic.get("businessRules", []) if isinstance(logic.get("businessRules"), list) else []
    must_preserve = logic.get("mustPreserveBehaviors", []) if isinstance(logic.get("mustPreserveBehaviors"), list) else []
    dependencies = logic.get("dependencies", []) if isinstance(logic.get("dependencies"), list) else []

    module_purpose = logic.get("modulePurpose")
    if isinstance(module_purpose, dict):
        purpose_node = module_purpose
    else:
        purpose_node = {
            "text": str(module_purpose or f"{module_title} module documentation generated from discovery and logic artifacts."),
            "provenance": make_provenance("inferred", sources=["artifact:legacy-logic-extraction/logic-summary.json"], confidence=0.62),
        }

    analysis = {
        "moduleName": ctx.module_name,
        "modulePurpose": purpose_node,
        "importantFlows": workflows,
        "businessRules": business_rules,
        "dependencies": dependencies,
        "mustPreserveBehaviors": must_preserve,
        "relatedFiles": {
            "legacyJava": (discovery.get("javaFiles") or scope.get("javaFiles", []))[:120],
            "legacyJsp": (discovery.get("jspFiles") or scope.get("jspFiles", []))[:120],
            "legacyJs": (discovery.get("jsFiles") or scope.get("jsFiles", []))[:120],
            "convertedCsharp": scope.get("csharpFiles", [])[:180],
            "testFiles": scope.get("testFiles", [])[:120],
        },
        "dbInteractions": (discovery.get("dbTouchpoints") or scope.get("dbTouchpoints", []))[:120],
        "urls": (discovery.get("urls") or scope.get("urls", []))[:120],
        "unknowns": workflow_unknowns + (logic.get("unknowns", []) if isinstance(logic.get("unknowns"), list) else []),
        "confidence": float(logic.get("confidence") or 0.62),
        # Backward-compatible keys currently used by dashboard readers.
        "modulePurposeText": purpose_node.get("text", ""),
        "rules": [r.get("rule", "") if isinstance(r, dict) else str(r) for r in business_rules],
        "mustPreserve": [m.get("behavior", "") if isinstance(m, dict) else str(m) for m in must_preserve],
    }

    ctx.write_json("module-analysis.json", analysis)

    return {
        "status": "passed",
        "summary": (
            f"Module documentation generated for {ctx.module_name} with "
            f"flows={len(workflows)}, rules={len(business_rules)}, unknowns={len(analysis['unknowns'])}."
        ),
        "metrics": {
            "sections": 9,
            "flowsDocumented": len(workflows),
            "rulesDocumented": len(business_rules),
            "relatedFiles": len(analysis["relatedFiles"]["legacyJava"]) + len(analysis["relatedFiles"]["legacyJsp"]) + len(analysis["relatedFiles"]["legacyJs"]),
            "confidence": analysis["confidence"],
        },
        "findings": [],
        "recommendations": [
            {
                "message": "Use module-analysis workflows/rules as primary source for scenario and parity mapping.",
                "priority": "high",
                "evidence": "Documentation artifact now includes provenance-tagged flows and business rules.",
            }
        ],
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "inferred", "fallback"],
            "confidence": analysis["confidence"],
            "unknowns": analysis["unknowns"],
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
