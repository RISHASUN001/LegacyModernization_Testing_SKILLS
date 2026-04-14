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
- Resolve artifact output folder under `artifacts/{module}/{runId}/{skill}/`.
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
- Primary entry script: `run.py`
- Compatibility script: `run.ps1` (optional, Windows/pwsh fallback)
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

