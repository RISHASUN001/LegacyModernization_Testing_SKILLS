# Skill: clean-architecture-assessment

## name
`clean-architecture-assessment`

## purpose
Assess converted C# module against clean architecture boundaries and target structure guidance.

## stage alignment
Supports **Stage: architecture-review** in the 7-stage modernization pipeline.

## when to use
Use this skill when Stage **architecture-review** evidence must be generated or refreshed for the selected run.

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
- `architecture-review.json`

## artifact files produced
- `artifacts/{module}/{runId}/clean-architecture-assessment/`

## verification evidence
- `result.json` contains status, metrics, findings, recommendations, artifacts, stage, and contract version.
- Stage detail files provide evidence rendered directly in dashboard stage panels.

## common failure patterns
- Direct infrastructure usage from web layer
- Missing abstraction boundaries for repositories

## downstream skills
- `test-plan-generation`
- `failure-diagnosis`

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
