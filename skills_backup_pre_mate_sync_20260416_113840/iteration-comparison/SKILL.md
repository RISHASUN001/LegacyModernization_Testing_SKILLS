# Skill: iteration-comparison

## Purpose
Compare current run against prior runs for parity, execution quality, and stability trends.

## Stage
`iteration-comparison`

## Comparison Rules
- Compare preservation score and workflow parity deltas.
- Compare test pass/fail movement and failure categories.
- Report regressions, improvements, and unresolved gaps.

## Required Inputs
- `moduleName`
- `runId`

## Outputs
- `iteration-comparison.json`
- `trend-summary.json`
- `result.json`
