# Skill: unit-test-execution

## name
`unit-test-execution`

## purpose
Execute unit tests and persist category-specific results with purpose/scenario context.

## stage alignment
Supports **Stage: execution** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **execution** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `convertedSourceRoot`

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `log.txt`

## artifact files produced
- `artifacts/{module}/{runId}/unit-test-execution/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Validator behavior mismatch with extracted rules
- Mock setup stale after repository changes

## downstream skills
- `failure-diagnosis`
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.ps1`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
