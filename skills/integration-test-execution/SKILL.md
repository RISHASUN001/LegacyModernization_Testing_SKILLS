# Skill: integration-test-execution

## name
`integration-test-execution`

## purpose
Execute integration tests for data mapping and cross-layer orchestration validation.

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
- `artifacts/{module}/{runId}/integration-test-execution/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Oracle alias mismatch to DTO mapping
- Procedure parameter order mismatch

## downstream skills
- `failure-diagnosis`
- `parity-verification`

## script reference / execution notes
- Entry script: `run.ps1`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
