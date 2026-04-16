#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_skill_definitions(skills_root: Path) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for cfg in skills_root.glob("*/config.json"):
        data = json.loads(cfg.read_text(encoding="utf-8"))
        name = str(data.get("name") or cfg.parent.name)
        if name == "mate-orchestrator":
            continue
        definitions[name] = {
            "name": name,
            "stage": str(data.get("stage") or "unassigned"),
            "script": cfg.parent / "run.py",
            "inputs": data.get("inputs", []),
            "outputs": data.get("outputs", []),
            "dependencies": data.get("dependencies", [])
        }
    return definitions


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_up_to_date(result_path: Path, dependency_paths: list[Path]) -> bool:
    if not result_path.exists():
        return False
    result_mtime = result_path.stat().st_mtime
    for dep in dependency_paths:
        if dep.exists() and dep.stat().st_mtime > result_mtime:
            return False
    return True


def validate_required_inputs(payload: dict[str, Any], required_inputs: list[str]) -> list[str]:
    missing: list[str] = []
    for key in required_inputs:
        value = payload.get(key)
        if value is None:
            missing.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(key)
            continue
        if isinstance(value, list) and len(value) == 0:
            missing.append(key)
    return missing


def validate_contracts(
    stage_order: list[str],
    stage_meta: dict[str, Any],
    required_evidence: dict[str, Any],
    skills: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    stage_set = set(stage_order)

    unknown_skill_stages = sorted({
        str(skill.get("stage") or "")
        for skill in skills.values()
        if str(skill.get("stage") or "") not in stage_set
    })
    if unknown_skill_stages:
        errors.append(
            "Unknown skill stage(s) not in stageOrder: " + ", ".join(unknown_skill_stages)
        )

    unknown_evidence_stages = sorted([
        stage for stage in required_evidence.keys()
        if stage not in stage_set
    ])
    if unknown_evidence_stages:
        errors.append(
            "requiredEvidence contains stage(s) not in stageOrder: " + ", ".join(unknown_evidence_stages)
        )

    missing_stage_meta = sorted([
        stage for stage in stage_order
        if stage not in stage_meta
    ])
    if missing_stage_meta:
        errors.append(
            "Missing stage metadata for stage(s): " + ", ".join(missing_stage_meta)
        )

    return errors


def ensure_within(root: Path, path: Path, label: str) -> str | None:
    canonical_root = root.resolve()
    canonical_path = path.resolve()
    root_prefix = str(canonical_root)
    path_value = str(canonical_path)
    if not path_value.startswith(root_prefix + "/") and path_value != root_prefix:
        return f"{label} must be inside '{canonical_root}', got '{canonical_path}'."
    return None


def validate_paths(
    mate_root: Path,
    input_path: Path,
    skills_root: Path,
    artifacts_root: Path
) -> list[str]:
    errors: list[str] = []
    expected_skills = (mate_root / "skills").resolve()
    expected_artifacts = (mate_root / "artifacts").resolve()
    expected_run_inputs = (mate_root / "run-inputs").resolve()

    if skills_root.resolve() != expected_skills:
        errors.append(
            f"skills-root must be '{expected_skills}', got '{skills_root.resolve()}'."
        )

    if artifacts_root.resolve() != expected_artifacts:
        errors.append(
            f"artifacts-root must be '{expected_artifacts}', got '{artifacts_root.resolve()}'."
        )

    if not input_path.exists():
        errors.append(f"input file does not exist: '{input_path}'.")
    else:
        location_error = ensure_within(expected_run_inputs, input_path, "input")
        if location_error:
            errors.append(location_error)

    if not skills_root.exists():
        errors.append(f"skills-root does not exist: '{skills_root}'.")

    artifacts_root.mkdir(parents=True, exist_ok=True)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="MATE orchestrator")
    parser.add_argument("--input", required=True)
    parser.add_argument("--skills-root", default="skills")
    parser.add_argument("--artifacts-root", default="artifacts")
    parser.add_argument("--rerun-mode", default="changed", choices=["changed", "full"])
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    skills_root = Path(args.skills_root).resolve()
    artifacts_root = Path(args.artifacts_root).resolve()
    mate_root = Path(__file__).resolve().parents[2]

    path_errors = validate_paths(mate_root, input_path, skills_root, artifacts_root)
    if path_errors:
        out = {
            "status": "failed",
            "summary": "Invalid orchestrator path configuration.",
            "errors": path_errors
        }
        print(json.dumps(out, indent=2))
        return 1

    payload = read_json(input_path)
    module_name = str(payload.get("moduleName") or "__missing-module__")
    run_id = str(payload.get("runId") or "run-001")

    orchestrator_cfg_path = skills_root / "orchestrator" / "config.json"
    orchestrator_cfg = read_json(orchestrator_cfg_path)

    stage_order = orchestrator_cfg.get("stageOrder", [])
    stage_meta = orchestrator_cfg.get("stages", {})
    required_evidence = orchestrator_cfg.get("requiredEvidence", {})
    required_inputs = orchestrator_cfg.get("requiredInputs", [])

    missing_inputs = validate_required_inputs(payload, required_inputs)
    if missing_inputs:
        out = {
            "status": "failed",
            "summary": f"Missing required orchestrator inputs: {', '.join(missing_inputs)}",
            "missingInputs": missing_inputs
        }
        print(json.dumps(out, indent=2))
        return 1

    run_root = artifacts_root / module_name / run_id
    orchestration_root = run_root / "orchestration"
    orchestration_root.mkdir(parents=True, exist_ok=True)

    skills = load_skill_definitions(skills_root)
    contract_errors = validate_contracts(
        stage_order if isinstance(stage_order, list) else [],
        stage_meta if isinstance(stage_meta, dict) else {},
        required_evidence if isinstance(required_evidence, dict) else {},
        skills
    )
    if contract_errors:
        out = {
            "status": "failed",
            "summary": "Invalid orchestrator contract.",
            "errors": contract_errors
        }
        print(json.dumps(out, indent=2))
        return 1

    selected = sorted(
        skills.values(),
        key=lambda x: (stage_order.index(x["stage"]), x["name"])
    )

    grouped_by_stage: dict[str, list[dict[str, Any]]] = {}
    for skill in selected:
        grouped_by_stage.setdefault(str(skill["stage"]), []).append(skill)

    started_at = now_iso()
    stage_results: list[dict[str, Any]] = []
    skill_results: list[dict[str, Any]] = []
    stage_evidence_index: dict[str, list[str]] = {}
    all_passed = True

    for idx, stage in enumerate(stage_order, start=1):
        stage_skills = grouped_by_stage.get(stage, [])
        meta = stage_meta.get(stage, {}) if isinstance(stage_meta, dict) else {}
        next_stage = stage_order[idx] if idx < len(stage_order) else None

        stage_context = {
            "runId": run_id,
            "moduleName": module_name,
            "stage": stage,
            "stageIndex": idx,
            "title": meta.get("title", stage),
            "objective": meta.get("objective", ""),
            "disclosure": {
                "now": {
                    "inputType": meta.get("inputType", "pipeline-input"),
                    "outputType": meta.get("outputType", "stage-artifacts"),
                    "skills": [s["name"] for s in stage_skills]
                },
                "next": {
                    "stage": next_stage,
                    "title": (stage_meta.get(next_stage, {}) if isinstance(stage_meta, dict) and next_stage else {}).get("title", next_stage),
                    "expectedInputType": (stage_meta.get(next_stage, {}) if isinstance(stage_meta, dict) and next_stage else {}).get("inputType", "n/a")
                }
            },
            "contracts": [
                {
                    "skill": s["name"],
                    "inputs": s.get("inputs", []),
                    "outputs": s.get("outputs", []),
                    "dependencies": s.get("dependencies", [])
                }
                for s in stage_skills
            ]
        }
        stage_context_path = orchestration_root / f"stage-{idx:02d}-context.json"
        write_json(stage_context_path, stage_context)

        stage_skill_results: list[dict[str, Any]] = []
        for skill in stage_skills:
            script = Path(skill["script"])
            if not script.exists():
                stage_skill_results.append({
                    "skill": skill["name"],
                    "stage": stage,
                    "status": "failed",
                    "returnCode": 1,
                    "stdout": "",
                    "stderr": f"Missing run.py for skill {skill['name']}",
                    "reused": False,
                    "resultPath": ""
                })
                all_passed = False
                continue

            result_file = run_root / skill["name"] / "result.json"
            dependency_paths = [
                (run_root / str(dep) / "result.json")
                for dep in skill.get("dependencies", [])
                if isinstance(dep, str)
            ]

            reused = False
            if args.rerun_mode == "changed" and is_up_to_date(result_file, dependency_paths):
                reused = True
                proc_return = 0
                proc_stdout = str(result_file.as_posix())
                proc_stderr = ""
            else:
                cmd = ["python3", str(script), "--input", str(input_path), "--artifacts-root", str(artifacts_root)]
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(mate_root))
                proc_return = proc.returncode
                proc_stdout = (proc.stdout or "").strip()
                proc_stderr = (proc.stderr or "").strip()

            status = "passed" if proc_return == 0 else "failed"
            if status == "failed":
                all_passed = False

            skill_result = {
                "skill": skill["name"],
                "stage": stage,
                "returnCode": proc_return,
                "stdout": proc_stdout,
                "stderr": proc_stderr,
                "status": status,
                "reused": reused,
                "resultPath": result_file.as_posix()
            }

            if result_file.exists():
                try:
                    skill_result_json = read_json(result_file)
                    skill_result["summary"] = skill_result_json.get("summary", "")
                    skill_result["artifacts"] = skill_result_json.get("artifacts", [])
                    skill_result["metrics"] = skill_result_json.get("metrics", {})
                    skill_result["findings"] = skill_result_json.get("findings", [])
                except Exception as ex:
                    skill_result["resultReadError"] = str(ex)

            stage_skill_results.append(skill_result)
            skill_results.append(skill_result)

        evidence = []
        for rel in required_evidence.get(stage, []) if isinstance(required_evidence, dict) else []:
            evidence_path = run_root / rel
            evidence.append({
                "path": rel,
                "exists": evidence_path.exists()
            })
        stage_evidence_index[stage] = [e["path"] for e in evidence if e["exists"]]

        stage_status = (
            "passed"
            if stage_skill_results and all(r["status"] == "passed" for r in stage_skill_results)
            else ("skipped" if not stage_skill_results else "failed")
        )
        if stage_status == "failed":
            all_passed = False

        stage_result = {
            "stage": stage,
            "stageIndex": idx,
            "stageTitle": meta.get("title", stage),
            "stageObjective": meta.get("objective", ""),
            "status": stage_status,
            "skills": stage_skill_results,
            "skillCount": len(stage_skill_results),
            "skillsFailed": len([r for r in stage_skill_results if r["status"] == "failed"]),
            "reusedSkills": len([r for r in stage_skill_results if r.get("reused")]),
            "contextFile": stage_context_path.as_posix(),
            "requiredEvidence": evidence
        }
        stage_results.append(stage_result)
        write_json(orchestration_root / f"stage-{idx:02d}-results.json", stage_result)

    summary = {
        "schemaVersion": "2.1",
        "runId": run_id,
        "moduleName": module_name,
        "effectiveRoots": {
            "inputPath": str(input_path),
            "skillsRoot": str(skills_root),
            "artifactsRoot": str(artifacts_root)
        },
        "startedAt": started_at,
        "endedAt": now_iso(),
        "status": "passed" if all_passed else "failed",
        "summary": "MATE orchestration completed with stage contracts, evidence tracking, and rerun support.",
        "stages": stage_results,
        "results": skill_results,
        "stageEvidenceIndex": stage_evidence_index
    }
    summary_path = run_root / "orchestration-summary.json"
    write_json(summary_path, summary)

    out = {
        "status": summary["status"],
        "summaryPath": summary_path.as_posix(),
        "results": skill_results
    }
    print(json.dumps(out, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())