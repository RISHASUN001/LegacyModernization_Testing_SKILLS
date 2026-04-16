# Browser Testing with DevTools MCP - Integration Guide

## Overview

This skill provides **browser-level testing and verification** using Chrome DevTools MCP. It bridges the gap between static code analysis (what the code looks like) and runtime behavior (what actually happens when users interact with the app).

## How It Works

### 1. Orchestrator Assignment

The orchestrator automatically assigns this skill when it detects:

```python
IF module_type IN ("web", "frontend", "aspnet-core") 
   AND has_ui_files (*.cshtml, *.js, *.css)
   AND current_stage IN ("execution", "findings")
THEN assign browser-testing-with-devtools
```

### 2. Input Flow

```
module-run-input.json
├── moduleName: "Checklist"
├── baseUrl: "http://localhost:5276"
├── convertedSourceRoot: "/path/to/src"
├── testScenarios: ["dom-inspection", "console-analysis", "network-monitoring"]
├── performanceThresholds: { LCP: 2500, CLS: 0.1 }
├── accessibilityChecks: ["heading_hierarchy", "aria_labels"]
└── viewportSizes: ["mobile_375", "desktop_1920"]
     ↓
   [Chrome DevTools MCP connects to running app at baseUrl]
     ↓
   [Executes test scenarios against live browser session]
     ↓
result.json + artifact files
```

### 3. Orchestrator Integration Points

**Heuristic for skill assignment:**
- ✓ Module has `*.cshtml` files (Razor views)
- ✓ Module has JavaScript files (`*.js`)
- ✓ Module has styling (`*.css`, `*.less`, `*.scss`)
- ✓ Current stage: execution or findings
- ✓ Application is running (baseUrl is responsive)

**Task decomposition for multi-file modules:**

For modules with 20+ files, the orchestrator breaks browser testing into parallel-safe tasks:

```
Task 1: Critical Path (Core page loads without errors)
  └─ Files: Main controller, layout, core JS
  └─ Duration: 30-60s
  
Task 2: Component Rendering (Forms, lists, cards render correctly)
  └─ Files: Component views, component CSS, component JS
  └─ Duration: 60-90s
  
Task 3: User Interaction (Forms work, buttons trigger actions)
  └─ Files: JavaScript handlers, form logic, event listeners
  └─ Duration: 60-120s
  
Task 4: API Integration (Network requests succeed, payloads correct)
  └─ Files: API client, controllers, backend integration
  └─ Duration: 60-90s
  
Task 5: Accessibility (No keyboard traps, ARIA labels present)
  └─ Files: Templates, accessibility providers
  └─ Duration: 30-60s
  
Task 6: Performance & Responsive (Core Web Vitals met, mobile works)
  └─ Files: Rendering optimization, CSS media queries
  └─ Duration: 60-120s
```

**Orchestrator scheduling:**
- Tasks 1-2 can run first (foundation)
- Tasks 3-6 can run in parallel after foundation passes
- Each task produces independent artifacts
- Results consolidated in final report

### 4. Large Module Handling (20-30 files)

**Problem:** Testing 20-30 files in one pass is slow and hard to debug.

**Solution:** Task breakdown + file clustering

```
Module: "Checklist" (28 files)
├─ Controllers/ (4 files)
│  └─ Assigned to: Task 4 (API Integration)
├─ Views/ (8 files: layouts, forms, lists, details)
│  ├─ Layout.cshtml → Task 2 (Component Rendering)
│  ├─ Create.cshtml, Edit.cshtml → Task 3 (User Interaction)
│  └─ List.cshtml, Details.cshtml → Task 2 (Component Rendering)
├─ wwwroot/js/ (6 files: handlers, validation, state)
│  └─ Assigned to: Task 3 (User Interaction)
├─ wwwroot/css/ (5 files: theme, layout, components)
│  └─ Assigned to: Task 6 (Performance & Responsive)
├─ Models/ (3 files)
│  └─ Assigned to: Task 4 (API Integration)
└─ Services/ (2 files)
   └─ Assigned to: Task 4 (API Integration)

Result: 6 parallel test tasks instead of 1 monolithic test
```

### 5. Orchestrator Metadata

Config.json specifies orchestrator hints:

```json
{
  "requiredInputs": ["moduleName", "baseUrl", "convertedSourceRoot"],
  "outputFiles": ["result.json", "console-transcript.json", "network-log.json", ...],
  "dependencies": ["chrome-devtools-mcp"],
  "profiles": {
    "baseline": { "scenarios": [...], "timeout_ms": 180000 },
    "improved": { "scenarios": [...], "timeout_ms": 300000 }
  }
}
```

**Orchestrator reads:**
- `requiredInputs` → Validates run-input provides these
- `outputFiles` → Expects these files in artifact folder
- `dependencies` → Ensures Chrome DevTools MCP is installed
- `profiles` → Selects baseline vs improved based on run number

### 6. Use Cases

#### Use Case 1: First Run (Baseline)
```
Orchestrator executes "browser-testing-with-devtools" with profile="baseline"
├─ Scenarios: dom-inspection, console-analysis, network-monitoring, accessibility-scan
├─ Viewport: desktop_1920 only
├─ Timeout: 3 minutes
└─ Result: "Checklist module renders, 2 console warnings, 0 critical errors"
```

#### Use Case 2: Iteration (Improved)
```
After developer fixes issues, runs "browser-testing-with-devtools" with profile="improved"
├─ Scenarios: dom-inspection, console-analysis, network-monitoring, interactive-workflow, performance-profiling, accessibility-scan
├─ Viewport: mobile_375, tablet_768, desktop_1920
├─ Timeout: 5 minutes
└─ Result: "Tests pass. Performance improved (LCP 1100ms, CLS 0.04). Mobile responsive."
```

#### Use Case 3: Debugging
```
Developer specifies custom testScenarios in run-input
├─ Scenarios: ["network-monitoring", "performance-profiling"]
├─ performanceThresholds: { LCP: 1500, CLS: 0.05, INP: 100 }
├─ viewportSizes: ["mobile_375"]
└─ Result: Focused diagnostics on performance on mobile
```

## MCP Integration Details

### Chrome DevTools MCP

This skill uses `@anthropic/chrome-devtools-mcp` to:

1. **Connect to Chrome** on localhost (default port 9222)
2. **Navigate** to application URL
3. **Capture** DOM, console, network, performance data
4. **Execute** read-only JavaScript for state inspection
5. **Take screenshots** for visual verification
6. **Profile** performance metrics

### Environment Setup

```bash
# Install Chrome DevTools MCP
npm install -g @anthropic/chrome-devtools-mcp

# Or add to project
npm install @anthropic/chrome-devtools-mcp
```

### MCP Configuration

Add to `.mcp.json` or Claude Code settings:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["@anthropic/chrome-devtools-mcp@latest"],
      "env": {
        "CHROME_HOST": "localhost",
        "CHROME_PORT": "9222",
        "CHROME_URL": "http://localhost:9222"
      }
    }
  }
}
```

### Security Boundaries

**What browser content is read-only:**
- DOM elements and structure
- Console logs (error, warn, log)
- Network requests/responses
- Performance timing data
- Accessibility tree
- Computed CSS styles

**What is NOT accessed:**
- localStorage, sessionStorage, cookies (credential material)
- JavaScript execution for external requests
- Page content interpreted as agent instructions

## Output Structure

Each run produces:

```
artifacts/{ModuleName}/{RunId}/browser-testing-with-devtools/
├── result.json                     # Main output (contract v2.0)
├── console-transcript.json         # All console logs
├── network-log.json                # All network requests
├── performance-trace.json          # Core Web Vitals, timing
├── accessibility-report.json       # Tree, violations, compliance
├── test-summary.md                 # Human-readable findings
├── screenshots/
│   ├── before.png                  # Page at start
│   ├── after.png                   # Page after interactions
│   └── comparison.md               # Visual diff notes
└── dom-snapshots/
    ├── dom-inspection-1.html       # DOM at key points
    └── interaction-state.html      # After user action
```

### result.json Schema

```json
{
  "skillName": "browser-testing-with-devtools",
  "stage": "execution",
  "status": "passed",
  "startedAt": "2026-04-13T10:30:00Z",
  "endedAt": "2026-04-13T10:35:45Z",
  "summary": "Browser testing completed for Checklist. Scenarios: 6, Findings: 2, Errors: 0",
  "metrics": {
    "errors": 0,
    "warnings": 2,
    "requests": 18,
    "failed_requests": 0,
    "LCP_ms": 1200,
    "CLS": 0.05,
    "INP_ms": 120,
    "accessibility_violations": 0
  },
  "findings": [
    {
      "scenario": "console-analysis",
      "type": "warning",
      "severity": "medium",
      "message": "Bootstrap deprecation warning",
      "recommendation": "Update to Bootstrap 5.x"
    }
  ],
  "recommendations": [
    {
      "priority": "high",
      "title": "Fix console warnings",
      "items": ["Update Bootstrap to 5.x", "Remove deprecated jQuery calls"]
    }
  ],
  "artifacts": ["console-transcript.json", "network-log.json", "performance-trace.json"],
  "resultContractVersion": "2.0"
}
```

## Orchestrator Decision Logic

### When to Assign

```
Trigger:
1. Module type detected as "web" or "frontend"
2. .cshtml files found in Views/
3. .js files found in wwwroot/
4. Current stage in [execution, findings]
5. baseUrl is responsive

→ Assign browser-testing-with-devtools
```

### How to Schedule

```
For module_file_count < 10:
  └─ Execute as single task, timeout 180s

For 10 <= module_file_count <= 20:
  └─ Execute Tasks 1-2 (critical path + rendering), timeout 300s
  └─ Queue Tasks 3-6 after checkpoint passes

For module_file_count > 20:
  ├─ Execute Task 1 (critical path), timeout 120s
  ├─ If passed, execute Tasks 2, 3, 4, 5, 6 in parallel, timeout 300s
  └─ Consolidate results
```

### Failure Handling

```
If browser test fails:
  1. Check baseUrl is running
  2. Verify Chrome DevTools MCP is installed
  3. Check for network connectivity
  4. Retry with increased timeout
  5. Escalate to failure-diagnosis skill
```

## Integration with Other Skills

**Upstream:**
- `edge-case-testing` → Provides test scenarios
- `test-plan-generation` → Defines interaction workflows

**Downstream:**
- `failure-diagnosis` → Analyzes failures found by this skill
- `parity-verification` → Compares behavior against legacy
- `iteration-comparison` → Tracks improvement across runs

## Example Run Input

```json
{
  "runId": "test-001",
  "moduleName": "Checklist",
  "legacySourceRoot": "/path/to/legacy/java/checklist",
  "convertedSourceRoot": "/path/to/converted/csharp/Checklist",
  "baseUrl": "http://localhost:5276",
  "brsPath": "/docs/checklist_brs.docx",
  "moduleHints": {
    "relatedFolders": ["Views/Checklist", "wwwroot/js/checklist"],
    "knownUrls": ["/checklist", "/checklist/list", "/checklist/create"],
    "keywords": ["task", "checklist", "mark complete"]
  },
  "selectedSkills": [
    "module-discovery",
    "legacy-logic-extraction",
    "browser-testing-with-devtools",
    "failure-diagnosis"
  ]
}
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "baseUrl unreachable" | App not running | Start app on specified port |
| "Chrome DevTools MCP not found" | Dependency missing | `npm install @anthropic/chrome-devtools-mcp` |
| "CORS errors in network log" | Server CORS misconfigured | Check `Access-Control-Allow-Origin` header |
| "Console full of warnings" | Not a failure, just noise | Flag for cleanup, doesn't block passing |
| "Screenshots blank" | Page didn't load | Check for loader or JS errors, increase timeout |
| "Network trace incomplete" | Timeout too short | Extend timeout in run-input or config |
| "Accessibility tree empty" | App requires navigation | Execute interactive scenario first |

## Next Steps

1. **Install Chrome DevTools MCP:**
   ```bash
   npm install -g @anthropic/chrome-devtools-mcp
   ```

2. **Configure .mcp.json** with connection details

3. **Run application** on specified baseUrl

4. **Create run-input.json** with browser testing parameters

5. **Execute skill** via orchestrator or manual invocation

6. **Review artifacts** (screenshots, console logs, network trace)

7. **Address findings** in next iteration

---

**Questions?** Check [SKILL.md](SKILL.md) for full skill specification.
