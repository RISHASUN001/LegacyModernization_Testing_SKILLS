# Skill: integration-test-execution

## Purpose
Execute C# integration/API-level tests against the converted module.

## Stage
`execution`

## Execution Rules
- Use converted app endpoints and module-specific scenarios.
- Capture status codes, assertions, and failures.
- Persist reproducible command/context metadata.

## Dependencies
- `test-plan-generation`

## Outputs
- `integration-test-results.json`
- `result.json`
