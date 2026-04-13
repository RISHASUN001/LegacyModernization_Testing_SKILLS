# Workspace Cleanup & Verification Guide

## 📋 Files to Remove (Obsolete/Superseded)

### Documentation Files (Superseded by newer versions)

| File | Reason to Remove | Replacement |
|------|-----------------|-------------|
| `MODERNIZATION_PIPELINE_PROMPT.md` | Old approach (manual copy-paste into continue.dev) | Auto-orchestration via SKILL.md detection |
| `ORCHESTRATOR_GUIDE.md` | Superseded by newer version | Use `ORCHESTRATOR_GUIDE_NEW.md` |
| `START_HERE.md` | Superseded by newer version | Use `READY_TO_USE.md` |
| `TESTING_GUIDE.md` | Old testing guide (mock API based) | Use orchestrator pipeline instead |
| `TEST_EXECUTION_SUMMARY.md` | Old test results (not automated) | Results via orchestrator database |
| `USAGE_GUIDE.md` | Old generic guide | Use `READY_TO_USE.md` + `ORCHESTRATOR_GUIDE_NEW.md` |
| `QUICK_START.md` | Old quick start | Use `READY_TO_USE.md` (3 steps) |
| `COMPLETION_SUMMARY.md` | Old project summary | Use `READY_TO_USE.md` |

### Removal Command
```bash
cd /Users/risha/Documents/Buildathon

rm -f MODERNIZATION_PIPELINE_PROMPT.md \
      ORCHESTRATOR_GUIDE.md \
      START_HERE.md \
      TESTING_GUIDE.md \
      TEST_EXECUTION_SUMMARY.md \
      USAGE_GUIDE.md \
      QUICK_START.md \
      COMPLETION_SUMMARY.md
```

---

## ✅ Files to Keep (Active Use)

### Core Documentation (Current & Required)
- ✅ `README.md` - Project overview
- ✅ `READY_TO_USE.md` - **Quick reference (USE THIS)**
- ✅ `ORCHESTRATOR_GUIDE_NEW.md` - **Complete workflow**
- ✅ `.CLAUDE_AUTO_INVOKE.md` - Claude auto-invocation rules

### Configuration Files
- ✅ `global.json` - .NET SDK version
- ✅ `module-run-input.json` - Sample input config
- ✅ `LegacyModernization.slnx` - Solution file

### Application Files
- ✅ `test-login.html` - Test login page (used by browser testing)

### Legacy Reference (Documentation Only)
- ✅ `samples/legacy-java-app/` - Reference code for comparison

---

## 🔍 Skills Verification Checklist

### 13 Main Skills (All Present ✅)

| # | Skill Directory | SKILL.md | config.json | run.py/run.ps1 | Status |
|---|---|---|---|---|---|
| 1 | module-discovery | ✅ | ✅ | ✅ | Verify paths |
| 2 | legacy-logic-extraction | ✅ | ✅ | ✅ | Verify paths |
| 3 | module-documentation | ✅ | ✅ | ✅ | Verify paths |
| 4 | clean-architecture-assessment | ✅ | ✅ | ✅ | Verify paths |
| 5 | test-plan-generation | ✅ | ✅ | ✅ | Verify paths |
| 6 | unit-test-execution | ✅ | ✅ | ✅ | Verify paths |
| 7 | integration-test-execution | ✅ | ✅ | ✅ | Verify paths |
| 8 | e2e-test-execution | ✅ | ✅ | ✅ | Verify paths |
| 9 | api-test-execution | ✅ | ✅ | ✅ | Verify paths |
| 10 | edge-case-testing | ✅ | ✅ | ✅ | Verify paths |
| 11 | browser-testing-with-devtools | ✅ | ✅ | ✅ | Verify paths |
| 12 | failure-diagnosis | ✅ | ✅ | ✅ | Verify paths |
| 13 | lessons-learned | ✅ | ✅ | ✅ | Verify paths |

### 2 Comparison/Analysis Skills

| # | Skill Directory | SKILL.md | config.json | run.py/run.ps1 | Status |
|---|---|---|---|---|---|
| 14 | parity-verification | ✅ | ✅ | ✅ | Verify paths |
| 15 | iteration-comparison | ✅ | ✅ | ✅ | Verify paths |

### 1 Orchestrator (NEW)

| # | Skill Directory | SKILL.md | config.json | run.py | Status |
|---|---|---|---|---|---|
| 16 | legacy-modernization-orchestrator | ✅ | ✅ | ✅ | **Primary** |

---

## 🛠 Setup Verification Script

```bash
#!/bin/bash
# Verify all skills have correct structure

cd /Users/risha/Documents/Buildathon

echo "🔍 Verifying Skill Structure..."

SKILLS=(
    "module-discovery"
    "legacy-logic-extraction"
    "module-documentation"
    "clean-architecture-assessment"
    "test-plan-generation"
    "unit-test-execution"
    "integration-test-execution"
    "e2e-test-execution"
    "api-test-execution"
    "edge-case-testing"
    "browser-testing-with-devtools"
    "failure-diagnosis"
    "lessons-learned"
    "parity-verification"
    "iteration-comparison"
    "legacy-modernization-orchestrator"
)

for skill in "${SKILLS[@]}"; do
    skill_dir="skills/$skill"
    
    echo -n "  $skill: "
    
    if [ ! -f "$skill_dir/SKILL.md" ]; then
        echo "❌ Missing SKILL.md"
        continue
    fi
    
    if [ ! -f "$skill_dir/config.json" ]; then
        echo "❌ Missing config.json"
        continue
    fi
    
    if [ ! -f "$skill_dir/run.py" ] && [ ! -f "$skill_dir/run.ps1" ]; then
        echo "❌ Missing run.py or run.ps1"
        continue
    fi
    
    echo "✅"
done

echo ""
echo "🔍 Checking Orchestrator..."
if [ -f "skills/legacy-modernization-orchestrator/run.py" ]; then
    echo "  ✅ Orchestrator run.py exists"
    echo "  ✅ Supports --input-stdin: $(grep -q 'input-stdin' skills/legacy-modernization-orchestrator/run.py && echo 'YES' || echo 'NO')"
fi

echo ""
echo "🔍 Checking Database..."
if [ -d "data" ]; then
    echo "  ✅ data/ directory exists"
else
    echo "  ❌ data/ directory missing (will be created on first run)"
fi

echo ""
echo "✅ Verification Complete"
```

---

## 📝 Complete Setup & Run Instructions

### Phase 1: Cleanup (Remove Obsolete Files)

```bash
cd /Users/risha/Documents/Buildathon

# Remove superseded documentation
rm -f MODERNIZATION_PIPELINE_PROMPT.md \
      ORCHESTRATOR_GUIDE.md \
      START_HERE.md \
      TESTING_GUIDE.md \
      TEST_EXECUTION_SUMMARY.md \
      USAGE_GUIDE.md \
      QUICK_START.md \
      COMPLETION_SUMMARY.md

echo "✅ Cleanup complete"
```

### Phase 2: Verify Setup

```bash
# Build C# application
dotnet build src/LegacyModernization.Dashboard.Web/LegacyModernization.Dashboard.Web.csproj

# Verify all skills exist
ls -1d skills/*/SKILL.md | wc -l  # Should show 16
```

### Phase 3: Start C# Application

**Terminal 1**:
```bash
cd /Users/risha/Documents/Buildathon/src/LegacyModernization.Dashboard.Web
dotnet run
```

**Expected Output**:
```
info: LegacyModernization.Infrastructure.Services.MetadataSyncService[0]
      Metadata sync completed. Runs=X, Skills=30+
info: Microsoft.Hosting.Lifetime[14]
      Now listening on: http://localhost:5000
```

### Phase 4: Access Dashboard

**Browser**: Open `http://localhost:5000`

**Verify**:
- ✅ Dashboard loads
- ✅ "Modernization" tab visible
- ✅ "Input Builder" section accessible

### Phase 5: Generate Input (Dashboard)

**In Browser** → `http://localhost:5000`:

1. Click **"Input Builder"**
2. Select **Module**: "Checklist"
3. Check test categories:
   - ☑ Unit Tests
   - ☑ Integration Tests
   - ☑ E2E Tests
   - ☑ API Tests
   - ☑ Edge Case Testing
   - ☑ Browser Testing
4. Click **"Generate Input JSON"**
5. **Copy** the JSON output

### Phase 6: Execute Pipeline (continue.dev)

**In continue.dev/Claude**:

1. Paste JSON: `"module": "Checklist",...`
2. Request:
```
Execute the modernization pipeline with this configuration:
{paste_json}
```

**Claude will**:
- ✅ Auto-detect orchestrator (`skills/legacy-modernization-orchestrator/SKILL.md`)
- ✅ Auto-invoke: `echo '{json}' | python3 skills/legacy-modernization-orchestrator/run.py --input-stdin --verbose --stream`
- ✅ Cascade through 7 stages
- ✅ Auto-persist to database
- ✅ Report when complete

### Phase 7: View Results

**Dashboard** automatically updates:
- Pipeline Status (Stages 1-7)
- Test Results (47 tests breakdown)
- Findings (2-8 issues identified)
- Progress Chart (improvement trend)
- Recommendations (actionable next steps)

---

## ⚙️ Skill Path Verification

Each skill's SKILL.md must reference correct paths for run.py execution.

### Template (All Skills Use This Pattern)

**SKILL.md**:
```markdown
## Usage

```bash
python3 skills/{skill-name}/run.py \
  --input {config_file} \
  --module {module} \
  --output-dir {output_dir}
```
```

### Verify All Skills Have Correct Paths

```bash
# Check each skill's run.py is executable and has correct shebang
for skill in skills/*/run.py; do
    echo "Checking: $skill"
    head -1 "$skill"  # Should be: #!/usr/bin/env python3
    ls -la "$skill"   # Should have x permission
done
```

---

## 🧪 Full Pipeline Test (Verify Everything Works)

### Dry Run (No External Dependencies)

```bash
cd /Users/risha/Documents/Buildathon

# Test orchestrator with dry-run
python3 skills/legacy-modernization-orchestrator/run.py \
  --input run-inputs/module-run-input.browser-test.json \
  --stages 1 2 3 4 \
  --verbose

# Verify outputs
ls -la artifacts/Checklist/run-*/stage-*/stage-result.json
sqlite3 data/modernization.db "SELECT COUNT(*) FROM orchestration_stages;"
```

### Expected Output

```
====================================================================
STAGE 1: Discovery
====================================================================
✓ STAGE 1 COMPLETED in 62.1s

====================================================================
STAGE 2: Logic Understanding
====================================================================
✓ STAGE 2 COMPLETED in 118.5s

====================================================================
STAGE 3: Architecture Review
====================================================================
✓ STAGE 3 COMPLETED in 89.2s

====================================================================
STAGE 4: Test Plan
====================================================================
✓ STAGE 4 COMPLETED in 60.8s

====================================================================
ORCHESTRATION COMPLETE
====================================================================
Total Duration: 330.6s
Stages Completed: 4/7
Stages Failed: 0
✅ PIPELINE EXECUTION SUCCESSFUL
```

---

## 📊 Database Verification

After running orchestrator, verify database is populated:

```bash
# Check database exists
ls -lh data/modernization.db

# Check tables are populated
sqlite3 data/modernization.db << EOF
SELECT 'orchestration_runs:' as table_name, COUNT(*) as row_count FROM orchestration_runs
UNION ALL
SELECT 'orchestration_stages' as table_name, COUNT(*) as row_count FROM orchestration_stages
UNION ALL
SELECT 'orchestration_findings' as table_name, COUNT(*) as row_count FROM orchestration_findings
UNION ALL
SELECT 'modernization_progress' as table_name, COUNT(*) as row_count FROM modernization_progress;
EOF
```

**Expected Output**:
```
table_name|row_count
orchestration_runs|1
orchestration_stages|7
orchestration_findings|3-8
modernization_progress|1
```

---

## ✅ Checklist Before Running

- [ ] Removed 8 obsolete documentation files
- [ ] Verified all 16 skills have SKILL.md, config.json, run script
- [ ] Built C# application: `dotnet build` ✅
- [ ] Started Dashboard on localhost:5000
- [ ] Dashboard loads and shows "Modernization" tab
- [ ] Input Builder accessible and working
- [ ] Generated JSON from Input Builder
- [ ] continue.dev ready to receive input
- [ ] Claude can access workspace files
- [ ] All skill scripts are executable (`chmod +x`)
- [ ] Database directory exists or will be created
- [ ] Legacy reference app present: `samples/legacy-java-app/`

---

## 🚀 Quick Command Summary

```bash
# 1. Cleanup
rm -f MODERNIZATION_PIPELINE_PROMPT.md ORCHESTRATOR_GUIDE.md START_HERE.md TESTING_GUIDE.md TEST_EXECUTION_SUMMARY.md USAGE_GUIDE.md QUICK_START.md COMPLETION_SUMMARY.md

# 2. Build
dotnet build src/LegacyModernization.Dashboard.Web/LegacyModernization.Dashboard.Web.csproj

# 3. Run Dashboard
cd src/LegacyModernization.Dashboard.Web && dotnet run

# 4. In another terminal - Test orchestrator
cd /Users/risha/Documents/Buildathon
python3 skills/legacy-modernization-orchestrator/run.py \
  --input run-inputs/module-run-input.browser-test.json \
  --verbose

# 5. View results
curl http://localhost:5000/api/modernization/findings
```

---

## Next Steps

1. ✅ Run cleanup commands above
2. ✅ Verify skill structure with provided script
3. ✅ Start C# app and test orchestrator
4. ✅ Generate input from dashboard
5. ✅ Execute pipeline via continue.dev
6. ✅ View results on dashboard

---

**Status**: Ready for cleanup and full pipeline test
**Last Updated**: April 2026
**Total Skills**: 16 (13 main + 2 comparison + 1 orchestrator)
