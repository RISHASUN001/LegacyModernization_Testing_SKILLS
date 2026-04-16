# Skill: legacy-modernization-orchestrator

## Purpose
Run the full module-first modernization pipeline end-to-end without redesigning the platform.

## Pipeline Contract (9 stages)
1. C# Discovery
2. C# Logic Understanding
3. Java Discovery
4. Java Logic Understanding
5. Functional Parity
6. Test Plan
7. Execution
8. Findings
9. Iteration Comparison

## Core Rules
- C# code is the primary scope anchor.
- Strict mode must block broad fallback discovery.
- No separate test API product is required for verification.
- Persist artifacts/results for reruns and comparisons.

## Required Inputs
- `moduleName`
- `runId`

## Important Optional Inputs
- `convertedSourceRoot`, `convertedModuleRoot`
- `legacySourceRoot`, `legacyBackendRoot`, `legacyFrontendRoot`
- `moduleStartUrl`, `targetUrl`, `moduleHints.*`
- `strictModuleOnly`

## Outputs
- `artifacts/{module}/{runId}/orchestration-summary.json`
- `artifacts/{module}/{runId}/stage-*/stage-result.json`
- per-skill artifact folders
