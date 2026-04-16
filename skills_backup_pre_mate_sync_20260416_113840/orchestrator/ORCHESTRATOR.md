# mate-orchestrator

## Stage Order (10 Stages)
1. csharp-discovery
2. csharp-logic-understanding
3. java-discovery
4. legacy-logic-understanding
5. diagram-generation
6. functional-parity-and-sql-table-comparison
7. ai-test-generation
8. test-execution
9. clean-architecture-and-findings
10. pipeline-vanity-check

## Path Guardrails (MATE-only)
- `--skills-root` must be exactly `MATE/skills`.
- `--artifacts-root` must be exactly `MATE/artifacts`.
- `--input` must be a file under `MATE/run-inputs`.
- Orchestrator fails fast if any guardrail is violated.
- Effective roots are recorded in `orchestration-summary.json` under `effectiveRoots`.

## Copilot Chat Paste-to-Run Workflow
- If UI input submission is blocked, you can paste JSON directly in Copilot chat.
- Chat (or terminal) can run:
  - `python3 MATE/skills/orchestrator/invoke_from_json.py --json '{...}'`
  - or `python3 MATE/skills/orchestrator/invoke_from_json.py --json-file /path/to/payload.json`
- This helper will:
  - save payload to `MATE/run-inputs/run-input.<module>.<timestamp>.json`
  - invoke orchestrator with MATE-only roots
  - print invocation output and exit code

## Required Run Inputs
- moduleName
- workflowNames[]
- convertedRoots[]
- legacyBackendRoots[]
- legacyFrontendRoots[]
- baseUrl
- startUrl
- dotnetTestTarget

## Optional Run Inputs
- strictModuleOnly
- strictAIGeneration
- enableUserInputPrompting
- keywords[]
- controllerHints[]
- viewHints[]
- expectedEndUrls[]

## Core Rules
- Module-first discovery is mandatory.
- C# discovery is the source of truth.
- Legacy discovery must be anchored from C# evidence.
- Workflow scoping is mandatory. If the selected workflow is only a sub-area of a module, discovery must stay within that scope.
- strictAIGeneration=true means AI-driven stages must fail clearly if AI generation is unavailable.
- Test generation must use prior artifacts from discovery, logic, diagrams, and parity.
- Playwright is the E2E/browser layer. There is no separate E2E stage outside Playwright.
- Unit and integration execution use `dotnet test` against `dotnetTestTarget`.
- Playwright execution uses Python + pytest, starting from `startUrl` under `baseUrl`.

## User Prompt Checkpoint
- Checkpoint occurs between stage 7 and stage 8.
- If required inputs are missing for generated tests and enableUserInputPrompting=true, run pauses as AwaitingUserInput.
- User input is persisted and reused in reruns.
- Prompting is mainly for browser/workflow tests where payloads cannot be inferred.

## Artifact Flow
- Artifacts persist under: `MATE/artifacts/{moduleName}/{runId}/{skillName}/`
- Each skill writes `result.json` plus declared artifacts.
- Stage 7 must output generated test artifacts for:
  - unit
  - integration
  - playwright
  - edge
- Stage 8 must output execution artifacts for:
  - unit
  - integration
  - playwright
- Stage 10 validates required artifacts, generated tests, and execution evidence.

## Test Execution Defaults
- Generated unit tests are copied to: `Tests/Unit/{moduleName}/`
- Generated integration tests are copied to: `Tests/Integration/{moduleName}/`
- Generated Playwright tests are copied to: `Tests/Playwright/{moduleName}/`
- Playwright execution command is: `pytest`
- Playwright execution uses environment:
  - `BASE_URL`
  - `START_URL`

## Rerun Behavior
- Reruns reuse unchanged artifacts.
- Only invalidated downstream stages are regenerated.
- Prior user-input payloads are reused unless explicitly replaced.
- Iteration comparison records:
  - tests added
  - tests removed
  - failures reduced/increased
  - parity changes
  - findings deltas

## Final Readiness Gate
- Stage 10 must verify:
  - required discovery artifacts exist
  - required logic artifacts exist
  - diagrams exist
  - parity outputs exist
  - generated tests exist
  - execution results exist
  - findings exist
- Final recommendation must be one of:
  - ship-with-confidence
  - needs-review
  - hold