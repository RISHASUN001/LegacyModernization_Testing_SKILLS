# Skill: unit-test-execution

## Purpose
Execute C# unit tests for module workflows and persist evidence.

## Stage
`execution`

## Execution Rules
- Run only tests scoped to the module/workflows when possible.
- Capture pass/fail, duration, and failing test identifiers.
- Emit strict failure state on execution errors.

## Dependencies
- `test-plan-generation`

## Outputs
- `unit-test-results.json`
- `result.json`
