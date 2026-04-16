# Orchestrator Guide: Complete Module-First Workflow

## Input Field Reference (Run Input Builder)

Use these fields with module-first intent:

- `Module Name`: Logical module identifier used in artifact paths and stage summaries.
- `Base URL`: Running converted app URL (for route reachability, Playwright, and DevTools probes).
- `Converted Source Root`: Root of ASP.NET Core converted code.
- `Converted Module Root` (recommended): Exact C# module folder to bound discovery.
- `Entry Controller Name` (optional): Preferred entry controller hint (for naming/trace clarity).
- `Home/Index URL` (optional): UI home/menu path context.
- `Module Start URL` (required boundary): Primary route boundary used to derive module workflows.
- `Menu Path Hints` (optional): Human hints for workflow labels (does not override missing code evidence).
- `Expected Workflow Names` (optional): Desired workflow labels mapped to real discovered routes when possible.
- `Controller/Action Hints` (optional): Additional routing hints.
- `Legacy Source Root`: Legacy monolith root.
- `Legacy Backend Root` (recommended): Java backend scope (for example `src/edcs`).
- `Legacy Frontend Root` (recommended): JSP scope (for example `src/jsp`).
- `Java Package Hints` / `JSP Folder Hints` / `Keywords`: Evidence hints for counterpart matching.
- `Expected Terminal URLs` (optional): Route outcomes used for flow checks and diagnostics probes.
- `Strict Module Only`: Keep enabled for bounded evidence-only discovery.

## Current Pipeline (9 Stages)

1. C# Discovery
2. C# Logic Understanding
3. Java Discovery
4. Java Logic Understanding
5. Functional Parity
6. Test Plan
7. Execution
8. Findings
9. Iteration Comparison

## The Recommended Workflow (End-to-End)

### Step 1: Start C# Application (Terminal 1)

```bash
cd /Users/risha/Documents/Buildathon/src/LegacyModernization.Dashboard.Web
dotnet run
# Running on http://localhost:5000
```

**Dashboard** is now accessible at `http://localhost:5000`

### Step 2: Generate Input Configuration (Browser)

Open `http://localhost:5000` and navigate to **"Input Builder"** section:

1. **Module**: Select "Checklist" (dropdown)
2. **Test Categories** (checkboxes):
   - ☑ Unit Tests
   - ☑ Integration Tests
   - ☑ E2E Tests
   - ☑ API Tests
   - ☑ Edge Case Testing
   - ☑ Browser Testing
3. **Thresholds**:
   - Test Pass Rate: 95%
   - Architecture Score: 75
   - Parity Coverage: 95%
4. **Performance Baselines**:
   - Page Load: 500ms
   - API Response: 100ms
   - Test Timeout: 300s
5. Click **"Generate Input JSON"**
6. **Copy** the generated JSON

**Generated JSON looks like** (example):
```json
{
  "module": "Checklist",
  "iteration": 1,
  "legacy_app_path": "samples/legacy-java-app",
  "modern_app_url": "http://localhost:5000",
  "test_categories": ["unit", "integration", "e2e", "api", "edge-case", "browser"],
  "brs_validation": true,
  "performance_thresholds": {
    "page_load_ms": 500,
    "api_response_ms": 100,
    "test_execution_timeout": 300
  }
}
```

### Step 3: Paste to continue.dev (Claude)

1. Open **continue.dev**
2. Paste the JSON you copied
3. Request:
```
Execute the modernization pipeline with this configuration:
[paste_json_here]
```

### Step 4: Claude Automatically Orchestrates (Terminal Output Watches)

**What Claude does**:
- ✅ Scans workspace for `SKILL.md` files
- ✅ Detects: `skills/legacy-modernization-orchestrator/SKILL.md` → Identifies as **ORCHESTRATOR**
- ✅ Automatically invokes: `echo '{json}' | python3 skills/legacy-modernization-orchestrator/run.py --input-stdin --verbose --stream`
- ✅ Executes cascading 7-stage pipeline:

```
Stage 1: Discovery (60s)          → Finds modules, features
  ↓ Results saved → Database updated
Stage 2: Logic Understanding (120s) → Extract legacy logic
  ↓ Results saved → Database updated
Stage 3: Architecture Review (90s)  → Score modern app
  ↓ Results saved → Database updated
Stage 4: Test Plan (60s)            → Generate 23+ test scenarios
  ↓ Results saved → Database updated
Stage 5: Execution (300s)           → Run 6 test categories in PARALLEL
  - Unit tests, Integration tests, E2E tests
  - API tests, Edge cases, Browser tests
  ↓ Results saved → Database updated
Stage 6: Findings (120s)            → Analyze failures, generate recommendations
  ↓ Results saved → Database updated
Stage 7: Iteration (90s)            → Verify parity vs legacy, track progress
  ↓ Results saved → Database updated

✅ COMPLETE (15-30 minutes total)
```

### Step 5: View Results (Browser Auto-Updates)

Open dashboard: `http://localhost:5000` → **"Modernization"** tab

**Dashboard displays** (auto-refreshed as stages complete):

| Section | Shows |
|---------|-------|
| **Pipeline Status** | Stage 1-7 progress bar |
| **Test Results** | 47 tests: breakdown by category (unit, integration, E2E, API, edge-case, browser) |
| **Findings Panel** | 2-8 issues identified with severity and recommendations |
| **Progress Chart** | Trend line showing improvement across iterations (run-001 vs run-002) |
| **BRS Validation** | Feature parity check: legacy features → modern equivalents |
| **Recommendations** | Actionable next steps for improvement |

---

## How Orchestration Works (Auto-Detection)

```
Input: module-run-input.json (from Dashboard Input Builder)
    ↓
continue.dev receives JSON
    ↓
Claude scans workspace: find SKILL.md files
    ↓
Found: skills/legacy-modernization-orchestrator/SKILL.md
    ↓
Parse SKILL.md header: "🎯 ORCHESTRATOR SKILL"
    ↓
Understand: This is the orchestrator
    ↓
Auto-invoke: python3 run.py --input-stdin < input.json
    ↓
Orchestrator reads input from stdin
    ↓
Execute Stage 1 → Save JSON → Persist to DB → Report "Stage 1 Complete"
Execute Stage 2 → Save JSON → Persist to DB → Report "Stage 2 Complete"
... continues through Stage 7 ...
    ↓
Tell user: "Pipeline complete. View results at http://localhost:5000"
```

**Key**: No manual file paths, no copy-paste of SKILL.md. Claude automatically detects and invokes.

---

## Database Persistence (Automatic)

All results automatically stored in: `data/modernization.db`

**Tables**:
- `orchestration_runs` - Run metadata (ID, module, start/end time, status)
- `orchestration_stages` - Each stage's result (number, name, status, duration, result file)
- `orchestration_findings` - 2-8 findings per run with severity & recommendations
- `modernization_progress` - Test pass rate, parity %, architecture score per iteration

**Example Query** (if manually checking):
```bash
sqlite3 data/modernization.db \
  "SELECT stage_name, finding, recommendation FROM orchestration_findings WHERE iteration = (SELECT MAX(iteration) FROM orchestration_findings) ORDER BY severity DESC;"
```

---

## Execution Timeline

| Stage | Duration | What It Does |
|-------|----------|--------------|
| **Stage 1: Discovery** | 60s | Find modules, features in legacy code |
| **Stage 2: Logic Understanding** | 120s | Extract legacy logic patterns, document modern equivalents |
| **Stage 3: Architecture Review** | 90s | Score modern app quality, identify violations |
| **Stage 4: Test Plan** | 60s | Generate 23+ test scenarios |
| **Stage 5: Execution** | ~150-200s effective | Run 6 test categories in PARALLEL (stops at longest test) |
| **Stage 6: Findings** | 120s | Analyze test failures, generate recommendations |
| **Stage 7: Iteration** | 90s | Verify parity vs legacy, track progress across iterations |
| **TOTAL** | **15-30 min** | All stages, efficient parallelization |

---

## Cascading Behavior

Each stage **automatically**:
1. ✓ Waits for previous stage to complete
2. ✓ Uses previous stage's output as input
3. ✓ Executes its own scripts/tests
4. ✓ Saves results to JSON files
5. ✓ **Persists results to database immediately**
6. ✓ Updates frontend dashboard
7. ✓ Either proceeds to next stage or halts if critical error

**Error Handling**:
- If Stage N fails → Stages N+1, N+2... marked "skipped" (dependency failed)
- Error message logged to database
- Frontend displays error with recovery options

**Example**: Stage 3 fails due to missing architecture files → Stages 4-7 skipped → User prompted to fix Stage 3 → Can resume from Stage 4

---

## Success Indicators

Pipeline is **successful** when:

✅ All 7 stages show "COMPLETED" in database
✅ Stage 5: 45-47 of 47 tests passed (≥95% pass rate)
✅ Stage 6: 2-8 actionable findings identified
✅ Stage 7: Feature parity ≥ 95% vs legacy
✅ Dashboard displays all results without errors
✅ `artifacts/Checklist/run-001/orchestration-summary.json` shows `stages_failed: []`

---

## File Organization

```
Project Root
├── skills/legacy-modernization-orchestrator/
│   ├── SKILL.md           ← Orchestrator specification (Claude reads this)
│   ├── run.py             ← Main orchestrator script (Claude invokes this)
│   └── config.json        ← Thresholds, timeouts, settings
│
├── src/LegacyModernization.Dashboard.Web/
│   ├── Program.cs
│   ├── Controllers/
│   │   └── InputBuilderController.cs  ← Generates module input config
│   └── ...
│
├── artifacts/
│   └── Checklist/
│       └── run-001/        ← Results of this execution
│           ├── stage-1/stage-result.json
│           ├── stage-2/stage-result.json
│           ├── stage-3/stage-result.json
│           ├── stage-4/stage-result.json
│           ├── stage-5/stage-result.json
│           ├── stage-6/stage-result.json
│           ├── stage-7/stage-result.json
│           └── orchestration-summary.json
│
├── data/modernization.db   ← SQLite (all results persistent)
│
└── samples/legacy-java-app/  ← Reference (for discovery, logic extraction)
    ├── LoginServlet.java
    ├── index.jsp
    ├── dashboard.jsp
    └── README.md
```

---

## Iteration Tracking (Automatic)

Each time you run the pipeline:

| Run | Iteration | Purpose |
|-----|-----------|---------|
| **Run 001** | 1 | **Baseline** - Initial metrics |
| **Run 002** | 2 | **Compare** - See what changed vs Run 001 |
| **Run 003** | 3 | **Trend** - Cumulative progress |
| **Run 004** | 4 | **Verify** - Confirm fixes worked |

**Dashboard automatically**:
- Tracks each iteration
- Calculates deltas (improvement/regression)
- Shows trend line across iterations
- Highlights progress areas

Example:
```
Run-001: 42/47 tests pass (89%)
Run-002: 45/47 tests pass (95%) ↑ +3 tests fixed
Run-003: 47/47 tests pass (100%) ↑ +2 tests fixed
```

---

## Input Builder on Dashboard

**Location**: `http://localhost:5000` → Menu → "Input Builder" (or similar)

**Form Fields**:
- **Module**: Checklist, Orders, Inventory, etc. (dropdown)
- **Test Categories**: Checkboxes for each test type
- **Thresholds**: Sliders for pass rate, architecture score, parity target
- **Performance**: Text inputs for timeouts

**Output**: Runnable JSON configuration

**Usage**: Copy → Paste to continue.dev → Request execution

---

## Monitoring (Optional)

If you want to watch in real-time:

**Terminal 2** (while Claude is executing):
```bash
# Watch database updates
watch -n 1 "sqlite3 data/modernization.db 'SELECT stage_name, status, duration_seconds FROM orchestration_stages ORDER BY stage_number DESC LIMIT 7;'"
```

**Terminal 3** (check file output):
```bash
# Watch artifacts directory
ls -lah artifacts/Checklist/run-001/
```

**Browser**: Dashboard auto-refreshes every 1-2 seconds as stages complete

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "Claude doesn't detect orchestrator" | SKILL.md not in expected location | Ensure `skills/legacy-modernization-orchestrator/SKILL.md` exists |
| "localhost:5000 refused" | C# app not running | `dotnet run` in Terminal 1 |
| "Input contains invalid JSON" | Copy-paste error or formatting | Re-generate from Input Builder and copy again |
| "Stage 5 timeout" | Tests take >5 minutes | Increase timeout in `config.json`, or run fewer test categories |
| "Database locked error" | Previous run still writing | Wait 30s or kill Python process: `pkill python3` |
| Dashboard shows no results | Database query failed | Check `data/modernization.db` exists: `ls -lh data/` |

---

## Next Steps After Success

1. ✅ Review findings on dashboard
2. ✅ Fix any identified issues in C# code
3. ✅ Run input builder again, update configuration
4. ✅ Paste new JSON to continue.dev
5. ✅ Compare older runs (run-001 vs run-002) in dashboard
6. ✅ Verify all BRS requirements are met

---

## Key Features

✅ **Automatic Detection** - Claude finds orchestrator SKILL.md
✅ **Auto-Cascading** - Stages run sequentially with auto-persistence
✅ **Parallel Stage 5** - 6 test categories run simultaneously
✅ **Database Persistence** - All results auto-saved to `modernization.db`
✅ **Frontend Integration** - Dashboard auto-updates as stages complete
✅ **Iteration Tracking** - Previous runs stored and compared
✅ **Error Handling** - Failures skip dependent stages gracefully
✅ **Zero Manual Steps** - Input Builder → continue.dev → Auto-execution → Results

---

**Status**: ✅ Ready for automated execution
**Estimated Time**: 15-30 minutes per run
**Next Action**: Start C# app + Open continue.dev
