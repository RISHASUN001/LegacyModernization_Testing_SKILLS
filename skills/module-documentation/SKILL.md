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

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `module-analysis.json`

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
