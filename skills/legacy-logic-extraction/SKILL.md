# Skill: legacy-logic-extraction

## name
`legacy-logic-extraction`

## purpose
Extract module purpose, logic flows, rules, dependencies, and preservation constraints from legacy sources.

## stage alignment
Supports **Stage: logic-understanding** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **logic-understanding** evidence must be generated or refreshed for the selected run.

## required inputs
- `moduleName`
- `legacySourceRoot`

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Load module behavior profiles from `module-profiles.json` (token matching, purpose template, flows, rules, preserve behaviors).
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `logic-summary.json`

## artifact files produced
- `artifacts/{module}/{runId}/legacy-logic-extraction/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Session-driven logic path not visible from controller only
- Implicit business rules hidden in JSP scriptlets

## downstream skills
- `module-documentation`
- `test-plan-generation`

## script reference / execution notes
- Entry script: `run.py`
- Module profile file: `module-profiles.json` (data-driven behavior definitions)
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

