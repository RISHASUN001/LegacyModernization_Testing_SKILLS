# Skill: module-documentation

## Purpose
Produce module documentation artifacts for dashboard readability and downstream analysis.

## Stage
`java-logic`

## Required Inputs
- `moduleName`
- `runId`

## Important Optional Inputs
- `generateModuleClaudeMd`
- `targetUrl`, `moduleHints.scopeHint`, `architecturePolicy`

## Outputs
- `module-analysis.json`
- `result.json`
- `artifacts/{module}/{runId}/CLAUDE.md` (optional)
