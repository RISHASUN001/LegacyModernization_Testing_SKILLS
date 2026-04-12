# Skill: playwright-browser-verification

## name
`playwright-browser-verification`

## purpose
Run browser and devtools-inspired verification with screenshots, console/network/runtime evidence.

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
- `console-logs.json`
- `network-failures.json`
- `dom-state.json`
- `runtime-issues.json`
- `performance-observations.json`
- `screenshots/*`

## artifact files produced
- `artifacts/{module}/{runId}/playwright-browser-verification/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Selector drift causes false failures
- Unhandled runtime exception during save/submit

## downstream skills
- `failure-diagnosis`
- `lessons-learned`

## script reference / execution notes
- Entry script: `run.ps1`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
