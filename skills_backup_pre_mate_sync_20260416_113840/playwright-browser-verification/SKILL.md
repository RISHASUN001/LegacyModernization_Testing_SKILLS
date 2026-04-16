# Skill: playwright-browser-verification

## Purpose
Perform realistic browser verification against the converted app directly.

## Stage
`execution`

## Browser Rules
- No required dependency on a generated test API product.
- Use application routes and workflow-aware checks.
- In strict mode, fail when no executable browser tests are available.
- Persist runtime/network/error evidence.

## Dependencies
- `test-plan-generation`

## Outputs
- `playwright-verification-report.json`
- `playwright-network-summary.json`
- `playwright-runtime-summary.json`
- `result.json`
