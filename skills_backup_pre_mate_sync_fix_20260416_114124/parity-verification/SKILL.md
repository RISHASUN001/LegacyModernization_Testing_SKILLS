# Skill: parity-verification

## Purpose
Measure functional preservation between C# and Java workflows with evidence-based parity scoring.

## Stage
`functional-parity`

## Parity Requirements
- Compare purpose, flow shape, route/outcome behavior, and side effects.
- Compare SQL and table usage.
- Emit module score and workflow-level scores.
- Highlight preserved, partial, missing, extra, and ambiguous areas.

## Required Inputs
- `moduleName`
- `legacySourceRoot`
- `convertedSourceRoot`

## Dependencies
- `csharp-logic-understanding`
- `java-logic-understanding`
- `java-counterpart-discovery`
- `logic-flow-visualization`

## Outputs
- `functional-parity-map.json`
- `workflow-parity-summary.json`
- `sql-parity-map.json`
- `table-parity-map.json`
- `preservation-score.json`
- `parity-diff.json`
- `result.json`
