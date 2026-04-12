# Skill: e2e-test-execution

## name
`e2e-test-execution`

## purpose
Execute end-to-end scenarios validating complete workflow continuity from UI to persistence.

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
- `e2e-scenarios.json`

## artifact files produced
- `artifacts/{module}/{runId}/e2e-test-execution/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Workflow branch mismatch between UI and API
- Session timeout handling divergence

## downstream skills
- `failure-diagnosis`
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.ps1`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
