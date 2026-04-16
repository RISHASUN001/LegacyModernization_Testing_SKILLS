#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill

SPEC = {
    "name": "parity-verification",
    "stage": "functional-parity",
    "requiredInputs": ["moduleName", "legacySourceRoot", "convertedSourceRoot"],
}

_SQL_STMT_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b[\s\S]{0,260}?(?:;|$)", re.IGNORECASE)
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+([A-Z_][A-Z0-9_]{1,})\b", re.IGNORECASE)
_USING_RE = re.compile(r"^\s*using\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)


def _read_text(path: str, max_chars: int = 200_000) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    return text[:max_chars]


def _normalize_query(sql: str) -> str:
    compact = re.sub(r"\s+", " ", sql or "").strip()
    return compact[:260]


def _extract_query_signatures(files: list[str]) -> list[dict]:
    signatures: list[dict] = []
    for file_path in files:
        text = _read_text(file_path)
        if not text:
            continue

        for match in _SQL_STMT_RE.finditer(text):
            query = _normalize_query(match.group(0))
            if not query:
                continue

            verb_match = re.match(r"^(SELECT|INSERT|UPDATE|DELETE)\b", query, re.IGNORECASE)
            verb = (verb_match.group(1).upper() if verb_match else "UNKNOWN")
            tables = sorted(set(t.upper() for t in _TABLE_RE.findall(query)))
            if not tables and "." not in query:
                continue

            signatures.append(
                {
                    "file": file_path,
                    "query": query,
                    "verb": verb,
                    "tables": tables,
                }
            )

    return signatures[:120]


def _score_match(legacy: dict, converted: dict) -> float:
    legacy_tables = set(legacy.get("tables", []))
    converted_tables = set(converted.get("tables", []))
    if not legacy_tables and not converted_tables:
        return 0.0
    overlap = len(legacy_tables & converted_tables)
    union = len(legacy_tables | converted_tables) or 1
    table_score = overlap / union
    verb_score = 1.0 if legacy.get("verb") == converted.get("verb") else 0.0
    return round((table_score * 0.8) + (verb_score * 0.2), 3)


def _build_sql_parity(scope: dict) -> dict:
    legacy_files = (scope.get("javaFiles", []) + scope.get("jspFiles", []) + scope.get("configFiles", []))[:220]
    converted_files = (scope.get("csharpFiles", []) + scope.get("configFiles", []))[:220]

    legacy_queries = _extract_query_signatures([str(f) for f in legacy_files])
    converted_queries = _extract_query_signatures([str(f) for f in converted_files])

    used_converted: set[int] = set()
    pairs: list[dict] = []
    matched_count = 0

    for legacy in legacy_queries[:40]:
        best_idx = -1
        best_score = 0.0
        for idx, converted in enumerate(converted_queries):
            if idx in used_converted:
                continue
            score = _score_match(legacy, converted)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx >= 0 and best_score >= 0.45:
            used_converted.add(best_idx)
            converted = converted_queries[best_idx]
            matched_count += 1
            pairs.append(
                {
                    "status": "matched",
                    "legacyFile": legacy.get("file", ""),
                    "legacyQuery": legacy.get("query", ""),
                    "legacyTables": legacy.get("tables", []),
                    "convertedFile": converted.get("file", ""),
                    "convertedQuery": converted.get("query", ""),
                    "convertedTables": converted.get("tables", []),
                    "confidence": best_score,
                }
            )
        else:
            pairs.append(
                {
                    "status": "missing",
                    "legacyFile": legacy.get("file", ""),
                    "legacyQuery": legacy.get("query", ""),
                    "legacyTables": legacy.get("tables", []),
                    "convertedFile": "",
                    "convertedQuery": "",
                    "convertedTables": [],
                    "confidence": 0.25,
                }
            )

    table_legacy_counts: dict[str, int] = {}
    table_converted_counts: dict[str, int] = {}
    for item in legacy_queries:
        for table in item.get("tables", []):
            table_legacy_counts[table] = table_legacy_counts.get(table, 0) + 1
    for item in converted_queries:
        for table in item.get("tables", []):
            table_converted_counts[table] = table_converted_counts.get(table, 0) + 1

    table_matches: list[dict] = []
    all_tables = sorted(set(table_legacy_counts.keys()) | set(table_converted_counts.keys()))
    for table in all_tables[:80]:
        legacy_count = table_legacy_counts.get(table, 0)
        converted_count = table_converted_counts.get(table, 0)
        if legacy_count > 0 and converted_count > 0:
            status = "matched"
        elif legacy_count > 0:
            status = "missing"
        else:
            status = "new"
        table_matches.append(
            {
                "table": table,
                "legacyOccurrences": legacy_count,
                "convertedOccurrences": converted_count,
                "status": status,
            }
        )

    return {
        "legacyQueryCount": len(legacy_queries),
        "convertedQueryCount": len(converted_queries),
        "matchedCount": matched_count,
        "tableMatches": table_matches,
        "beforeAfter": pairs[:40],
    }


def _module_tokens_from_scope(scope: dict, module_name: str) -> set[str]:
    tokens = {module_name.lower()}
    tokens.update({p for p in re.split(r"[^a-z0-9]+", module_name.lower()) if p})

    for file_path in [str(x) for x in (scope.get("csharpFiles") or [])]:
        parts = [p.lower() for p in file_path.split("/") if p]
        if "modules" in parts:
            idx = parts.index("modules")
            if idx + 1 < len(parts):
                tokens.add(parts[idx + 1])

    return {t for t in tokens if t}


def _extract_dependency_refs(files: list[str]) -> list[str]:
    refs: list[str] = []
    for file_path in files:
        text = _read_text(file_path)
        if not text:
            continue
        refs.extend(_USING_RE.findall(text))
        refs.extend(_IMPORT_RE.findall(text))
    return refs


def _classify_cross_module_dependencies(scope: dict, module_name: str, allowed_cross_modules: list[str]) -> dict:
    module_tokens = _module_tokens_from_scope(scope, module_name)
    allowed = {m.lower() for m in allowed_cross_modules if m}
    allowed.update({"shared"})

    known_modules = {
        "auth",
        "checklist",
        "atcchecklist",
        "mobilecart",
        "workorder",
        "reports",
        "shared",
        "conveyorchecklist",
        "conveyorreports",
    }

    refs = _extract_dependency_refs(
        [str(x) for x in (scope.get("csharpFiles") or [])]
        + [str(x) for x in (scope.get("javaFiles") or [])]
    )

    dependencies: list[dict] = []
    seen: set[str] = set()
    for ref in refs:
        lower = ref.lower()
        parts = [p for p in re.split(r"[^a-z0-9]+", lower) if p]
        foreign_tokens = [p for p in parts if p not in module_tokens and p in known_modules]
        if not foreign_tokens:
            continue

        foreign = foreign_tokens[0]
        key = f"{foreign}:{ref}"
        if key in seen:
            continue
        seen.add(key)

        dependencies.append(
            {
                "dependencyModule": foreign,
                "reference": ref,
                "status": "allowed" if foreign in allowed else "violation",
            }
        )

    violations = [d for d in dependencies if d.get("status") == "violation"]

    return {
        "allowedCrossModules": sorted(allowed),
        "dependencies": dependencies[:120],
        "violations": violations[:60],
    }


def execute(ctx):
    discovery = ctx.load_artifact_json("module-discovery", "discovery-map.json") or {}
    logic = ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json") or {}
    csharp_logic = ctx.load_artifact_json("csharp-logic-understanding", "csharp-logic-summary.json") or {}
    java_logic = ctx.load_artifact_json("java-logic-understanding", "java-logic-summary.json") or {}
    scope = ctx.resolve_scope()
    allowed_cross_modules = [str(x).strip() for x in (ctx.get("allowedCrossModules") or []) if str(x).strip()]

    must_preserve = logic.get("mustPreserveBehaviors", []) if isinstance(logic.get("mustPreserveBehaviors"), list) else []
    if not must_preserve:
        must_preserve = [{"behavior": x} for x in (logic.get("mustPreserve", []) if isinstance(logic.get("mustPreserve"), list) else [])]

    urls = discovery.get("urls", []) if isinstance(discovery.get("urls"), list) else []
    db_touchpoints = discovery.get("dbTouchpoints", []) if isinstance(discovery.get("dbTouchpoints"), list) else []

    run_results = ctx.iter_run_results()
    execution_results = [r for r in run_results if str(r.get("stage", "")).lower() == "execution"]

    failed_execution_skills = [r for r in execution_results if str(r.get("status", "")).lower() != "passed"]
    failed_skill_names = [str(r.get("skillName") or r.get("skill") or "unknown-skill") for r in failed_execution_skills]

    checks: list[dict] = []
    sql_parity = _build_sql_parity(scope)
    dependency_parity = _classify_cross_module_dependencies(scope, ctx.module_name, allowed_cross_modules)
    sql_missing = max(0, int(sql_parity.get("legacyQueryCount", 0)) - int(sql_parity.get("matchedCount", 0)))
    sql_check_status = "failed" if sql_missing > 0 else "passed"

    for item in must_preserve[:20]:
        behavior = str(item.get("behavior") if isinstance(item, dict) else item)
        related_failures = [s for s in failed_skill_names if any(token in s.lower() for token in ["api", "e2e", "playwright", "integration"]) ]
        status = "failed" if related_failures else "passed"
        checks.append(
            {
                "name": behavior,
                "status": status,
                "evidence": {
                    "failedExecutionSkills": related_failures,
                    "relatedUrls": urls[:5],
                    "relatedDbTouchpoints": db_touchpoints[:5],
                },
                "provenance": make_provenance(
                    "code-evidence",
                    sources=["artifact:legacy-logic-extraction/logic-summary.json", "artifact:module-discovery/discovery-map.json"],
                    confidence=float((item.get("provenance") or {}).get("confidence") or 0.75) if isinstance(item, dict) else 0.72,
                ),
            }
        )

    if not checks:
        checks.append(
            {
                "name": f"{ctx.module_name} fallback parity check",
                "status": "failed" if failed_execution_skills else "passed",
                "evidence": {"failedExecutionSkills": failed_skill_names},
                "provenance": make_provenance(
                    "fallback",
                    sources=["fallback:no-must-preserve-behaviors"],
                    confidence=0.4,
                    unknowns=["Logic stage did not provide must-preserve behavior items"],
                ),
            }
        )

    checks.append(
        {
            "name": "SQL/table parity between legacy and converted code",
            "status": sql_check_status,
            "evidence": {
                "legacyQueryCount": sql_parity.get("legacyQueryCount", 0),
                "convertedQueryCount": sql_parity.get("convertedQueryCount", 0),
                "matchedCount": sql_parity.get("matchedCount", 0),
                "missingCount": sql_missing,
            },
            "provenance": make_provenance(
                "code-evidence",
                sources=["module-scope:legacy+converted", "sql-pattern-extraction"],
                confidence=0.78,
            ),
        }
    )

    checks.append(
        {
            "name": "Cross-module dependency policy compliance",
            "status": "failed" if dependency_parity.get("violations") else "passed",
            "evidence": {
                "allowedCrossModules": dependency_parity.get("allowedCrossModules", []),
                "detectedDependencies": len(dependency_parity.get("dependencies", [])),
                "violationCount": len(dependency_parity.get("violations", [])),
            },
            "provenance": make_provenance(
                "code-evidence",
                sources=["csharp-using/import-analysis", "java-import-analysis"],
                confidence=0.74,
            ),
        }
    )

    parity_total = len(checks)
    parity_failed = len([c for c in checks if c["status"] != "passed"])
    parity_passed = max(0, parity_total - parity_failed)
    parity_score = int(round((parity_passed / parity_total) * 100)) if parity_total else 0

    gaps = []
    if parity_failed > 0:
        gaps.append(f"{parity_failed} parity checks failed based on execution and preserve-behavior linkage.")
    if not urls:
        gaps.append("No URL discovery evidence; route parity validation confidence reduced.")
    if not db_touchpoints:
        gaps.append("No DB touchpoint evidence; persistence parity validation confidence reduced.")
    if sql_missing > 0:
        gaps.append(f"SQL parity mismatch: {sql_missing} legacy query patterns do not have converted matches.")
    if dependency_parity.get("violations"):
        gaps.append(
            f"Detected {len(dependency_parity.get('violations', []))} cross-module dependency policy violation(s)."
        )

    csharp_workflows = csharp_logic.get("workflows") if isinstance(csharp_logic.get("workflows"), list) else []
    java_workflows = java_logic.get("workflows") if isinstance(java_logic.get("workflows"), list) else []

    workflow_pairs = []
    for csharp_wf in csharp_workflows[:20]:
        if not isinstance(csharp_wf, dict):
            continue
        c_name = str(csharp_wf.get("name") or "").strip()
        if not c_name:
            continue

        c_tokens = {p for p in re.split(r"[^a-z0-9]+", c_name.lower()) if len(p) >= 3}
        best = None
        best_score = 0.0
        for java_wf in java_workflows[:30]:
            if not isinstance(java_wf, dict):
                continue
            j_name = str(java_wf.get("name") or "").strip()
            j_tokens = {p for p in re.split(r"[^a-z0-9]+", j_name.lower()) if len(p) >= 3}
            if not c_tokens or not j_tokens:
                continue
            overlap = len(c_tokens & j_tokens)
            union = max(1, len(c_tokens | j_tokens))
            score = overlap / union
            if score > best_score:
                best_score = score
                best = java_wf

        status = "preserved" if best_score >= 0.45 else ("partial" if best_score >= 0.2 else "missing")
        workflow_pairs.append(
            {
                "workflowName": c_name,
                "status": status,
                "preservationScore": round(best_score, 3),
                "csharp": {
                    "entryPoint": str(csharp_wf.get("entryPoint") or csharp_wf.get("entryRoute") or ""),
                    "dependencies": csharp_wf.get("dependencies", []),
                },
                "java": {
                    "workflowName": str(best.get("name") or "") if isinstance(best, dict) else "",
                    "entryPoint": str(best.get("entryPoint") or best.get("entryHint") or "") if isinstance(best, dict) else "",
                    "dependencies": best.get("dependencies", []) if isinstance(best, dict) else [],
                },
                "provenance": make_provenance("flow-derived", sources=["csharp-logic-summary.json", "java-logic-summary.json"], confidence=0.74),
            }
        )

    module_preservation = int(round((sum(p.get("preservationScore", 0.0) for p in workflow_pairs) / max(1, len(workflow_pairs))) * 100)) if workflow_pairs else parity_score

    parity = {
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "parityScore": parity_score,
        "modulePreservationScore": module_preservation,
        "checkedItems": {
            "mustPreserve": len(must_preserve),
            "urls": len(urls),
            "dbTouchpoints": len(db_touchpoints),
            "executionSkills": len(execution_results),
            "legacyQueries": sql_parity.get("legacyQueryCount", 0),
            "convertedQueries": sql_parity.get("convertedQueryCount", 0),
            "matchedQueries": sql_parity.get("matchedCount", 0),
        },
        "checks": checks,
        "sqlParity": sql_parity,
        "dependencyParity": dependency_parity,
        "gaps": gaps,
        "confidence": 0.81 if checks and urls else 0.58,
    }
    ctx.write_json("parity-diff.json", parity)
    ctx.write_json("functional-parity-map.json", parity)
    ctx.write_json("workflow-parity-summary.json", {"moduleName": ctx.module_name, "workflows": workflow_pairs})
    ctx.write_json("sql-parity-map.json", {"moduleName": ctx.module_name, "beforeAfter": sql_parity.get("beforeAfter", []), "matchedCount": sql_parity.get("matchedCount", 0)})
    ctx.write_json("table-parity-map.json", {"moduleName": ctx.module_name, "tables": sql_parity.get("tableMatches", [])})
    ctx.write_json("preservation-score.json", {"moduleName": ctx.module_name, "moduleScore": module_preservation, "workflowScores": [{"workflowName": item.get("workflowName", ""), "score": item.get("preservationScore", 0)} for item in workflow_pairs]})

    findings = []
    if parity_failed > 0:
        findings.append(
            {
                "type": "ParityGap",
                "scenario": "Legacy vs converted behavior parity",
                "message": f"Parity score for {ctx.module_name} is {parity_score} with {parity_failed} failing checks.",
                "likelyCause": "Execution failures and/or unmet must-preserve behavior checks.",
                "evidence": "See parity-diff.json checks[] and evidence links.",
                "severity": "high" if parity_score < 80 else "medium",
                "status": "open",
                "confidence": parity["confidence"],
            }
        )

    return {
        "status": "passed",
        "summary": f"Parity verification for {ctx.module_name}: score={parity_score}, failedChecks={parity_failed}.",
        "metrics": {
            "total": parity_total,
            "passed": parity_passed,
            "failed": parity_failed,
            "warnings": len(gaps),
            "newTestsAdded": 0,
            "parityScore": parity_score,
            "matchedQueries": sql_parity.get("matchedCount", 0),
            "legacyQueries": sql_parity.get("legacyQueryCount", 0),
            "modulePreservationScore": module_preservation,
        },
        "findings": findings,
        "recommendations": [
            {
                "message": "Close failed parity checks by aligning execution failures to must-preserve behavior requirements.",
                "priority": "high" if parity_score < 85 else "medium",
                "evidence": f"parityScore={parity_score}; failedChecks={parity_failed}",
            }
        ],
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "fallback"],
            "confidence": parity["confidence"],
            "unknowns": gaps,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
