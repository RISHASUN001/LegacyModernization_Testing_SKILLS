#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
    "name": "failure-diagnosis",
    "stage": "findings",
    "requiredInputs": ["moduleName", "runId"],
}


def _logs_from_artifacts(artifacts: list[str]) -> list[str]:
    out: list[str] = []
    for artifact in artifacts:
        lower = str(artifact).lower()
        if lower.endswith(".txt") or lower.endswith(".log") or "console-logs.json" in lower or "network-failures.json" in lower:
            out.append(artifact)
    return out


def execute(ctx):
    run_results = ctx.iter_run_results()

    scenario_failures: list[dict] = []
    skill_clusters: list[dict] = []
    findings: list[dict] = []

    for result in run_results:
        status = str(result.get("status", "")).lower()
        if status == "passed":
            continue

        skill = str(result.get("skillName") or result.get("skill") or "unknown-skill")
        summary = str(result.get("summary") or "")
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), list) else []

        failing_scenarios = []
        for scenario in (metrics.get("scenarios") or []):
            if isinstance(scenario, dict) and str(scenario.get("status", "")).lower() != "passed":
                failing_scenarios.append(scenario)

        if not failing_scenarios:
            failing_scenarios = [
                {
                    "name": skill,
                    "status": "failed",
                    "notes": summary,
                    "provenance": {"type": "inferred", "sources": [f"artifact:{skill}/result.json"], "confidence": 0.65},
                }
            ]

        likely_cause = summary or "Skill execution reported non-passing status."
        logs = _logs_from_artifacts([str(a) for a in artifacts])

        for scenario in failing_scenarios:
            scenario_name = str(scenario.get("name") or skill)
            scenario_failures.append(
                {
                    "skill": skill,
                    "scenario": scenario_name,
                    "likelyCause": likely_cause,
                    "evidence": {
                        "resultSummary": summary,
                        "logs": logs[:5],
                        "artifacts": [str(a) for a in artifacts][:8],
                    },
                    "provenance": scenario.get("provenance", {"type": "inferred", "sources": [f"artifact:{skill}/result.json"], "confidence": 0.64}),
                }
            )

            findings.append(
                {
                    "type": "ScenarioFailure",
                    "scenario": scenario_name,
                    "message": f"{scenario_name} failed in skill {skill}.",
                    "likelyCause": likely_cause,
                    "evidence": f"skill={skill}; logs={', '.join(logs[:2]) if logs else 'none'}",
                    "severity": "high",
                    "status": "open",
                    "confidence": float((scenario.get("provenance") or {}).get("confidence") or 0.78),
                    "relatedStage": str(result.get("stage") or "execution"),
                    "relatedSkill": skill,
                    "affectedFiles": logs[:3],
                }
            )

        skill_clusters.append(
            {
                "name": f"{skill} failure cluster",
                "likelyCause": likely_cause,
                "affectedSkills": [skill],
                "failedScenarios": [str(s.get("name") or skill) for s in failing_scenarios],
                "evidenceArtifacts": logs[:6],
            }
        )

    diagnosis_report = {
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "totalSkillResults": len(run_results),
        "failedSkillResults": len([r for r in run_results if str(r.get("status", "")).lower() != "passed"]),
        "clusters": skill_clusters,
        "scenarioFailures": scenario_failures,
    }
    ctx.write_json("diagnosis-report.json", diagnosis_report)

    recommendations = [
        {
            "message": "Prioritize scenario-level failures that have concrete console/network/log evidence first.",
            "priority": "high" if scenario_failures else "low",
            "evidence": f"scenarioFailures={len(scenario_failures)}; clusters={len(skill_clusters)}",
        }
    ]

    return {
        "status": "passed",
        "summary": f"Failure diagnosis generated {len(skill_clusters)} cluster(s) and {len(scenario_failures)} scenario-level failures for {ctx.module_name}.",
        "metrics": {
            "clusters": len(skill_clusters),
            "scenarioFailures": len(scenario_failures),
            "highImpact": len(findings),
            "quickWins": 0,
        },
        "findings": findings,
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "inferred"],
            "confidence": 0.8 if scenario_failures else 0.6,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
