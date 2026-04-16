#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from discovery import (
    extract_routes,
    extract_sql_lines,
    extract_tables,
    score_legacy_match,
    tokenize_anchor,
    unique_strings,
)
from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result


SKILL_NAME = "legacy-module-discovery"


def classify_legacy_file(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()

    if suffix == ".jsp":
        return "jsp"
    if suffix == ".xml":
        return "xml"
    if suffix == ".java":
        if "dao" in name:
            return "dao"
        if "action" in name or "controller" in name:
            return "action"
        if "bean" in name or "form" in name:
            return "bean"
        if "ejb" in name or "service" in name:
            return "service"
        return "java"
    return "other"


def build_reasons(path: Path, text: str, anchor_tokens: list[str], workflow_names: list[str]) -> list[str]:
    reasons: list[str] = []
    lower_name = path.name.lower()
    lower_text = text.lower()

    for token in anchor_tokens:
        if token in lower_name:
            reasons.append(f"name matched token '{token}'")
        elif token in lower_text:
            reasons.append(f"content matched token '{token}'")

    for wf in workflow_names:
        wf_lower = str(wf).lower()
        if wf_lower in lower_name or wf_lower in lower_text:
            reasons.append(f"workflow matched '{wf}'")

    file_type = classify_legacy_file(path)
    reasons.append(f"legacy file type '{file_type}'")

    return list(dict.fromkeys(reasons))


def confidence_from_score(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    if score >= 1:
        return "low"
    return "exclude"


def main() -> int:
    parser = argparse.ArgumentParser(description=SKILL_NAME)
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    payload = normalize_payload(load_payload(args.input))
    validation_errors = validate_payload(payload)
    ctx = make_context(payload, args.artifacts_root, SKILL_NAME)

    if validation_errors:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Input validation failed for legacy discovery.",
            artifacts=[],
            metrics={"validationErrors": len(validation_errors)},
            findings=[{"type": "InputValidation", "message": "; ".join(validation_errors)}],
        )
        print(result_path)
        return 1

    artifacts_root = Path(args.artifacts_root)
    csharp_root = artifacts_root / ctx.module_name / ctx.run_id / "csharp-module-discovery"

    csharp_anchor_parts: list[str] = []
    for artifact_name in [
        "csharp-module-map.json",
        "controller-route-map.json",
        "csharp-sql-map.json",
        "csharp-table-usage.json",
        "scoped-file-relevance.json",
    ]:
        path = csharp_root / artifact_name
        if path.exists():
            csharp_anchor_parts.append(path.read_text(encoding="utf-8", errors="ignore"))

    workflow_names = payload.get("workflowNames", [])
    keywords = payload.get("keywords", [])
    anchor_tokens = tokenize_anchor(csharp_anchor_parts + workflow_names + keywords)

    if payload.get("strictModuleOnly", True) and not anchor_tokens:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "No C# anchor evidence found; strict module-first legacy discovery cannot proceed.",
            artifacts=[],
            findings=[{"type": "ModuleFirstViolation", "message": "Missing anchor tokens from C# discovery artifacts."}],
        )
        print(result_path)
        return 1

    legacy_files: list[Path] = []
    for root in payload.get("legacyBackendRoots", []) + payload.get("legacyFrontendRoots", []):
        root_path = Path(root)
        if root_path.exists() and root_path.is_dir():
            legacy_files.extend(root_path.rglob("*.java"))
            legacy_files.extend(root_path.rglob("*.jsp"))
            legacy_files.extend(root_path.rglob("*.xml"))

    legacy_files = sorted(set(p.resolve() for p in legacy_files if p.is_file()), key=lambda p: p.as_posix())

    scored: list[tuple[int, Path, str]] = []
    for path in legacy_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        score = score_legacy_match(path, text, anchor_tokens)
        if score > 0:
            scored.append((score, path, text))

    scored.sort(key=lambda x: (-x[0], x[1].as_posix()))

    selected = scored[:400] if payload.get("strictModuleOnly", True) else scored

    module_map_items: list[dict[str, Any]] = []
    java_sql_map: list[dict[str, Any]] = []
    scoped_relevance: list[dict[str, Any]] = []
    table_accum: list[str] = []

    backend_files: list[str] = []
    frontend_files: list[str] = []

    for score, path, text in selected:
        routes = extract_routes(text)
        sql_lines = extract_sql_lines(text)
        tables = extract_tables(sql_lines)
        table_accum.extend(tables)

        file_type = classify_legacy_file(path)
        confidence = confidence_from_score(score)
        reasons = build_reasons(path, text, anchor_tokens, workflow_names)

        item = {
            "path": path.as_posix(),
            "name": path.name,
            "type": file_type,
            "score": score,
            "confidence": confidence,
            "routes": routes,
            "tables": tables
        }
        module_map_items.append(item)

        scoped_relevance.append({
            "file": path.as_posix(),
            "basename": path.name,
            "type": file_type,
            "score": score,
            "confidence": confidence,
            "included": True,
            "reasons": reasons,
            "workflowNames": workflow_names
        })

        if file_type == "jsp":
            frontend_files.append(path.as_posix())
        else:
            backend_files.append(path.as_posix())

        if sql_lines:
            java_sql_map.append(
                {
                    "file": path.as_posix(),
                    "queries": sql_lines,
                    "tables": tables,
                }
            )

    unique_tables = unique_strings(table_accum)

    module_map_path = write_json(
        ctx.out_dir / "legacy-module-map.json",
        {
            "moduleName": ctx.module_name,
            "workflowNames": workflow_names,
            "strictModuleOnly": payload.get("strictModuleOnly", True),
            "anchorTokenCount": len(anchor_tokens),
            "legacyBackendRoots": payload.get("legacyBackendRoots", []),
            "legacyFrontendRoots": payload.get("legacyFrontendRoots", []),
            "backendFiles": backend_files,
            "frontendFiles": frontend_files,
            "selectedFiles": module_map_items,
        },
    )

    sql_path = write_json(ctx.out_dir / "java-sql-map.json", {"items": java_sql_map})
    table_path = write_json(ctx.out_dir / "java-table-usage.json", {"tables": unique_tables})
    scoped_path = write_json(ctx.out_dir / "legacy-scoped-file-relevance.json", {"items": scoped_relevance})

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Legacy discovery selected {len(module_map_items)} anchored files from {len(legacy_files)} candidates for workflow-scoped analysis.",
        artifacts=[module_map_path, sql_path, table_path, scoped_path],
        metrics={
            "legacyCandidates": len(legacy_files),
            "selectedLegacyFiles": len(module_map_items),
            "sqlFiles": len(java_sql_map),
            "tables": len(unique_tables),
            "anchorTokens": len(anchor_tokens),
            "workflowCount": len(workflow_names),
            "backendFiles": len(backend_files),
            "frontendFiles": len(frontend_files),
        },
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())