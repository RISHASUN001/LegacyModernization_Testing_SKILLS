# Skill: test-plan-generation

## name
`test-plan-generation`

## purpose
Generate structured test plan including existing coverage, gaps, and category purpose.

## stage alignment
Supports **Stage: test-plan** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **test-plan** evidence must be generated or refreshed for the selected run.

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
- `test-plan.json`

## artifact files produced
- `artifacts/{module}/{runId}/test-plan-generation/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Suggested tests not mapped to preserve-list items
- Coverage summary ignores edge-case category

## downstream skills
- `unit-test-execution`
- `integration-test-execution`
- `e2e-test-execution`
- `api-test-execution`
- `edge-case-testing`
- `playwright-browser-verification`

## script reference / execution notes
- Entry script: `run.py`
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.

## How To Run
- Single skill:
  - `python run.py --input <module-run-input.json> --artifacts-root <artifacts-root>`
- Full 7-stage pipeline (router):
  - `python skills/legacy-modernization-orchestrator/run.py --input <module-run-input.json>`

## Script Reference / Execution Notes
- Primary script entry is defined in `config.json` (`scriptEntry`).
- Option A mode: run externally in Continue.dev/Claude, persist artifacts/results, then load from dashboard.

## Provenance & Preflight (Revamp)
- Result contract remains `2.0` with additive optional fields: `statusReason`, `preflight`, `trace`, `provenanceSummary`.
- Stage artifacts include provenance envelopes (`type`, `sources`, `confidence`, `unknowns`) where applicable.
- Execution skills run in strict preflight mode and produce `preflight.json` + `execution-log.txt`.
- Primary runtime command:
  - `python run.py --input <module-run-input.json> --artifacts-root <artifacts-root>`

