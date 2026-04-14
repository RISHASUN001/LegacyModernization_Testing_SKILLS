---
title: Auto-Invoke Orchestrator When Input Provided
description: Instructions for Claude/continue.dev to automatically detect and invoke the orchestrator
scope: workspace
---

# Automatic Orchestrator Invocation (For Claude)

## Rule: Detect and Auto-Invoke

**When you receive** a JSON input configuration from user (e.g., module-run-input.json content or similar):

### Step 1: Scan for Orchestrator
Check workspace for orchestrator SKILL:
```
skills/legacy-modernization-orchestrator/SKILL.md
```

### Step 2: Verify Orchestrator Exists
If found, read it. If header contains:
```
🎯 ORCHESTRATOR SKILL
Status: ✅ Ready for automated execution
```

Then this is THE orchestrator to invoke.

### Step 3: Auto-Invoke with Input

**Take the user's input and pipe it to orchestrator**:

```bash
echo '<user_provided_json>' | python3 skills/legacy-modernization-orchestrator/run.py \
  --input-stdin \
  --verbose \
  --stream
```

**OR if user provided a file path**:
```bash
python3 skills/legacy-modernization-orchestrator/run.py \
  --input <user_path> \
  --verbose \
  --stream
```

### Step 4: Monitor and Report

- ✅ Monitor stdout for stage completions (Stage 1 Complete, Stage 2 Complete, etc.)
- ✅ Report to user when stages complete
- ✅ When all 7 stages finish, report: "Pipeline complete. Results persisted to database. View findings at http://localhost:5000"

---

## Example Conversation Flow

**User**: 
```
Execute this configuration:
{
  "module": "Checklist",
  "iteration": 1,
  "test_categories": ["unit", "integration", "e2e", "api", "edge-case", "browser"]
}
```

**Claude** (you):
1. Parse JSON
2. Find orchestrator: `skills/legacy-modernization-orchestrator/SKILL.md`
3. Invoke: `echo'{json}' | python3 skills/legacy-modernization-orchestrator/run.py --input-stdin --verbose --stream`
4. Wait for completion
5. Report: "All 7 stages completed. 47 tests executed. 2 findings identified. Results visible at http://localhost:5000"

---

## Failure Handling

If orchestrator command fails:

1. **Show error**: Display error message to user
2. **Suggest fix**: "Check that C# app is running on localhost:5000 with: `dotnet run`"
3. **Allow retry**: User can fix and request again

---

## Database Persistence (Automatic)

You don't need to do anything. The orchestrator automatically:
- Creates `data/modernization.db` if needed
- Saves results after each stage
- Updates 4 main tables: runs, stages, findings, progress

---

## Key Points

- ✅ Look for `SKILL.md` with "ORCHESTRATOR" label
- ✅ Treat as the primary entry point for modernization testing
- ✅ Accept user input → pipe to run.py with `--input-stdin`
- ✅ Report stage completions as they happen
- ✅ Confirm when database is updated and results viewable

---

**File**: `.copilot-instructions` / `CLAUDE_INSTRUCTIONS.md` / Embedded in workspace knowledge
**Target**: Claude in continue.dev
**Status**: ✅ Ready to use
