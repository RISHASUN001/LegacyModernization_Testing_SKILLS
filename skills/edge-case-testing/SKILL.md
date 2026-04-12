# Skill: edge-case-testing

## name
`edge-case-testing`

## purpose
Execute rare-condition test scenarios for resilience and correctness under non-happy paths.

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
- `edge-case-matrix.json`

## artifact files produced
- `artifacts/{module}/{runId}/edge-case-testing/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Duplicate-submit race causes duplicate rows
- Stale-session flow returns generic errors

## downstream skills
- `failure-diagnosis`
- `iteration-comparison`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
