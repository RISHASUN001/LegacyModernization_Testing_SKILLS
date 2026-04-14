# Skill: legacy-modernization-orchestrator

## Name
`legacy-modernization-orchestrator`

## Purpose
Primary router skill for Option A execution (external IDE execution with persisted artifacts for dashboard replay).

## Stage Alignment
Pipeline router for all 7 stages:
1. Discovery
2. Logic Understanding
3. Architecture Review
4. Test Plan
5. Execution
6. Findings
7. Iteration Comparison

## When To Use
- Use this skill to run a complete module modernization pipeline from a prepared run input JSON.
- Use direct single-skill execution only for focused retries/troubleshooting.

## Required Inputs
- `moduleName`
- `runId`
- `selectedSkills` (optional; defaults to discovered skills)
- optional compatibility aliases accepted: `module`, `run_id`

## Optional Scoped Inputs
- `targetUrl`
- `moduleHints.scopeHint`
- `strictModuleOnly`
- `allowedCrossModules`
- `architecturePolicy`
- `generateModuleClaudeMd`

## Process
1. Load and normalize run input JSON.
2. Validate required fields.
3. Discover runnable skills from `skills/*/config.json`.
4. Resolve selected skills + dependencies.
5. Execute by stage order with deterministic artifact paths.
6. Persist per-stage summaries and `orchestration-summary.json`.

## Outputs
- `artifacts/{module}/{runId}/module-run-input.json`
- `artifacts/{module}/{runId}/stage-<n>/stage-result.json`
- `artifacts/{module}/{runId}/orchestration-summary.json`
- per-skill artifacts under `artifacts/{module}/{runId}/{skill}/...`

## Verification Evidence
- Stage summaries and final orchestration summary include skill statuses and timings.
- Skill `result.json` files contain contract v2.0 fields plus optional additive fields:
  - `statusReason`
  - `preflight`
  - `trace`
  - `provenanceSummary`

## Common Failure Patterns
- Missing run input keys (`moduleName`, `runId`)
- Invalid module paths/hints causing empty discovery scope
- Execution preflight failures (invalid `baseUrl`, app unreachable, missing test tooling/commands)

## Downstream Skills
Router-only meta skill. It orchestrates all selected module skills.

## Script Reference / Execution Notes
- Primary command:
  - `python skills/legacy-modernization-orchestrator/run.py --input <module-run-input.json>`
- Optional flags:
  - `--module <moduleName>`
  - `--run-id <runId>`
  - `--output-dir <custom-run-root>`
  - `--from-stage <n>`
  - `--verbose`

## Continue.dev / Claude (Option A)
1. Generate run input JSON in dashboard (Run Input Builder).
2. Run this orchestrator in IDE via Continue/Claude.
3. Refresh dashboard to replay persisted artifacts and metadata.
