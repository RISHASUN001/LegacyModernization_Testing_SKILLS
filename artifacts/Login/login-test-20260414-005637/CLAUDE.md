# CLAUDE Guidance: Login

## Scope
- moduleName: Login
- runId: login-test-20260414-005637
- strictModuleOnly: False
- targetUrl: n/a
- scopeHint: n/a
- architecturePolicy: module-first
- allowedCrossModules: Shared (default)

## Module Purpose
Login module handles authentication and protected-page access flows. Java files discovered: 1. Key routes: /dashboard, /login

## Key Flows
- Open login page
- Session timeout returns to login

## Core Rules
- If credentials are invalid, stay on login page and show validation message
- If session is expired, protected routes redirect to login

## Architecture Guardrails
- Keep controllers thin and workflow logic in Services.
- No direct repository usage from controllers.
- Use gateways/interfaces for cross-module calls.
- Keep shared folder minimal and cross-cutting only.

## Skill Map Snapshot
- Recursive SKILL.md scan executed at generation time.
- api-test-execution
- browser-testing-with-devtools
- clean-architecture-assessment
- csharp-logic-understanding
- csharp-module-discovery
- e2e-test-execution
- edge-case-testing
- failure-diagnosis
- integration-test-execution
- iteration-comparison
- java-counterpart-discovery
- java-logic-understanding
- legacy-logic-extraction
- legacy-modernization-orchestrator
- lessons-learned
- logic-flow-visualization
- module-discovery
- module-documentation
- parity-verification
- playwright-browser-verification
- test-plan-generation
- unit-test-execution

## Notes
- This guidance is module-scoped and should not be applied to unrelated modules.
- Test generation must stay within discovered scope and requested target URL/hint.
