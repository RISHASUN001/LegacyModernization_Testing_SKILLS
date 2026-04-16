# Skill: api-test-execution

## Purpose
Optionally execute API-focused validation where suitable tests/endpoints exist.

## Stage
`execution`

## Important Note
This skill is optional and not required as a standalone product in the module-first pipeline.

## Execution Rules
- Run only when applicable API tests are defined.
- Report skipped status clearly when not applicable.
- Persist endpoint-level evidence for executed checks.

## Outputs
- `api-test-results.json`
- `result.json`
