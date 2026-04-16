# MATE Skill Invocation Pipeline

## Overview

This guide explains how data flows from the **run input builder** through the **orchestrator** to individual **skills**, and how to verify the pipeline works correctly.

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Input Builder (Dashboard UI)                                │
│    User fills form: moduleName, workflowNames[], baseUrl, etc. │
└────────────────────┬────────────────────────────────────────────┘
                     │ POST /pipeline/input
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Dashboard Controller (PipelineController.cs)                │
│    - Save run input to .json file (run-inputs/)               │
│    - Generate unique runId (e.g. run-20260416-143022)         │
│    - Invoke orchestrator in background                         │
└────────────────────┬────────────────────────────────────────────┘
                     │ subprocess: python3 orchestrator/run.py
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Orchestrator (orchestrator/run.py)                          │
│    - Load run input .json                                       │
│    - Load orchestrator config (stage order, skill contracts)   │
│    - Create orchestration-summary.json                          │
│    - For each stage, for each skill:                           │
│      - Invoke: python3 skill/run.py --input <path> --artifacts-root artifacts
│      - Collect result.json from skill                          │
└────────────────────┬────────────────────────────────────────────┘
                     │ For each skill in stage_order
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Skill (e.g. csharp-module-discovery/run.py)                │
│    - Load run input .json via --input                          │
│    - Extract moduleName, convertedRoots[], workflowNames[]    │
│    - Perform skill-specific logic                              │
│    - Write result.json (status, summary, artifacts, metrics)  │
│    - Write actual artifacts (discovery maps, etc)              │
│    - Exit with code 0 (success) or 1 (failure)               │
└────────────────────┬────────────────────────────────────────────┘
                     │ Artifacts populate artifacts/{moduleName}/{runId}/{skillName}/
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Dashboard UI (Run Details Page)                             │
│    - Read artifacts/{moduleName}/{runId}/orchestration-summary │
│    - Display stages, skills, results, artifacts                │
│    - User can inspect generated artifacts                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Required Inputs

All skills receive the same run input JSON. The orchestrator requires these fields:

### Core Inputs (Required)
```json
{
  "moduleName": "Checklist",
  "workflowNames": ["Create", "Edit"],
  "convertedRoots": ["/path/to/LegacyModernization.Application"],
  "legacyBackendRoots": ["/path/to/legacy-app/src"],
  "legacyFrontendRoots": ["/path/to/legacy-app/web"],
  "baseUrl": "http://localhost:5029",
  "startUrl": "/pipeline",
  "dotnetTestTarget": "/path/to/LegacyModernization.Tests.csproj"
}
```

### Optional Inputs
```json
{
  "controllerHints": ["ChecklistController"],
  "viewHints": ["Index", "Create", "Edit"],
  "keywords": ["checklist", "item"],
  "expectedEndUrls": ["/checklist/list"],
  "strictModuleOnly": false,
  "strictAIGeneration": false,
  "enableUserInputPrompting": true
}
```

---

## Skill Execution Contract

### Skill Input (Via Command Line)
Every skill is invoked with:
```bash
python3 skill/run.py --input <path/to/run-input.json> --artifacts-root <path/to/artifacts>
```

### Skill Output (result.json)
Every skill MUST write a result.json to its output directory:
```
artifacts/{moduleName}/{runId}/{skillName}/result.json
```

Expected schema:
```json
{
  "skillName": "csharp-module-discovery",
  "status": "passed|failed",
  "startedAt": "2026-04-16T14:30:00Z",
  "endedAt": "2026-04-16T14:30:05Z",
  "summary": "Human-readable summary of what was done",
  "metrics": {
    "candidateFiles": 41,
    "includedFiles": 20,
    "controllers": 2
  },
  "artifacts": [
    "csharp-module-map.json",
    "controller-route-map.json"
  ],
  "findings": [
    {
      "type": "RouteMissing",
      "message": "Controller action not found in routes",
      "severity": "warning"
    }
  ]
}
```

### Skill Artifact Paths
Artifacts are declared relative to the skill directory:
```
artifacts/Checklist/run-20260416-143022/csharp-module-discovery/csharp-module-map.json
```

---

## Stage Sequence (10 Stages)

1. **csharp-module-discovery**: Scopes C# module, discovers controllers, routes, services, SQL, tables
2. **csharp-logic-understanding**: AI explains C# workflow branches, validations, DB touchpoints
3. **legacy-module-discovery**: Anchors legacy Java files to C# evidence
4. **legacy-logic-understanding**: AI explains expected legacy behavior
5. **diagram-generation**: Generates Mermaid + Excalidraw workflow diagrams
6. **parity-analysis**: Compares legacy vs. converted logic, flags behavior drift
7. **ai-test-generation**: AI generates unit, integration, edge-case, and playwright tests
8. **test-execution**: Runs unit, integration, edge, and playwright tests (pytest + dotnet)
9. **clean-architecture-assessment**: Validates architecture goals and constraints
10. **vanity-check**: Final pipeline sanity checks

---

## Testing the Pipeline

### Step 1: Use the Input Builder
1. Open `http://127.0.0.1:5029/pipeline/input`
2. Fill in form:
   - **moduleName**: "Checklist"
   - **workflowNames[]**: "Create, Edit"
   - **convertedRoots[]**: Absolute path to LegacyModernization.Application
   - **legacyBackendRoots[]**: Absolute path to legacy-java-app/src (can be empty if no legacy)
   - **legacyFrontendRoots[]**: Absolute path to legacy-java-app/web (can be empty if no legacy)
   - **baseUrl**: "http://localhost:5029"
   - **startUrl**: "/pipeline"
   - **dotnetTestTarget**: Absolute path to .sln or .csproj
3. Click **Save Run Input**

### Step 2: Wait for Orchestrator
- Dashboard redirects to run details page: `http://127.0.0.1:5029/pipeline/run/Checklist/run-20260416-143022`
- Orchestrator runs in background; skills execute one per stage
- Artifacts populate in `artifacts/Checklist/run-20260416-143022/{skillName}/`

### Step 3: Monitor Progress
- **Dashboard displays:**
  - Stages and their status (passed, failed, pending)
  - Skills per stage with return codes, metrics, artifacts
  - Side-by-side layout: skills on left, artifacts on right
- **Artifacts available for download** via `/pipeline/artifact/{moduleName}/{runId}?path=...`

### Step 4: Inspect Generated Tests
Navigate to skill directories:
```
artifacts/Checklist/run-20260416-143022/unit-test-generation/
artifacts/Checklist/run-20260416-143022/playwright-test-generation/
artifacts/Checklist/run-20260416-143022/integration-test-generation/
```

Each contains generated test code (Python .py files).

---

## Troubleshooting

### Skill Fails With Input Validation Error
- Verify all required fields are set in run input
- Check orchestrator-summary.json → stages → skills → findings for details

### Artifact Paths Show as "missing"
- Verify skill wrote artifacts to the correct path
- Check skill's result.json → artifacts array for declared paths
- Verify file exists at `artifacts/{moduleName}/{runId}/{skillName}/{artifactName}`

### Orchestrator Hangs
- Check if a skill is blocked waiting for user input
- Set `enableUserInputPrompting: false` in optional inputs
- Monitor subprocess stderr for errors

### Generated Tests Are Empty
- Verify AI provider is available (see strictAIGeneration flag)
- Check parity-analysis and csharp-logic-understanding passed
- Playwright tests need baseUrl and startUrl to be valid

---

## Key Design Principles

1. **Pure JSON Communication**: All data flows via JSON input files and result.json outputs
2. **Declarative Contracts**: Each skill declares inputs, outputs, and dependencies in config.json
3. **Evidence-Driven**: Each stage produces artifacts that feed into the next stage
4. **Checkpointing**: Orchestrator-summary.json persists full run state for reruns and dashboarding
5. **Skill Isolation**: Skills are independent Python processes; failures don't cascade
6. **Artifact Normalization**: Dashboard resolves artifacts from various formats to run-relative paths

---

## For Skill Developers

### Skill Template (Python)
```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser(description="my-skill")
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    # Load run input
    payload = json.loads(Path(args.input).read_text())
    module_name = payload.get("moduleName")
    run_id = payload.get("runId")

    # Output directory
    out_dir = Path(args.artifacts_root) / module_name / run_id / "my-skill"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Perform work...

    # Write result.json
    result = {
        "skillName": "my-skill",
        "status": "passed",
        "summary": "Work completed",
        "artifacts": [
            str(out_dir / "output.json")
        ],
        "metrics": {"itemsProcessed": 42}
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    (out_dir / "output.json").write_text(json.dumps({"data": "..."}))

    print((out_dir / "result.json").as_posix())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Running Orchestrator Manually

```bash
cd /Users/risha/Documents/Buildathon

python3 skills/orchestrator/run.py \
  --input run-inputs/run-input.Checklist.TIMESTAMP.json \
  --artifacts-root artifacts \
  --skills-root skills \
  --rerun-mode changed
```

Output: orchestration-summary.json in artifacts/Checklist/{runId}/

---

That's the complete pipeline! Use this guide to verify data flows correctly end-to-end.
