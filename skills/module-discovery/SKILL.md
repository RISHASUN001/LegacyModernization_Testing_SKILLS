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

## process
- Load `module-run-input.json` from run context.
- Resolve artifact output folder under `artifacts/<module>/<run>/<skill>/`.
- Execute stage-specific analysis/test workflow.
- Persist `result.json` and stage detail artifacts.

## outputs
- `result.json`
- `discovery-map.json`

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
