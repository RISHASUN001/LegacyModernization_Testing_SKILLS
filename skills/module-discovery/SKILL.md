# Skill: module-discovery

## name
`module-discovery`

## purpose
Discover related Java/JSP/JS/config files, URLs, and database touchpoints for a selected module.

## stage alignment
Supports **Stage: discovery** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **discovery** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `legacySourceRoot`
- `moduleHints.relatedFolders`

## optional scoped inputs
- `targetUrl` (absolute or relative URL path to focus one menu flow)
- `moduleHints.scopeHint` (short natural-language hint, typically <=20 words)
- `strictModuleOnly` (when true, exclude unrelated module files early)
- `allowedCrossModules` (explicit allow-list for cross-module evidence)

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/{module}/{runId}/{skill}/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `discovery-map.json`

`discovery-map.json` now includes `scopeContext` and `totalSelectedFiles` so downstream skills and dashboard views can trace applied scope decisions.

## artifact files produced
- `artifacts/{module}/{runId}/module-discovery/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Path hints miss nested packages
- Keyword-only search includes unrelated modules

## downstream skills
- `legacy-logic-extraction`
- `module-documentation`

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

