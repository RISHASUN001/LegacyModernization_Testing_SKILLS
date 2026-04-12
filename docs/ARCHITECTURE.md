# Architecture (Revamped)

## 1. Platform Shape

- **Primary mode**: Option A external skill execution (Continue.dev/Claude in IDE).
- **Frontend role**: run-input builder + persisted results viewer + iteration tracker.
- **Persistence**:
  - Filesystem artifacts in `artifacts/`
  - SQLite metadata in `data/modernization.db`

## 2. 7-Stage Dashboard IA

Run-centric pipeline page is the main experience:
1. Discovery
2. Logic Understanding
3. Architecture Review
4. Test Plan
5. Execution
6. Findings
7. Iteration Comparison

Entry pages:
- Home
- Skill Library
- Run Input Builder
- Module Runs
- Findings (cross-run)

## 3. Skill Metadata Contract

Each `skills/<skill>/config.json` includes:
- `name`
- `stage`
- `category`
- `scriptEntry`
- `requiredInputs`
- `optionalInputs`
- `outputFiles`
- `artifactFolders`
- `dependencies`
- `summaryOutputType`
- `resultContractVersion`

## 4. Skill Result Contract (v2.0)

Each skill writes `result.json`:
- `skillName`
- `stage`
- `moduleName`
- `runId`
- `status`
- `startedAt`
- `endedAt`
- `summary`
- `metrics`
- `artifacts`
- `findings`
- `recommendations`
- `resultContractVersion`

Stage-specific files are written beside `result.json`.

## 5. SQLite Metadata Shape

- `modules`
- `runs`
- `skills`
- `skill_executions` (stage-aware)
- `test_category_results` (purpose/scenarios/warnings/logs/artifacts/source skill)
- `finding_records` (likely cause/evidence/confidence/affected files)
- `recommendation_records`
- `iteration_deltas` (previous vs current progression)

## 6. Extensibility

The design preserves a clean path to future dashboard-triggered execution because:
- scripts are explicit in config
- dependencies are explicit
- artifact contract is stable and stage-aware
