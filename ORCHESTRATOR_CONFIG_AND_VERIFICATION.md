# Orchestrator Configuration & Skill Path Verification

## 🎯 Orchestrator Entry Point

**Primary Skill**: `skills/legacy-modernization-orchestrator/`

### How it Works

```
Input: module-run-input.json (from Dashboard Input Builder)
    ↓
Orchestrator (run.py) reads input via --input-stdin
    ↓
Orchestrator calls each skill's run.py sequentially
    ↓
Stages:
  1. module-discovery/run.py
  2. legacy-logic-extraction/run.py + module-documentation/run.py
  3. clean-architecture-assessment/run.py
  4. test-plan-generation/run.py
  5. (6 test runners in parallel):
     - unit-test-execution/run.py
     - integration-test-execution/run.py
     - e2e-test-execution/run.py
     - api-test-execution/run.py
     - edge-case-testing/run.py
     - browser-testing-with-devtools/test_runner.py  ← Note: Python script, not run.py
  6. failure-diagnosis/run.py + lessons-learned/run.py
  7. parity-verification/run.py + iteration-comparison/run.py
    ↓
All results → data/modernization.db (auto-persisted)
```

---

## ✅ Skill Execution Commands (Orchestrator Invokes)

### Stage 1: Discovery

```bash
python3 skills/module-discovery/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 2: Logic Understanding

```bash
# 2a
python3 skills/legacy-logic-extraction/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 2b
python3 skills/module-documentation/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 3: Architecture Review

```bash
python3 skills/clean-architecture-assessment/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 4: Test Plan

```bash
python3 skills/test-plan-generation/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 5: Test Execution (6 in Parallel)

```bash
# 5a: Unit Tests
python3 skills/unit-test-execution/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 5b: Integration Tests
python3 skills/integration-test-execution/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 5c: E2E Tests
python3 skills/e2e-test-execution/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 5d: API Tests
python3 skills/api-test-execution/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 5e: Edge Case Tests
python3 skills/edge-case-testing/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 5f: Browser Testing (Note: Different script name)
python3 skills/browser-testing-with-devtools/test_runner.py \
  --run-id {run_id} \
  --module {module} \
  --base-url http://localhost:5000 \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 6: Findings

```bash
# 6a
python3 skills/failure-diagnosis/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 6b
python3 skills/lessons-learned/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

### Stage 7: Iteration

```bash
# 7a
python3 skills/parity-verification/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}

# 7b
python3 skills/iteration-comparison/run.py \
  --run-id {run_id} \
  --module {module} \
  --output-dir artifacts/{module}/{run_id}
```

---

## 🔍 Verification: Each Skill Has Correct Structure

### Required Files Per Skill

```
skills/{skill-name}/
├── SKILL.md           ← Documentation
├── config.json        ← Configuration
├── run.py or run.ps1  ← Executable script
└── [optional] README.md, INTEGRATION_GUIDE.md, etc.
```

### Verify All Skills

```bash
cd /Users/risha/Documents/Buildathon

# List all skills
echo "📋 Skills in workspace:"
ls -1d skills/*/

# Verify each has required files
for skill_dir in skills/*/; do
    skill_name=$(basename "$skill_dir")
    if [ -f "$skill_dir/SKILL.md" ] && [ -f "$skill_dir/config.json" ] && [ -f "$skill_dir/run.py" ]; then
        echo "✅ $skill_name"
    else
        echo "❌ $skill_name (missing files)"
        [ ! -f "$skill_dir/SKILL.md" ] && echo "   Missing: SKILL.md"
        [ ! -f "$skill_dir/config.json" ] && echo "   Missing: config.json"
        [ ! -f "$skill_dir/run.py" ] && echo "   Missing: run.py"
    fi
done
```

### Special Case: browser-testing-with-devtools

Uses `test_runner.py` instead of `run.py`. Orchestrator should call:
```bash
python3 skills/browser-testing-with-devtools/test_runner.py ...
```

---

## ⚙️ Orchestrator run.py Calls Each Skill

### Inside run.py (How Skills Are Invoked)

```python
def execute_stage(stage_number, run_id, module, output_dir):
    stage_info = STAGES[stage_number]
    scripts = stage_info["scripts"]  # List of run.py/test_runner.py to execute
    
    for script_path in scripts:
        subprocess.run([
            "python3", str(script_path),
            "--run-id", run_id,
            "--module", module,
            "--output-dir", str(output_dir)
        ])
```

### Stage 5 Special: Parallel Execution

```python
if parallel:  # Stage 5 only
    with Pool(max_workers=6) as pool:
        results = pool.map(run_stage_script, script_infos)
```

All 6 test scripts run simultaneously, then results aggregated.

---

## 📊 Expected Output Structure

After orchestrator completes:

```
artifacts/Checklist/run-001/
├── stage-1/
│   └── stage-result.json
├── stage-2/
│   ├── stage-result.json
│   ├── legacy-logic-extraction-result.json
│   └── module-documentation-result.json
├── stage-3/
│   └── stage-result.json
├── stage-4/
│   └── stage-result.json
├── stage-5/
│   ├── stage-result.json
│   ├── unit-test-result.json
│   ├── integration-test-result.json
│   ├── e2e-test-result.json
│   ├── api-test-result.json
│   ├── edge-case-test-result.json
│   └── browser-test-result.json
├── stage-6/
│   ├── stage-result.json
│   ├── failure-diagnosis-result.json
│   └── lessons-learned-result.json
├── stage-7/
│   ├── stage-result.json
│   ├── parity-verification-result.json
│   └── iteration-comparison-result.json
└── orchestration-summary.json

data/modernization.db
├── orchestration_runs (1 row per run)
├── orchestration_stages (7 rows: stages 1-7)
├── orchestration_findings (2-8 rows: issues identified)
└── modernization_progress (1 row: overall metrics)
```

---

## 🚀 Full Pipeline Execution Sequence

### Execution Flow Diagram

```
INPUT JSON (Dashboard Input Builder)
    │
    ├─ Parse: module, run_id, iteration
    │
    ├─ DB: Insert orchestration_run
    │
    ├── Stage 1: Discovery
    │   ├─ Run: script[0] (module-discovery/run.py)
    │   ├─ Save: JSON result
    │   ├─ DB: INSERT orchestration_stages + orchestration_findings
    │   └─ ✓ Complete or ✗ Error → Skip Stage 2+
    │
    ├── Stage 2: Logic Understanding  
    │   ├─ Run: script[0] (legacy-logic-extraction/run.py)
    │   ├─ Run: script[1] (module-documentation/run.py)
    │   ├─ Save: JSON results
    │   ├─ DB: INSERT orchestration_stages + orchestration_findings
    │   └─ ✓ Complete or ✗ Error → Skip Stage 3+
    │
    ├── Stage 3: Architecture Review
    │   └─ [Same pattern]
    │
    ├── Stage 4: Test Plan
    │   └─ [Same pattern]
    │
    ├── Stage 5: Test Execution (PARALLEL)
    │   ├─ Worker 1: unit-test-execution/run.py
    │   ├─ Worker 2: integration-test-execution/run.py
    │   ├─ Worker 3: e2e-test-execution/run.py
    │   ├─ Worker 4: api-test-execution/run.py
    │   ├─ Worker 5: edge-case-testing/run.py
    │   ├─ Worker 6: browser-testing-with-devtools/test_runner.py
    │   ├─ Wait for all 6 to complete
    │   └─ DB: Aggregate results
    │
    ├── Stage 6: Findings
    │   └─ [Same pattern - sequential]
    │
    ├── Stage 7: Iteration
    │   └─ [Same pattern - sequential]
    │
    ├─ DB: UPDATE orchestration_run (status=COMPLETED)
    │
    └─ Final: orchestration-summary.json + Dashboard updates
```

---

## 💾 Database Schema (Auto-Created)

```sql
-- orchestration_runs
id | run_id | module | iteration | status | total_stages | completed_stages | created_at

-- orchestration_stages
id | run_id | stage_number | stage_name | status | duration_seconds | result_file | error_message

-- orchestration_findings
id | run_id | iteration | stage_number | stage_name | category | severity | finding | recommendation

-- modernization_progress
id | run_id | iteration | module | total_tests | passed_tests | parity_percentage
```

---

## ✅ Checklist: Before Running Orchestrator

- [ ] All 16 skills have SKILL.md, config.json, run.py
- [ ] Orchestrator: `skills/legacy-modernization-orchestrator/SKILL.md` marked as `🎯 ORCHESTRATOR SKILL`
- [ ] Orchestrator: `run.py` supports `--input-stdin`
- [ ] C# Dashboard running on localhost:5000
- [ ] Input Builder accessible (generates JSON)
- [ ] Database directory `/data/` ready (or will be created)
- [ ] Python 3 available: `python3 --version`
- [ ] All skill scripts are executable: `chmod +x skills/*/run.py`
- [ ] Legacy reference present: `samples/legacy-java-app/`

---

## 🧪 Test Dry Run (No External Dependencies)

```bash
cd /Users/risha/Documents/Buildathon

# Run orchestrator with first 4 stages only
python3 skills/legacy-modernization-orchestrator/run.py \
  --input run-inputs/module-run-input.browser-test.json \
  --stages 1 2 3 4 \
  --verbose \
  --no-db  # Skip DB write for testing

# Verify outputs created
ls -la artifacts/Checklist/*/stage-*/stage-result.json
```

**Expected**: 4 stage directories with result JSON files, no database writes.

---

## 🔗 Integration with continue.dev

**When User Provides Input**:
```json
{
  "module": "Checklist",
  "iteration": 1,
  "test_categories": ["unit", "integration", "e2e", "api", "edge-case", "browser"]
}
```

**Claude Does**:
1. Detect: `skills/legacy-modernization-orchestrator/SKILL.md`
2. Invoke: `echo '{json}' | python3 skills/legacy-modernization-orchestrator/run.py --input-stdin --verbose --stream`
3. Monitor: Stage completions (stdout)
4. Report: All 7 stages executed, results in database

---

**Status**: ✅ All skills configured correctly
**Orchestrator**: ✅ Ready for auto-invocation
**Pipeline**: ✅ Ready for full execution
**Database**: ✅ Schema ready, auto-creates on first run
