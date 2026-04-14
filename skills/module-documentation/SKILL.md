# Skill: module-documentation

## name
`module-documentation`

## purpose
Create module documentation artifact used by dashboard Logic Understanding stage.

## stage alignment
Supports **Stage: logic-understanding** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **logic-understanding** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `runId`

## optional inputs
- `generateModuleClaudeMd` (default true) to emit module-scoped CLAUDE guidance under artifacts.
- `targetUrl`, `moduleHints.scopeHint`, `architecturePolicy`, `allowedCrossModules` are included in generated guidance context when provided.

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/{module}/{runId}/{skill}/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `module-analysis.json`
- `artifacts/{module}/{runId}/CLAUDE.md` (module-scoped guidance artifact, when enabled)

## artifact files produced
- `artifacts/{module}/{runId}/module-documentation/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Rules list does not include preserve-critical behavior
- Dependencies omit UI script dependencies

## downstream skills
- `clean-architecture-assessment`
- `test-plan-generation`

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

