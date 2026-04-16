# Skill: browser-testing-with-devtools

## Purpose
Collect app-direct browser diagnostics and DevTools-style findings for module routes.

## Stage
`execution`

## Diagnostic Rules
- Probe live converted app routes, not synthetic test API endpoints.
- Capture console/network/performance/accessibility signals when available.
- Emit strict, evidence-backed failures when preconditions are missing.

## Dependencies
- `test-plan-generation`

## Outputs
- `devtools-browser-diagnostics.json`
- `devtools-route-health.json`
- `result.json`
