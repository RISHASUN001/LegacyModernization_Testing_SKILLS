# Skill: java-counterpart-discovery

## Purpose
Map Java backend/JSP frontend counterparts to C# workflows using evidence scoring.

## Stage
`java-discovery`

## Matching Requirements
- Use C# workflow names/routes/logic as anchor.
- Score relevance from path, content, package/import overlap.
- Emit included and excluded files with rationale.
- Respect strict mode thresholding.

## Required Inputs
- `moduleName`
- `legacySourceRoot`
- `convertedSourceRoot`

## Dependencies
- `csharp-logic-understanding`

## Outputs
- `legacy-module-map.json`
- `legacy-workflows.json`
- `java-sql-map.json`
- `java-table-usage.json`
- `java-related-files.json`
- `java-exclusions.json`
- `result.json`
