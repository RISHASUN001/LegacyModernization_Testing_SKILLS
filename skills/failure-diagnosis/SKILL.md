# Skill: failure-diagnosis

## name
`failure-diagnosis`

## purpose
Correlate failed scenarios across execution stages and propose likely causes with evidence-backed recommendations.

## stage alignment
Supports **Stage: findings** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **findings** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `runId`

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `diagnosis-report.json`

## artifact files produced
- `artifacts/{module}/{runId}/failure-diagnosis/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Root causes merged too broadly
- Evidence pointers missing exact artifacts

## downstream skills
- `lessons-learned`
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
