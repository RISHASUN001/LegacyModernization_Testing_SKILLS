#!/usr/bin/env python3
"""
Legacy Modernization Orchestrator (Python-first, config-driven router)

Option A execution model:
- Reads module-run-input JSON
- Executes selected skills from skills/*/config.json
- Persists per-skill artifacts and stage summaries under artifacts/<module>/<runId>/
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("orchestrator")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SKILLS_ROOT = PROJECT_ROOT / "skills"
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"

STAGE_ORDER = [
    "discovery",
    "logic-understanding",
    "architecture-review",
    "test-plan",
    "execution",
    "findings",
    "iteration-comparison",
]

STAGE_LABELS = {
    "discovery": "Discovery",
    "logic-understanding": "Logic Understanding",
    "architecture-review": "Architecture Review",
    "test-plan": "Test Plan",
    "execution": "Execution",
    "findings": "Findings",
    "iteration-comparison": "Iteration Comparison",
}


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    stage: str
    script_entry: str
    dependencies: list[str]
    external_dependencies: list[str]
    directory: Path

    @property
    def script_path(self) -> Path:
        return self.directory / self.script_entry


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legacy modernization orchestrator")
    parser.add_argument("--input", default=None, help="Path to module run input JSON")
    parser.add_argument("--input-stdin", action="store_true", help="Read input JSON from stdin")
    parser.add_argument("--run-id", default=None, help="Optional runId override")
    parser.add_argument("--module", default=None, help="Optional moduleName override")
    parser.add_argument("--output-dir", default=None, help="Optional run output dir override")
    parser.add_argument("--from-stage", default=1, type=int, help="Resume execution from stage index")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs")
    return parser.parse_args()


def load_input_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_stdin:
        stdin_text = sys.stdin.read()
        if not stdin_text.strip():
            raise ValueError("--input-stdin provided but stdin payload is empty")
        return json.loads(stdin_text)

    if args.input:
        candidate = Path(args.input)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if not candidate.exists():
            raise FileNotFoundError(f"Input file not found: {candidate}")
        return json.loads(candidate.read_text(encoding="utf-8"))

    defaults = [
        PROJECT_ROOT / "module-run-input.json",
        PROJECT_ROOT / "run-inputs" / "module-run-input.browser-test.json",
    ]
    for default_file in defaults:
        if default_file.exists():
            logger.info("Using default input file: %s", default_file)
            return json.loads(default_file.read_text(encoding="utf-8"))

    raise ValueError("No input provided. Use --input, --input-stdin, or create module-run-input.json")


def normalize_payload(payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    normalized = dict(payload)

    module_name = args.module or payload.get("moduleName") or payload.get("module") or ""
    run_id = args.run_id or payload.get("runId") or payload.get("run_id") or ""

    normalized["moduleName"] = module_name
    normalized["runId"] = run_id

    if "legacySourceRoot" not in normalized and "legacy_source_root" in payload:
        normalized["legacySourceRoot"] = payload.get("legacy_source_root", "")
    if "convertedSourceRoot" not in normalized and "converted_source_root" in payload:
        normalized["convertedSourceRoot"] = payload.get("converted_source_root", "")

    selected = payload.get("selectedSkills")
    if isinstance(selected, list):
        normalized["selectedSkills"] = [str(s) for s in selected]
    else:
        normalized["selectedSkills"] = []

    return normalized


def validate_payload(payload: dict[str, Any]) -> list[str]:
    def is_placeholder(value: str) -> bool:
        text = value.strip()
        return bool(text) and text.startswith("<") and text.endswith(">")

    missing: list[str] = []
    module_name = str(payload.get("moduleName", "")).strip()
    run_id = str(payload.get("runId", "")).strip()
    if not module_name or is_placeholder(module_name):
        missing.append("moduleName")
    if not run_id or is_placeholder(run_id):
        missing.append("runId")
    return missing


def load_skill_definitions() -> dict[str, SkillDefinition]:
    definitions: dict[str, SkillDefinition] = {}

    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("_"):
            continue

        config_path = skill_dir / "config.json"
        if not config_path.exists():
            continue

        config = json.loads(config_path.read_text(encoding="utf-8"))
        name = config.get("name", skill_dir.name)

        if name == "legacy-modernization-orchestrator":
            continue

        script_entry = config.get("scriptEntry")
        if not script_entry:
            if (skill_dir / "run.py").exists():
                script_entry = "run.py"
            elif (skill_dir / "run.ps1").exists():
                script_entry = "run.ps1"
            else:
                raise ValueError(f"Skill {name} has no scriptEntry and no run.py/run.ps1")

        stage = config.get("stage", "execution")
        dependencies = [str(d) for d in config.get("dependencies", [])]
        external_dependencies = [str(d) for d in config.get("externalDependencies", [])]

        definition = SkillDefinition(
            name=name,
            stage=stage,
            script_entry=script_entry,
            dependencies=dependencies,
            external_dependencies=external_dependencies,
            directory=skill_dir,
        )

        if not definition.script_path.exists():
            raise FileNotFoundError(
                f"Skill {name} script missing: {definition.script_path}"
            )

        definitions[name] = definition

    if not definitions:
        raise RuntimeError("No skill definitions discovered under skills/")

    return definitions


def resolve_selected_skills(
    normalized_payload: dict[str, Any], skill_defs: dict[str, SkillDefinition]
) -> list[str]:
    requested = [s for s in normalized_payload.get("selectedSkills", []) if isinstance(s, str)]

    if not requested:
        requested = sorted(skill_defs.keys())

    # Remove router meta-skill if user accidentally included it.
    requested = [s for s in requested if s != "legacy-modernization-orchestrator"]

    selected: set[str] = set()

    def include(skill_name: str) -> None:
        if skill_name not in skill_defs:
            logger.debug("Dependency/skill '%s' not found in skill pack. Skipping.", skill_name)
            return
        if skill_name in selected:
            return
        selected.add(skill_name)
        for dep in skill_defs[skill_name].dependencies:
            # dependencies are skill dependencies only; ignore non-skill names.
            include(dep)

    for skill_name in requested:
        include(skill_name)

    # Preserve stage order and then skill-name order for determinism.
    ordered = sorted(
        selected,
        key=lambda s: (
            STAGE_ORDER.index(skill_defs[s].stage) if skill_defs[s].stage in STAGE_ORDER else 999,
            s,
        ),
    )
    return ordered


def command_for_skill(skill: SkillDefinition, input_path: Path, artifacts_root: Path) -> list[str]:
    script = skill.script_path
    suffix = script.suffix.lower()

    if suffix == ".py":
        return ["python3", str(script), "--input", str(input_path), "--artifacts-root", str(artifacts_root)]

    if suffix == ".ps1":
        if shutil.which("pwsh"):
            return ["pwsh", "-File", str(script), "-InputPath", str(input_path), "-ArtifactsRoot", str(artifacts_root)]
        if shutil.which("powershell"):
            return ["powershell", "-File", str(script), "-InputPath", str(input_path), "-ArtifactsRoot", str(artifacts_root)]
        raise RuntimeError(f"Skill {skill.name} requires PowerShell but pwsh/powershell was not found")

    raise RuntimeError(f"Unsupported script type for {skill.name}: {script}")


def run_skill(
    skill: SkillDefinition,
    input_path: Path,
    artifacts_root: Path,
    module_name: str,
    run_id: str,
) -> dict[str, Any]:
    started = now_iso()
    started_perf = time.time()

    command = command_for_skill(skill, input_path, artifacts_root)
    logger.info("Running skill: %s", skill.name)

    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    duration = round(time.time() - started_perf, 3)
    skill_result_path = artifacts_root / module_name / run_id / skill.name / "result.json"

    skill_status = "failed"
    summary = "Skill execution did not produce result.json."

    if skill_result_path.exists():
        try:
            parsed = json.loads(skill_result_path.read_text(encoding="utf-8"))
            skill_status = str(parsed.get("status", "unknown")).lower()
            summary = str(parsed.get("summary", ""))
        except Exception as ex:
            summary = f"Failed to parse result.json: {ex}"
            skill_status = "failed"

    if result.returncode != 0 and skill_status == "passed":
        # Guard against inconsistent process/result status.
        skill_status = "failed"

    ended = now_iso()
    return {
        "skill": skill.name,
        "stage": skill.stage,
        "status": skill_status,
        "startedAt": started,
        "endedAt": ended,
        "durationSeconds": duration,
        "summary": summary,
        "returnCode": result.returncode,
        "stdout": (result.stdout or "")[-2000:],
        "stderr": (result.stderr or "")[-2000:],
        "command": command,
        "resultPath": str(skill_result_path),
    }


def stage_status(skill_results: list[dict[str, Any]]) -> str:
    if not skill_results:
        return "skipped"
    if any(r.get("status") != "passed" for r in skill_results):
        return "failed"
    return "passed"


def main() -> int:
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    raw_payload = load_input_payload(args)
    payload = normalize_payload(raw_payload, args)

    missing = validate_payload(payload)
    if missing:
        logger.error("Invalid run input. Missing required fields: %s", ", ".join(missing))
        module_value = str(payload.get("moduleName") or "").strip()
        run_value = str(payload.get("runId") or "").strip()
        if module_value.startswith("<") and module_value.endswith(">"):
            module_value = ""
        if run_value.startswith("<") and run_value.endswith(">"):
            run_value = ""
        run_root = ARTIFACTS_ROOT / (module_value or "__missing-module__") / (run_value or "__missing-run__")
        run_root.mkdir(parents=True, exist_ok=True)
        summary = {
            "runId": payload.get("runId") or "",
            "moduleName": payload.get("moduleName") or "",
            "status": "failed",
            "startedAt": now_iso(),
            "endedAt": now_iso(),
            "selectedSkills": [],
            "stages": [],
            "failedSkills": [],
            "artifactsRoot": str(run_root),
            "statusReason": "input-validation-failed",
            "missingRequiredInputs": missing,
        }
        summary_path = run_root / "orchestration-summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        logger.info("Summary written: %s", summary_path)
        return 1

    module_name = str(payload["moduleName"])
    run_id = str(payload["runId"])

    skill_defs = load_skill_definitions()
    selected_skills = resolve_selected_skills(payload, skill_defs)

    run_root = Path(args.output_dir).resolve() if args.output_dir else (ARTIFACTS_ROOT / module_name / run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    # Skills expect an artifacts-root, then internally write artifacts/<module>/<run>/<skill>.
    # Derive the root so persisted output remains deterministic regardless of run_root override.
    if run_root.name == run_id and run_root.parent.name == module_name:
        skill_artifacts_root = run_root.parent.parent
    else:
        skill_artifacts_root = ARTIFACTS_ROOT

    # Persist normalized run input for traceability and for skill execution.
    run_input_path = run_root / "module-run-input.json"
    run_input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info("%s", "=" * 72)
    logger.info("Legacy Modernization Orchestrator")
    logger.info("Module: %s", module_name)
    logger.info("Run ID: %s", run_id)
    logger.info("Selected skills: %s", ", ".join(selected_skills))
    logger.info("Artifacts root: %s", run_root)
    logger.info("%s", "=" * 72)

    started_at = now_iso()
    all_results: list[dict[str, Any]] = []
    stages_summary: list[dict[str, Any]] = []

    grouped: dict[str, list[SkillDefinition]] = {stage: [] for stage in STAGE_ORDER}
    for skill_name in selected_skills:
        stage = skill_defs[skill_name].stage
        if stage not in grouped:
            grouped[stage] = []
        grouped[stage].append(skill_defs[skill_name])

    any_failed = False
    for idx, stage in enumerate(STAGE_ORDER, start=1):
        if idx < args.from_stage:
            stages_summary.append(
                {
                    "stage": stage,
                    "stageTitle": STAGE_LABELS.get(stage, stage),
                    "stageIndex": idx,
                    "status": "skipped",
                    "skills": [],
                }
            )
            continue

        stage_skills = grouped.get(stage, [])
        if not stage_skills:
            stages_summary.append(
                {
                    "stage": stage,
                    "stageTitle": STAGE_LABELS.get(stage, stage),
                    "stageIndex": idx,
                    "status": "skipped",
                    "skills": [],
                }
            )
            continue

        logger.info("\n[%d/7] Stage: %s", idx, STAGE_LABELS.get(stage, stage))

        stage_results: list[dict[str, Any]] = []
        for skill in stage_skills:
            outcome = run_skill(skill, run_input_path, skill_artifacts_root, module_name, run_id)
            stage_results.append(outcome)
            all_results.append(outcome)

        current_stage_status = stage_status(stage_results)
        if current_stage_status == "failed":
            any_failed = True

        stage_record = {
            "stage": stage,
            "stageTitle": STAGE_LABELS.get(stage, stage),
            "stageIndex": idx,
            "status": current_stage_status,
            "skillCount": len(stage_results),
            "skillsPassed": sum(1 for r in stage_results if r["status"] == "passed"),
            "skillsFailed": sum(1 for r in stage_results if r["status"] != "passed"),
            "skills": stage_results,
            "startedAt": stage_results[0]["startedAt"] if stage_results else None,
            "endedAt": stage_results[-1]["endedAt"] if stage_results else None,
        }
        stages_summary.append(stage_record)

        stage_file_dir = run_root / f"stage-{idx}"
        stage_file_dir.mkdir(parents=True, exist_ok=True)
        (stage_file_dir / "stage-result.json").write_text(
            json.dumps(stage_record, indent=2), encoding="utf-8"
        )

    ended_at = now_iso()

    summary = {
        "runId": run_id,
        "moduleName": module_name,
        "status": "failed" if any_failed else "passed",
        "startedAt": started_at,
        "endedAt": ended_at,
        "selectedSkills": selected_skills,
        "stages": stages_summary,
        "failedSkills": [r["skill"] for r in all_results if r["status"] != "passed"],
        "artifactsRoot": str(run_root),
    }

    summary_path = run_root / "orchestration-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    logger.info("\nSummary written: %s", summary_path)
    logger.info("Pipeline status: %s", summary["status"])

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
