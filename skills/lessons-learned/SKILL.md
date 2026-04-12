# Skill: lessons-learned

## name
`lessons-learned`

## purpose
Capture lessons, resolved issue context, and repeatable fixes from each modernization run.

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
- `lessons.json`

## artifact files produced
- `artifacts/{module}/{runId}/lessons-learned/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Lessons do not link to measurable impact
- Resolution notes missing run traceability

## downstream skills
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
