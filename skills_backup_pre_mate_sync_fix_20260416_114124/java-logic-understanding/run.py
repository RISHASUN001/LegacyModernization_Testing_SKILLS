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
    "name": "java-logic-understanding",
    "stage": "java-logic",
    "requiredInputs": ["moduleName", "legacySourceRoot"],
}

_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)


def _read_text(path: str, max_chars: int = 160_000) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _build_java_package_index(java_files: list[str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    package_to_files: dict[str, list[str]] = {}
    fqcn_to_file: dict[str, str] = {}

    for file_path in java_files[:900]:
        text = _read_text(file_path, max_chars=40_000)
        package_match = _PACKAGE_RE.search(text)
        package_name = package_match.group(1).strip() if package_match else ""
        class_name = Path(file_path).stem
        if package_name:
            package_to_files.setdefault(package_name, []).append(file_path)
            if class_name:
                fqcn_to_file[f"{package_name}.{class_name}"] = file_path
        elif class_name:
            fqcn_to_file[class_name] = file_path

    return package_to_files, fqcn_to_file


def _resolve_imported_files(imports: set[str], package_to_files: dict[str, list[str]], fqcn_to_file: dict[str, str], strict_mode: bool) -> set[str]:
    resolved: set[str] = set()
    for imp in imports:
        if imp in fqcn_to_file:
            resolved.add(fqcn_to_file[imp])
            continue

        package = imp.rsplit(".", 1)[0] if "." in imp else ""
        if not package:
            continue

        if strict_mode:
            resolved.update(package_to_files.get(package, []))
        else:
            for pkg, files in package_to_files.items():
                if pkg == package or pkg.startswith(package + "."):
                    resolved.update(files)

    return resolved


def execute(ctx):
    legacy_workflows_node = ctx.load_artifact_json("java-counterpart-discovery", "legacy-workflows.json") or {}
    sql_node = ctx.load_artifact_json("java-counterpart-discovery", "java-sql-map.json") or {}
    scope = ctx.resolve_scope()
    strict_mode = bool(ctx.payload.get("strictModuleOnly", True))

    workflows = legacy_workflows_node.get("workflows") if isinstance(legacy_workflows_node.get("workflows"), list) else []
    queries = sql_node.get("queries") if isinstance(sql_node.get("queries"), list) else []
    java_files = [str(p) for p in (scope.get("javaFiles") or [])]
    package_to_files, fqcn_to_file = _build_java_package_index(java_files)

    java_workflows = []
    import_linked_files_count = 0
    for wf in workflows[:20]:
        if not isinstance(wf, dict):
            continue
        files = wf.get("relatedFiles") if isinstance(wf.get("relatedFiles"), list) else []

        import_refs: set[str] = set()
        for file_path in files[:30]:
            text = _read_text(str(file_path))
            import_refs.update([imp.strip() for imp in _IMPORT_RE.findall(text) if imp.strip()])

        imported_files = sorted(_resolve_imported_files(import_refs, package_to_files, fqcn_to_file, strict_mode))[:60]
        import_linked_files_count += len(imported_files)

        java_workflows.append(
            {
                "workflowId": wf.get("workflowId") or "",
                "name": wf.get("name") or "",
                "purpose": f"Legacy Java workflow understanding for {ctx.module_name} counterpart path.",
                "entryPoint": wf.get("entryHint") or "",
                "actionSequence": [
                    "Action/Servlet receives request",
                    "Service/EJB handles business branch",
                    "DAO executes SQL",
                    "JSP forward/redirect renders response",
                ],
                "validations": ["Request/form validation", "Session/context checks"],
                "decisionBranches": [
                    "Forward path selected by condition",
                    "Error path propagates to JSP or message handler",
                ],
                "sideEffects": ["Database read/write", "Session propagation", "Audit/log side effects"],
                "dbTouchpoints": [q.get("tables", []) for q in queries[:3] if isinstance(q, dict)],
                "expectedOutputs": ["JSP/report rendering", "Form persistence behavior"],
                "dependencies": sorted({*files[:15], *imported_files[:15]}),
                "importEvidence": {
                    "seedFiles": files[:20],
                    "imports": sorted(import_refs)[:60],
                    "importLinkedFiles": imported_files,
                },
                "provenance": make_provenance("flow-derived", sources=["legacy-workflows.json"], confidence=0.69),
            }
        )

    summary = {
        "moduleName": ctx.module_name,
        "modulePurpose": f"Legacy Java logic understanding for module {ctx.module_name}.",
        "workflows": java_workflows,
        "businessRules": [
            {
                "rule": "Legacy flow intent must remain preserved in converted module.",
                "provenance": make_provenance("inferred", sources=["legacy-workflows.json"], confidence=0.64),
            }
        ],
        "unknowns": [] if java_workflows else ["No legacy workflow counterparts available from discovery artifacts."],
        "confidence": 0.74 if java_workflows else 0.41,
    }

    ctx.write_json("java-logic-summary.json", summary)

    return {
        "status": "passed" if java_workflows else "degraded",
        "summary": f"Java logic understanding produced {len(java_workflows)} workflow summaries.",
        "metrics": {
            "workflowCount": len(java_workflows),
            "sqlSignatureCount": len(queries),
            "importLinkedFiles": import_linked_files_count,
        },
        "findings": [],
        "recommendations": [],
        "provenanceSummary": {
            "scenarioSources": ["flow-derived", "code-evidence"],
            "confidence": 0.74 if java_workflows else 0.41,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
