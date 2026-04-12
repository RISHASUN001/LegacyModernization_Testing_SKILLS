# Skill-Pack Driven Legacy Modernization Ops Console

Revamped hackathon-ready platform for Java EE / JSP / Struts to ASP.NET Core C# modernization.

## Execution Model (Option A First)

1. Build `module-run-input.json` from dashboard.
2. Run selected skills externally in Continue.dev / Claude (IDE).
3. Skills persist outputs to `artifacts/<module>/<run>/<skill>/...`.
4. Dashboard syncs artifacts into SQLite metadata (`data/modernization.db`).
5. Dashboard renders a **7-stage pipeline** with test categories, findings, and iteration deltas.

## 7-Stage Product Flow

1. Discovery
2. Logic Understanding
3. Architecture Review
4. Test Plan
5. Execution
6. Findings
7. Iteration Comparison

## Skill Pack

`skills/` includes:
- `module-discovery`
- `legacy-logic-extraction`
- `module-documentation`
- `clean-architecture-assessment`
- `test-plan-generation`
- `unit-test-execution`
- `integration-test-execution`
- `e2e-test-execution`
- `api-test-execution`
- `edge-case-testing`
- `playwright-browser-verification`
- `failure-diagnosis`
- `lessons-learned`
- `iteration-comparison`
- `parity-verification`

Each skill contains:
- `SKILL.md`
- `config.json`
- executable script (`run.py` or `run.ps1`)

## Seed Data

- Module: `Checklist`
- Runs: `run-001` and `run-002`
- Run-002 demonstrates test improvements, resolved findings, and iteration deltas.

## Run

```bash
cd src/LegacyModernization.Dashboard.Web
DOTNET_CLI_HOME=/tmp dotnet run
```

Open the dashboard and go to **Module Runs → Open Pipeline**.
