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

SKILL_NAME = "findings-synthesis"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def collect_existing_findings(run_root: Path, skip_skill: str) -> list[dict[str, Any]]:
    aggregated: list[dict[str, Any]] = []
    if not run_root.exists():
        return aggregated

    for skill_dir in run_root.iterdir():
        if not skill_dir.is_dir() or skill_dir.name == skip_skill:
            continue
        result_file = skill_dir / "result.json"
        if not result_file.exists():
            continue
        data = read_json(result_file)
        for item in data.get("findings", []) if isinstance(data, dict) else []:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched.setdefault("sourceSkill", skill_dir.name)
                aggregated.append(enriched)
    return aggregated


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

    parity = read_json(run_root / "parity-analysis" / "parity-diff.json")
    clean_arch = read_json(run_root / "clean-architecture-assessment" / "clean-architecture-report.json")
    unit_results = read_json(run_root / "test-execution-unit" / "unit-test-results.json")
    integration_results = read_json(run_root / "test-execution-integration" / "integration-test-results.json")
    playwright_results = read_json(run_root / "test-execution-playwright" / "playwright-results.json")
    aggregated_findings = collect_existing_findings(run_root, SKILL_NAME)

    prompt = {
        "task": (
            "Synthesize the final findings for this module. "
            "Return JSON with moduleName, overallStatus, summary, preservationScore, "
            "keyFindings, failedAreas, likelyCauses, recommendedFixes, nextTests. "
            "Keep it concise and dashboard-friendly."
        ),
        "module": ctx.module_name,
        "parity": parity,
        "cleanArchitecture": clean_arch,
        "unitResults": unit_results,
        "integrationResults": integration_results,
        "playwrightResults": playwright_results,
        "aggregatedFindings": aggregated_findings
    }

    try:
        ai_resp = call_ai(prompt, strict=strict_ai)
        text = str(ai_resp.get("text") or "").strip()
        synthesis = json.loads(text)
        if not isinstance(synthesis, dict):
            raise ValueError("AI did not return a JSON object")
    except (AIProviderError, ValueError, json.JSONDecodeError) as ex:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            f"Findings synthesis failed: {ex}",
            artifacts=[],
            findings=[{"type": "FindingsSynthesisError", "message": str(ex)}],
        )
        print(result_path)
        return 1

    synthesis.setdefault("moduleName", ctx.module_name)
    synthesis.setdefault("overallStatus", "warning")
    synthesis.setdefault("summary", "")
    synthesis.setdefault("preservationScore", parity.get("overallParityScore", 0))
    synthesis.setdefault("keyFindings", [])
    synthesis.setdefault("failedAreas", [])
    synthesis.setdefault("likelyCauses", [])
    synthesis.setdefault("recommendedFixes", [])
    synthesis.setdefault("nextTests", [])

    synthesis_path = write_json(ctx.out_dir / "findings-synthesis.json", synthesis)

    dashboard_view = {
        "moduleName": ctx.module_name,
        "overallStatus": synthesis.get("overallStatus", "warning"),
        "summary": synthesis.get("summary", ""),
        "preservationScore": synthesis.get("preservationScore", 0),
        "keyFindings": synthesis.get("keyFindings", []),
        "failedAreas": synthesis.get("failedAreas", []),
        "recommendedFixes": synthesis.get("recommendedFixes", [])
    }
    dashboard_path = write_json(ctx.out_dir / "findings-dashboard.json", dashboard_view)

    md_lines = [
        f"# Findings Summary: {ctx.module_name}",
        "",
        f"**Overall Status:** {synthesis.get('overallStatus', 'unknown')}",
        f"**Preservation Score:** {synthesis.get('preservationScore', 0)}",
        "",
        synthesis.get("summary", ""),
        ""
    ]

    if synthesis.get("keyFindings"):
        md_lines.extend(["## Key Findings", ""])
        for item in synthesis["keyFindings"]:
            md_lines.append(f"- {item}")

    if synthesis.get("failedAreas"):
        md_lines.extend(["", "## Failed Areas", ""])
        for item in synthesis["failedAreas"]:
            md_lines.append(f"- {item}")

    if synthesis.get("likelyCauses"):
        md_lines.extend(["", "## Likely Causes", ""])
        for item in synthesis["likelyCauses"]:
            md_lines.append(f"- {item}")

    if synthesis.get("recommendedFixes"):
        md_lines.extend(["", "## Recommended Fixes", ""])
        for item in synthesis["recommendedFixes"]:
            md_lines.append(f"- {item}")

    if synthesis.get("nextTests"):
        md_lines.extend(["", "## Additional Tests To Add", ""])
        for item in synthesis["nextTests"]:
            md_lines.append(f"- {item}")

    md_path = ctx.out_dir / "findings-summary.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    findings = [
        {
            "type": "SynthesisFinding",
            "severity": "medium",
            "message": msg
        }
        for msg in synthesis.get("failedAreas", [])
    ]

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        f"Synthesized findings for module {ctx.module_name}.",
        artifacts=[synthesis_path, dashboard_path, str(md_path.as_posix())],
        metrics={
            "preservationScore": synthesis.get("preservationScore", 0),
            "keyFindings": len(synthesis.get("keyFindings", [])),
            "failedAreas": len(synthesis.get("failedAreas", []))
        },
        findings=findings,
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())