# Skill: test-plan-generation

## Purpose
Generate workflow-specific C# module tests after parity analysis.

## Stage
`test-plan`

## Planning Requirements
- Group tests by workflow.
- Cover unit, integration, route/form-post, edge, Playwright, DevTools.
- Use discovered C# workflow/routes as primary basis.
- Persist plan artifacts and rerun registry entries.

## Required Inputs
- `moduleName`
- `convertedSourceRoot`

## Outputs
- `test-plan.json`
- `generated-test-plan.json`
- `workflow-test-map.json`
- `result.json`

## Persistence
- Updates `artifacts/{module}/_registry/persistent-test-registry.json` for reruns.
