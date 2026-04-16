# Skill: java-logic-understanding

## Purpose
Build workflow-level Java logic understanding from counterpart evidence and import/package linkage.

## Stage
`java-logic`

## Logic Requirements
- Workflow purpose, entry, branch/forward behavior, validations, side effects.
- Action/Servlet -> service/EJB -> DAO -> JSP flow.
- SQL/table touchpoints.
- Dependency tracing via Java `import` and package resolution.

## Required Inputs
- `moduleName`
- `legacySourceRoot`

## Dependencies
- `java-counterpart-discovery`

## Outputs
- `java-logic-summary.json`
- `result.json`
