# Skill: failure-diagnosis

## Purpose
Aggregate and classify execution failures with probable root causes and fix guidance.

## Stage
`findings`

## Diagnosis Rules
- Read outputs from unit/integration/e2e/edge/browser executions.
- Cluster by category: functional, routing, data, environment, flaky.
- Provide evidence references and confidence levels.

## Dependencies
- `unit-test-execution`
- `integration-test-execution`
- `e2e-test-execution`
- `edge-case-testing`
- `playwright-browser-verification`

## Outputs
- `failure-analysis.json`
- `diagnosis-summary.json`
- `result.json`
