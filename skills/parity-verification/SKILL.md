# Skill: parity-verification

## name
`parity-verification`

## purpose
Verify converted module behavior parity against legacy baselines and identify gaps.
Includes explicit SQL/table parity checks with before/after query mapping when query evidence exists.

## stage alignment
Supports **Stage: findings** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **findings** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `legacySourceRoot`
- `convertedSourceRoot`

## optional inputs
- `allowedCrossModules` (module dependency allow-list, default includes `Shared`)

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/{module}/{runId}/{skill}/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `parity-diff.json`

## parity artifact details
`parity-diff.json` now includes:
- `checks[]`: behavioral parity checks and SQL/table parity summary check.
- `sqlParity.legacyQueryCount`, `sqlParity.convertedQueryCount`, `sqlParity.matchedCount`.
- `sqlParity.tableMatches[]`: table-level legacy vs converted occurrence comparison.
- `sqlParity.beforeAfter[]`: legacy query snippet vs best converted query match, with confidence.
- `dependencyParity.allowedCrossModules`, `dependencyParity.dependencies[]`, `dependencyParity.violations[]` for cross-module dependency policy validation.

## artifact files produced
- `artifacts/{module}/{runId}/parity-verification/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Edge path parity ignored while happy path passes
- Legacy redirect contracts not implemented
- SQL/table mapping drift between Java and C# data access layers

## downstream skills
- `lessons-learned`
- `iteration-comparison`

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

