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

from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result
from ai_provider import call_ai, AIProviderError

SKILL_NAME = "clean-architecture-assessment"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=SKILL_NAME)
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    payload = normalize_payload(load_payload(args.input))
    errors = validate_payload(payload)
    ctx = make_context(payload, args.artifacts_root, SKILL_NAME)

    if errors:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Input validation failed.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
        )
        print(result_path)
        return 1

    strict_ai = bool(payload.get("strictAIGeneration", True))

    run_root = Path(args.artifacts_root) / ctx.module_name / ctx.run_id
    csharp_map = read_json(run_root / "csharp-module-discovery" / "csharp-module-map.json")
    route_map = read_json(run_root / "csharp-module-discovery" / "controller-route-map.json")
    scope_map = read_json(run_root / "csharp-module-discovery" / "scoped-file-relevance.json")
    csharp_logic = read_json(run_root / "csharp-logic-understanding" / "csharp-logic-summary.json")
    parity = read_json(run_root / "parity-analysis" / "parity-diff.json")

    prompt = {
        "task": (
            "Assess this modernized C# module against a small set of clean architecture expectations. "
            "Return JSON with overallStatus, score, summary, checks, strengths, warnings, recommendations. "
            "Keep it concise and evidence-based."
        ),
        "module": ctx.module_name,
        "csharpModuleMap": csharp_map,
        "controllerRouteMap": route_map,
        "scopedFileRelevance": scope_map,
        "csharpLogic": csharp_logic,
        "parity": parity
    }

    try:
        ai_resp = call_ai(prompt, strict=strict_ai)
        text = str(ai_resp.get("text") or "").strip()
        report = json.loads(text)
        if not isinstance(report, dict):
            raise ValueError("AI did not return a JSON object")
    except (AIProviderError, ValueError, json.JSONDecodeError) as ex:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            f"Clean architecture assessment failed: {ex}",
            artifacts=[],
            findings=[{"type": "CleanArchitectureAssessmentError", "message": str(ex)}],
        )
        print(result_path)
        return 1

    report.setdefault("moduleName", ctx.module_name)
    report.setdefault("score", 0)
    report.setdefault("overallStatus", "warning")
    report.setdefault("summary", "")
    report.setdefault("checks", [])
    report.setdefault("strengths", [])
    report.setdefault("warnings", [])
    report.setdefault("recommendations", [])

    report_path = write_json(ctx.out_dir / "clean-architecture-report.json", report)

    md_lines = [
        f"# Clean Architecture Summary: {ctx.module_name}",
        "",
        f"**Overall Status:** {report.get('overallStatus', 'unknown')}",
        f"**Score:** {report.get('score', 0)}",
        "",
        report.get("summary", ""),
        "",
        "## Checks",
        ""
    ]

    for check in report.get("checks", []):
        md_lines.append(f"- **{check.get('name', 'check')}** — {check.get('status', 'unknown')}")
        md_lines.append(f"  - {check.get('details', '')}")

    if report.get("strengths"):
        md_lines.extend(["", "## Strengths", ""])
        for item in report["strengths"]:
            md_lines.append(f"- {item}")

    if report.get("warnings"):
        md_lines.extend(["", "## Warnings", ""])
        for item in report["warnings"]:
            md_lines.append(f"- {item}")

    if report.get("recommendations"):
        md_lines.extend(["", "## Recommendations", ""])
        for item in report["recommendations"]:
            md_lines.append(f"- {item}")

    summary_md_path = ctx.out_dir / "clean-architecture-summary.md"
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    findings = [
        {
            "type": "ArchitectureWarning",
            "severity": "medium",
            "message": msg
        }
        for msg in report.get("warnings", [])
    ]

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        "Clean architecture assessment completed.",
        artifacts=[report_path, str(summary_md_path.as_posix())],
        metrics={
            "score": report.get("score", 0),
            "checks": len(report.get("checks", [])),
            "warnings": len(report.get("warnings", []))
        },
        findings=findings,
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())