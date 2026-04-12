# Skill: parity-verification

## name
`parity-verification`

## purpose
Verify converted module behavior parity against legacy baselines and identify gaps.

## stage alignment
Supports **Stage: findings** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **findings** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `legacySourceRoot`
- `convertedSourceRoot`

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `parity-diff.json`

## artifact files produced
- `artifacts/{module}/{runId}/parity-verification/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Edge path parity ignored while happy path passes
- Legacy redirect contracts not implemented

## downstream skills
- `lessons-learned`
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
