# Skill: iteration-comparison

## name
`iteration-comparison`

## purpose
Summarize previous vs current run deltas: tests added/fixed, failures reduced, new/resolved findings.

## stage alignment
Supports **Stage: iteration-comparison** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **iteration-comparison** evidence must be generated or refreshed for the selected run.

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
- `iteration-delta.json`

## artifact files produced
- `artifacts/{module}/{runId}/iteration-comparison/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Delta counts not aligned with category summaries
- New findings and resolved findings not separated

## downstream skills
- `next iteration planning`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
