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
- Execution mode: external (Continue.dev / Claude in IDE), Option A-first.
