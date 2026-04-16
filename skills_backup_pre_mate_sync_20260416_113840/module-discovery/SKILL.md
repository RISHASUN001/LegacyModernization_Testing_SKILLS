# Skill: module-discovery

## Purpose
Discover Java/JSP scope for the same module after C# anchoring, using evidence-based inclusion.

## Stage
`java-discovery`

## Discovery Requirements
- Discover only module-relevant Java/JSP files.
- Do not include nearby unrelated files by folder proximity alone.
- Use hints and route/workflow context to improve precision.

## Required Inputs
- `moduleName`
- `legacySourceRoot`

## Important Optional Inputs
- `legacyBackendRoot`, `legacyFrontendRoot`
- `moduleHints.keywords`, `moduleHints.javaPackageHints`, `moduleHints.jspFolderHints`
- `strictModuleOnly`

## Outputs
- `discovery-map.json`
- `discovery-evidence.json`
- `result.json`
