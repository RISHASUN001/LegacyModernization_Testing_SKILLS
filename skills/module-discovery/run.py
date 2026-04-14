#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill
from skill_logic import dedupe, sample

SPEC = {
    "name": "module-discovery",
    "stage": "discovery",
    "requiredInputs": ["moduleName", "legacySourceRoot"],
}


def _with_provenance(path: str, sources: list[str], confidence: float) -> dict:
    return {
        "path": path,
        "provenance": make_provenance("code-evidence", sources=sources, confidence=confidence),
    }


def _load_module_profiles() -> list[dict]:
    profile_path = Path(__file__).resolve().parents[1] / "legacy-logic-extraction" / "module-profiles.json"
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    profiles = payload.get("profiles") if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        return []
    return [p for p in profiles if isinstance(p, dict)]


def _module_jsp_tokens(module_name: str, routes: list[str]) -> list[str]:
    base_tokens = [
        "form",
        "edit",
        "view",
        "create",
        "details",
        "index",
    ]

    profiles = _load_module_profiles()
    haystack = " ".join([module_name] + [str(x) for x in routes]).lower()
    for profile in profiles:
        tokens = [str(x).strip().lower() for x in (profile.get("matchTokens") or []) if str(x).strip()]
        if tokens and any(token in haystack for token in tokens):
            base_tokens.extend(tokens)

    module_parts = [part.strip().lower() for part in re.split(r"[^a-zA-Z0-9]+", module_name) if part.strip()]
    base_tokens.extend(module_parts)

    deduped: list[str] = []
    seen: set[str] = set()
    for token in base_tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _hint_entrypoints(scope: dict, module_name: str) -> list[dict]:
    entrypoints: list[dict] = []
    routes = scope.get("urls", [])
    module_token = module_name.lower()
    for route in routes[:80]:
        confidence = 0.82 if module_token in str(route).lower() else 0.66
        entrypoints.append(
            {
                "kind": "route",
                "value": route,
                "provenance": make_provenance(
                    "code-evidence",
                    sources=["url-extraction"],
                    confidence=confidence,
                    unknowns=[] if confidence > 0.7 else ["Route may be shared across modules"],
                ),
            }
        )

    servlet_candidates = [p for p in scope.get("javaFiles", []) if re.search(r"(servlet|controller|action)", p, re.IGNORECASE)]
    for path in servlet_candidates[:40]:
        entrypoints.append(
            {
                "kind": "code-entrypoint",
                "value": path,
                "provenance": make_provenance("code-evidence", sources=[path], confidence=0.88),
            }
        )

    jsp_tokens = _module_jsp_tokens(module_name, routes)
    jsp_pattern = "(" + "|".join(re.escape(token) for token in jsp_tokens) + ")"
    jsp_forms = [p for p in scope.get("jspFiles", []) if re.search(jsp_pattern, p, re.IGNORECASE)]
    for path in jsp_forms[:40]:
        entrypoints.append(
            {
                "kind": "view-entrypoint",
                "value": path,
                "provenance": make_provenance("code-evidence", sources=[path], confidence=0.76),
            }
        )

    return entrypoints[:120]


def _is_route_like(value: str) -> bool:
    route = (value or "").strip()
    if not route.startswith("/"):
        return False
    lower = route.lower()
    if lower.startswith("/views/") or lower.startswith("/wwwroot/"):
        return False
    if any(lower.endswith(ext) for ext in [".cshtml", ".jsp", ".java", ".js", ".ts", ".json", ".xml", ".md"]):
        return False
    if "/users/" in lower or "\\" in route:
        return False
    return True


def execute(ctx):
    scope = ctx.resolve_scope()
    module_token = ctx.module_name.lower()

    def _is_in_module_generated_bucket(path: str) -> bool:
        lower = path.lower().replace("\\", "/")
        marker = "/tests/generated/"
        idx = lower.find(marker)
        if idx < 0:
            return True
        remainder = lower[idx + len(marker):]
        bucket = remainder.split("/", 1)[0]
        return bucket == module_token

    java_files = sample(scope.get("javaFiles", []), 250)
    jsp_files = sample(scope.get("jspFiles", []), 250)
    js_files = sample(scope.get("jsFiles", []), 250)
    config_files = sample([p for p in scope.get("configFiles", []) if _is_in_module_generated_bucket(str(p))], 250)
    csharp_files = sample(scope.get("csharpFiles", []), 250)
    test_files = sample([p for p in scope.get("testFiles", []) if _is_in_module_generated_bucket(str(p))], 250)
    other_files = sample(scope.get("otherFiles", []), 250)

    urls = sample([u for u in scope.get("urls", []) if _is_route_like(str(u))], 250)
    db_touchpoints = sample(scope.get("dbTouchpoints", []), 250)

    files_by_type = {
        "java": [_with_provenance(p, [p], 0.9) for p in java_files],
        "jsp": [_with_provenance(p, [p], 0.86) for p in jsp_files],
        "js": [_with_provenance(p, [p], 0.84) for p in js_files],
        "config": [_with_provenance(p, [p], 0.83) for p in config_files],
        "csharp": [_with_provenance(p, [p], 0.8) for p in csharp_files],
        "test": [_with_provenance(p, [p], 0.8) for p in test_files],
        "other": [_with_provenance(p, [p], 0.6) for p in other_files],
    }

    route_candidates = [
        {
            "route": route,
            "normalizedRoute": route if str(route).startswith("/") else f"/{route}",
            "provenance": make_provenance(
                "code-evidence",
                sources=["url-extraction"],
                confidence=0.82,
                unknowns=[] if "." in str(route) else ["Route extension/type could not be inferred"],
            ),
        }
        for route in urls
    ]

    db_touchpoint_entries = [
        {
            "name": db,
            "provenance": make_provenance(
                "code-evidence",
                sources=["sql/token-extraction"],
                confidence=0.78,
                unknowns=["Verify package/procedure call direction in runtime traces"],
            ),
        }
        for db in db_touchpoints
    ]

    entrypoint_hints = _hint_entrypoints(scope, ctx.module_name)

    asset_counts = {
        "java": len(java_files),
        "jsp": len(jsp_files),
        "js": len(js_files),
        "config": len(config_files),
        "csharp": len(csharp_files),
        "test": len(test_files),
        "other": len(other_files),
        "total": len(java_files) + len(jsp_files) + len(js_files) + len(config_files) + len(csharp_files) + len(test_files) + len(other_files),
        "urls": len(urls),
        "dbTouchpoints": len(db_touchpoints),
    }

    confidence = 0.92 if asset_counts["total"] > 0 else 0.35

    discovery_map = {
        "moduleName": ctx.module_name,
        "roots": scope.get("roots", []),
        "hintPaths": scope.get("hintPaths", []),
        "terms": scope.get("terms", []),
        "scopeContext": scope.get("scopeContext", {}),
        "totalSelectedFiles": int(scope.get("totalSelectedFiles", 0) or 0),
        "assetCounts": asset_counts,
        "filesByType": files_by_type,
        "routeCandidates": route_candidates,
        "dbTouchpointsDetailed": db_touchpoint_entries,
        "entrypointHints": entrypoint_hints,
        "confidence": confidence,
        "provenance": make_provenance(
            "code-evidence",
            sources=dedupe(scope.get("roots", []) + scope.get("hintPaths", []))[:20],
            confidence=confidence,
        ),
        # Backward-compatible keys currently used by dashboard/skills.
        "javaFiles": java_files,
        "jspFiles": jsp_files,
        "jsFiles": js_files,
        "configFiles": config_files,
        "csharpFiles": csharp_files,
        "testFiles": test_files,
        "otherFiles": other_files,
        "urls": urls,
        "dbTouchpoints": db_touchpoints,
        "evidenceFiles": sample(
            dedupe(java_files + jsp_files + js_files + config_files + csharp_files + test_files),
            80,
        ),
    }

    discovery_evidence = {
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "evidence": {
            "filesSample": discovery_map["evidenceFiles"],
            "routeEvidence": route_candidates[:40],
            "dbEvidence": db_touchpoint_entries[:40],
            "entrypointHints": entrypoint_hints[:40],
        },
    }

    ctx.write_json("discovery-map.json", discovery_map)
    ctx.write_json("discovery-evidence.json", discovery_evidence)

    findings = []
    recommendations = []
    status = "passed"

    if asset_counts["total"] == 0:
        status = "failed"
        findings.append(
            {
                "type": "ModuleScopeEmpty",
                "scenario": "Discovery scan",
                "message": f"No module assets were discovered for module '{ctx.module_name}'.",
                "likelyCause": "Provided roots/hints do not match actual module file locations.",
                "evidence": "Discovery returned zero scoped assets.",
                "severity": "high",
                "status": "open",
                "confidence": 0.95,
            }
        )
        recommendations.append(
            {
                "message": "Update module hints and roots so discovery can scope the correct module folders.",
                "priority": "high",
                "evidence": "Stage 1 requires scoped assets for downstream logic/test planning.",
            }
        )

    if not urls:
        findings.append(
            {
                "type": "MissingUrlEvidence",
                "scenario": "Discovery URL extraction",
                "message": "No module URLs were extracted from discovered files.",
                "likelyCause": "Route definitions may be outside scoped files or use uncommon patterns.",
                "evidence": "URLs list is empty in discovery-map.json.",
                "severity": "medium",
                "status": "open",
                "confidence": 0.68,
            }
        )

    return {
        "status": status,
        "summary": (
            f"Discovery completed for {ctx.module_name}: assets={asset_counts['total']}, "
            f"routes={asset_counts['urls']}, dbTouchpoints={asset_counts['dbTouchpoints']}."
        ),
        "metrics": {
            "totalAssets": asset_counts["total"],
            "javaFiles": asset_counts["java"],
            "jspFiles": asset_counts["jsp"],
            "jsFiles": asset_counts["js"],
            "configFiles": asset_counts["config"],
            "urls": asset_counts["urls"],
            "dbTouchpoints": asset_counts["dbTouchpoints"],
            "confidence": confidence,
        },
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence"],
            "confidence": confidence,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
