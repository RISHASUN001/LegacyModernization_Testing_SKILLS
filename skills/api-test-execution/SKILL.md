# Skill: api-test-execution

## name
`api-test-execution`

## purpose
Execute API contract and behavior tests against converted endpoints.

## stage alignment
Supports **Stage: execution** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **execution** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `baseUrl`

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `log.txt`

## artifact files produced
- `artifacts/{module}/{runId}/api-test-execution/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Route alias missing from compatibility layer
- Validation payload schema mismatch

## downstream skills
- `failure-diagnosis`
- `playwright-browser-verification`

## script reference / execution notes
- Entry script: `run.ps1`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
