# Skill Pack (Option A)

Primary execution model:
1. Build `module-run-input.json` in dashboard.
2. Continue.dev / Claude runs skills from this folder in IDE.
3. Skills persist artifacts under `artifacts/{module}/{runId}/{skill}/...`.
4. Dashboard ingests persisted outputs and renders a 7-stage pipeline.
