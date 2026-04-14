#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
    "name": "clean-architecture-assessment",
    "stage": "architecture-review",
    "requiredInputs": ["moduleName", "convertedSourceRoot"],
}

NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_.]+)", re.MULTILINE)
CTOR_RE = re.compile(r"\bpublic\s+([A-Za-z0-9_]+Controller)\s*\(([^)]*)\)", re.MULTILINE)
USING_RE = re.compile(r"^\s*using\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)


def _architecture_policy(ctx) -> str:
    policy = str(ctx.get("architecturePolicy") or "module-first").strip().lower()
    return policy if policy in {"module-first", "balanced", "clean-architecture"} else "module-first"


def _module_roots(csharp_files: list[Path], module_name: str) -> list[Path]:
    token = module_name.lower()
    roots: list[Path] = []
    for path in csharp_files:
        lower_parts = [p.lower() for p in path.parts]
        if "modules" in lower_parts:
            idx = lower_parts.index("modules")
            if idx + 1 < len(path.parts) and path.parts[idx + 1].lower() == token:
                roots.append(Path(*path.parts[: idx + 2]))
    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = root.as_posix().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def execute(ctx):
    scope = ctx.resolve_scope()
    csharp_files = [Path(p) for p in scope.get("csharpFiles", [])]

    clean_issues: list[dict] = []
    namespace_issues: list[dict] = []
    di_issues: list[dict] = []
    coupling_issues: list[dict] = []

    module_token = ctx.module_name.lower()
    policy = _architecture_policy(ctx)

    program_files = [p for p in csharp_files if p.name.lower() in {"program.cs", "startup.cs"}]
    has_module_di = False
    for p in program_files:
        text = _read_text(p).lower()
        if module_token in text and ("addscoped" in text or "addtransient" in text or "addsingleton" in text):
            has_module_di = True
            break

    if not has_module_di:
        di_issues.append(
            {
                "title": f"Missing explicit DI registration signals for module '{ctx.module_name}'",
                "severity": "high",
                "evidence": "Program/Startup scan did not find module-specific AddScoped/AddTransient registrations.",
            }
        )

    if policy == "module-first":
        disallowed = {"domain", "application", "infrastructure", "features", "usecases"}
        module_roots = _module_roots(csharp_files, ctx.module_name)
        for module_root in module_roots[:3]:
            if not module_root.exists():
                continue
            for child in module_root.iterdir():
                if not child.is_dir():
                    continue
                if child.name.lower() in disallowed:
                    clean_issues.append(
                        {
                            "title": "Unnecessary folder for module-first policy",
                            "severity": "medium",
                            "evidence": f"{child.as_posix()} should be simplified under module-first architecture policy.",
                        }
                    )

    for path in csharp_files[:500]:
        text = _read_text(path)
        if not text:
            continue
        rel = path.as_posix()

        ns_match = NAMESPACE_RE.search(text)
        if ns_match:
            ns = ns_match.group(1).lower()
            if module_token and module_token not in ns and module_token in rel.lower():
                namespace_issues.append(
                    {
                        "title": "Namespace/folder mismatch for module-scoped file",
                        "severity": "medium",
                        "evidence": f"{rel} namespace '{ns_match.group(1)}' does not include module token '{ctx.module_name}'.",
                    }
                )

        if "controller" in rel.lower() and "repository" in text and " i" not in text.lower():
            clean_issues.append(
                {
                    "title": "Controller appears to depend on concrete repository/service implementation",
                    "severity": "high",
                    "evidence": f"{rel} contains concrete dependency references in controller context.",
                }
            )

        if "controller" in rel.lower():
            using_refs = [u for u in USING_RE.findall(text)]
            direct_repo_refs = [u for u in using_refs if u.lower().endswith("repository") or ".persistence." in u.lower()]
            if direct_repo_refs:
                coupling_issues.append(
                    {
                        "title": "Controller has direct persistence/repository coupling",
                        "severity": "high",
                        "evidence": f"{rel} uses {', '.join(direct_repo_refs[:3])}",
                    }
                )

        ctor = CTOR_RE.search(text)
        if ctor:
            args = ctor.group(2)
            concrete_args = [a.strip() for a in args.split(",") if a.strip() and " I" not in a and "ILogger" not in a]
            if concrete_args:
                coupling_issues.append(
                    {
                        "title": "Controller constructor includes concrete dependency parameter(s)",
                        "severity": "medium",
                        "evidence": f"{rel} constructor args: {', '.join(concrete_args[:3])}",
                    }
                )

    recommended_structure = [
        f"Modules/{ctx.module_name}/Application for use cases and contracts",
        f"Modules/{ctx.module_name}/Infrastructure for persistence and external adapters",
        f"Modules/{ctx.module_name}/Web for controllers and view models",
        "Composition root (Program/Startup) for DI wiring only",
    ]

    architecture_review = {
        "moduleName": ctx.module_name,
        "architecturePolicy": policy,
        "cleanArchitectureIssues": clean_issues[:20],
        "namespaceFolderIssues": namespace_issues[:20],
        "diIssues": di_issues[:20],
        "couplingIssues": coupling_issues[:20],
        "recommendedStructure": recommended_structure,
        "confidence": 0.79 if csharp_files else 0.42,
        "unknowns": [] if csharp_files else ["No converted C# files were discovered for module scope."],
    }
    ctx.write_json("architecture-review.json", architecture_review)

    high_count = sum(1 for issue in (clean_issues + di_issues + coupling_issues + namespace_issues) if issue.get("severity") == "high")
    total_issues = len(clean_issues) + len(namespace_issues) + len(di_issues) + len(coupling_issues)

    findings = []
    if total_issues > 0:
        findings.append(
            {
                "type": "ArchitectureIssuesDetected",
                "scenario": "Clean architecture review",
                "message": f"Detected {total_issues} architecture issue(s), including {high_count} high-severity issue(s).",
                "likelyCause": "Layer boundaries, namespace organization, or DI registrations are incomplete.",
                "evidence": "See architecture-review.json categorized issue lists.",
                "severity": "high" if high_count > 0 else "medium",
                "status": "open",
                "confidence": 0.82,
            }
        )

    return {
        "status": "passed",
        "summary": f"Architecture assessment for {ctx.module_name} found {total_issues} issue(s).",
        "metrics": {
            "violations": total_issues,
            "critical": high_count,
            "warnings": max(0, total_issues - high_count),
            "confidence": architecture_review["confidence"],
        },
        "findings": findings,
        "recommendations": [
            {
                "message": "Address high-severity layering/DI issues first, then resolve namespace and coupling warnings.",
                "priority": "high" if high_count > 0 else "medium",
                "evidence": "Architecture-review categories prioritize remediation order.",
            }
        ],
        "provenanceSummary": {
            "scenarioSources": ["code-evidence"],
            "confidence": architecture_review["confidence"],
            "unknowns": architecture_review["unknowns"],
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
