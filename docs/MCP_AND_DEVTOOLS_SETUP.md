# MCP and DevTools Setup (Option A)

## Baseline (No MCP install required)

This project runs DevTools diagnostics in **test API mode** by default:
- Skill: `browser-testing-with-devtools`
- Runtime: `skills/browser-testing-with-devtools/run.py`
- Input key: `testApiEndpoint` (defaults to `<baseUrl>/api/test`)

Required endpoint for full diagnostics:
- `GET {testApiEndpoint}/health`

If unavailable, the skill returns a structured degraded failure (`result.json`) instead of crashing.

## Optional MCP mode

If you later have a hosted/available MCP endpoint, copy `.mcp.example.json` to your MCP config location and fill values:
- `url`
- auth header/token

Example file in repo root:
- `.mcp.example.json`

## Continue.dev / Claude flow

1. Run converted C# app
2. Run dashboard app
3. Build run input JSON from dashboard (or `run-inputs/*.json`)
4. In Continue/Claude, run orchestrator with that input
5. Skills write artifacts under:
   - `artifacts/{module}/{runId}/{skill}/...`
6. Dashboard metadata sync reads persisted artifacts and shows results/stages

## Notes

- MCP is **optional** for this baseline.
- Keep `testApiEndpoint` in run input when DevTools evidence is needed.
- Playwright E2E skill and DevTools diagnostics skill are separate and both surface in Stage 5 execution.
