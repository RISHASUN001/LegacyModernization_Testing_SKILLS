#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill

SPEC = {
    "name": "java-counterpart-discovery",
    "stage": "java-discovery",
    "requiredInputs": ["moduleName", "legacySourceRoot", "convertedSourceRoot"],
}

_SQL_STMT_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b[\s\S]{0,260}?(?:;|$)", re.IGNORECASE)
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+([A-Z_][A-Z0-9_]{1,})\b", re.IGNORECASE)
_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)


def _read_text(path: str, max_chars: int = 120_000) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _tokens(*values: str) -> set[str]:
    out: set[str] = set()
    for value in values:
        for token in re.split(r"[^a-z0-9]+", (value or "").lower()):
            if len(token) >= 3:
                out.add(token)
    return out


def execute(ctx):
    scope = ctx.resolve_scope()
    csharp_logic = ctx.load_artifact_json("csharp-logic-understanding", "csharp-logic-summary.json") or {}
    csharp_namespace_node = ctx.load_artifact_json("csharp-module-discovery", "csharp-namespace-usage.json") or {}
    csharp_workflows = csharp_logic.get("workflows") if isinstance(csharp_logic.get("workflows"), list) else []
    strict_mode = bool(ctx.get("strictModuleOnly") or False)

    hints = set(_tokens(ctx.module_name, str(ctx.get("moduleHints.scopeHint") or "")))
    for wf in csharp_workflows:
        if isinstance(wf, dict):
            hints |= _tokens(str(wf.get("name") or ""), str(wf.get("entryPoint") or ""))

    csharp_namespaces = csharp_namespace_node.get("namespaces") if isinstance(csharp_namespace_node.get("namespaces"), list) else []
    csharp_using_refs = csharp_namespace_node.get("usingReferences") if isinstance(csharp_namespace_node.get("usingReferences"), list) else []
    for item in csharp_namespaces[:80]:
        if isinstance(item, dict):
            hints |= _tokens(str(item.get("namespace") or ""))
    for item in csharp_using_refs[:120]:
        if isinstance(item, dict):
            hints |= _tokens(str(item.get("using") or ""))

    java_files = [str(p) for p in (scope.get("javaFiles") or [])]
    jsp_files = [str(p) for p in (scope.get("jspFiles") or [])]
    candidates = java_files + jsp_files

    related: list[dict] = []
    excluded: list[dict] = []
    threshold = 0.18 if strict_mode else 0.12
    for file_path in candidates[:800]:
        text = _read_text(file_path)
        path_tokens = _tokens(file_path)
        package_tokens = _tokens(" ".join(_PACKAGE_RE.findall(text)))
        import_tokens = _tokens(" ".join(_IMPORT_RE.findall(text)))
        content_tokens = _tokens(text[:2000])

        weighted_overlap = (
            len((path_tokens & hints)) * 1.2
            + len((package_tokens & hints)) * 1.8
            + len((import_tokens & hints)) * 1.6
            + len((content_tokens & hints)) * 0.6
        )
        overlap = sorted((path_tokens | package_tokens | import_tokens | content_tokens) & hints)
        score = min(1.0, weighted_overlap / max(3.0, float(len(hints)) * 0.9))
        entry = {
            "path": file_path,
            "score": round(score, 3),
            "matchedTokens": overlap[:15],
            "packageMatches": sorted((package_tokens & hints))[:10],
            "importMatches": sorted((import_tokens & hints))[:10],
            "provenance": make_provenance("code-evidence", sources=[file_path], confidence=max(0.3, score)),
        }
        if score >= threshold:
            related.append(entry)
        else:
            excluded.append(
                {
                    "path": file_path,
                    "reason": "low-evidence-score",
                    "score": round(score, 3),
                    "matchedTokens": overlap[:10],
                    "provenance": make_provenance("inferred", sources=[file_path], confidence=0.5),
                }
            )

    related_paths = [x["path"] for x in related]
    sql_entries = []
    table_counts: dict[str, int] = {}
    for path in related_paths[:350]:
        text = _read_text(path)
        for match in _SQL_STMT_RE.finditer(text):
            query = re.sub(r"\s+", " ", match.group(0)).strip()[:260]
            tables = [t.upper() for t in _TABLE_RE.findall(query)]
            if not tables:
                continue
            sql_entries.append(
                {
                    "file": path,
                    "query": query,
                    "tables": sorted(set(tables)),
                    "provenance": make_provenance("code-evidence", sources=[path], confidence=0.72),
                }
            )
            for table in tables:
                key = table.upper()
                table_counts[key] = table_counts.get(key, 0) + 1

    legacy_workflows = []
    for idx, wf in enumerate(csharp_workflows[:12], start=1):
        if not isinstance(wf, dict):
            continue
        name = str(wf.get("name") or f"legacy-workflow-{idx:02d}")
        entry_point = str(wf.get("entryPoint") or "")
        wf_tokens = _tokens(name, entry_point)
        wf_files = [r["path"] for r in related if wf_tokens & set(r.get("matchedTokens") or [])][:30]
        legacy_workflows.append(
            {
                "workflowId": f"java-workflow-{idx:02d}",
                "name": name.replace(ctx.module_name, f"{ctx.module_name} legacy"),
                "entryHint": entry_point,
                "relatedFiles": wf_files,
                "provenance": make_provenance("flow-derived", sources=["csharp-logic-summary.json"], confidence=0.68),
            }
        )

    ctx.write_json(
        "legacy-module-map.json",
        {
            "moduleName": ctx.module_name,
            "legacyBackendRoot": str(ctx.get("legacyBackendRoot") or ctx.get("legacySourceRoot") or ""),
            "legacyFrontendRoot": str(ctx.get("legacyFrontendRoot") or ""),
            "relatedFileCount": len(related),
            "relatedFiles": related_paths[:300],
            "provenance": make_provenance("code-evidence", sources=related_paths[:25], confidence=0.7 if related else 0.35),
        },
    )
    ctx.write_json("legacy-workflows.json", {"moduleName": ctx.module_name, "workflows": legacy_workflows})
    ctx.write_json("java-sql-map.json", {"moduleName": ctx.module_name, "queries": sql_entries[:180]})
    ctx.write_json(
        "java-table-usage.json",
        {
            "moduleName": ctx.module_name,
            "tables": [{"table": t, "occurrences": c} for t, c in sorted(table_counts.items(), key=lambda it: (-it[1], it[0]))],
        },
    )
    ctx.write_json("java-related-files.json", {"moduleName": ctx.module_name, "related": related[:400]})
    ctx.write_json("java-exclusions.json", {"moduleName": ctx.module_name, "excluded": excluded[:400]})

    return {
        "status": "passed",
        "summary": f"Java counterpart discovery selected {len(related)} files and mapped {len(legacy_workflows)} legacy workflows.",
        "metrics": {
            "relatedFiles": len(related),
            "excludedFiles": len(excluded),
            "legacyWorkflows": len(legacy_workflows),
            "sqlSignatures": len(sql_entries),
            "tables": len(table_counts),
        },
        "findings": [],
        "recommendations": [],
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "flow-derived"],
            "confidence": 0.7 if related else 0.38,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
