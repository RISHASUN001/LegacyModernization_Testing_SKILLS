# Orchestrator Integration: Large Module Handling

## How the Orchestrator Routes Browser Testing

### Detection Phase

```python
def should_assign_browser_testing(module_metadata):
    """Orchestrator decides if browser-testing-with-devtools is needed."""
    
    triggers = [
        module_metadata.has_ui_files(),          # *.cshtml, *.js, *.css
        module_metadata["type"] in ["web", "frontend", "aspnet-core"],
        current_stage in ["execution", "findings"],
        application_is_running(module_metadata["baseUrl"])
    ]
    
    return all(triggers)

# Example: Checklist module has 28 files, detected as web-tier
# → Orchestrator assigns browser-testing-with-devtools
```

### Assignment Strategy

**For small modules (1-10 files):**
```
Assign → Execute single browser-testing task
         └─ All scenarios in one batch (180s timeout)
         └─ Desktop viewport only
         └─ Result: pass/fail
```

**For medium modules (10-20 files):**
```
Assign → Execute critical path (Task 1)
         └─ Timeout: 120s
         └─ If PASSES → Queue rendering + interaction (Tasks 2-3)
         └─ If FAILS → Escalate to failure-diagnosis
```

**For large modules (20-30 files):**
```
Assign → Execute foundation tasks first (Tasks 1-2)
         ├─ Task 1: Critical path (30-60s)
         ├─ Task 2: Rendering (60-90s)
         ├─ Checkpoint: Both must pass
         │
         └─ If checkpoint passes → Execute performance tasks in parallel
            ├─ Task 3: Interaction (60-120s)
            ├─ Task 4: Network (60-90s)
            ├─ Task 5: Accessibility (30-60s)
            ├─ Task 6: Performance (60-120s)
            └─ Consolidate results (30s)
                └─ Total: ~6-7 minutes for full suite
```

### File Mapping Example: Checklist Module (28 files)

Orchestrator performs static analysis to map files to test tasks:

```
Controllers/ (4 files)
├─ ChecklistController.cs         → Task 4 (API Integration)
├─ TaskController.cs              → Task 4 (API Integration)
├─ DashboardController.cs         → Task 2 (Component Rendering)
└─ ApiController.cs               → Task 4 (API Integration)

Models/ (3 files)
├─ ChecklistItem.cs               → Task 4 (API Integration)
├─ FilterCriteria.cs              → Task 4 (API Integration)
└─ PaginationModel.cs             → Task 4 (API Integration)

Views/ (8 files)
├─ Shared/Layout.cshtml           → Task 2 (Component Rendering)
├─ Checklist/Index.cshtml         → Task 2 (Component Rendering)
├─ Checklist/Create.cshtml        → Task 3 (User Interaction)
├─ Checklist/Edit.cshtml          → Task 3 (User Interaction)
├─ Checklist/Details.cshtml       → Task 2 (Component Rendering)
├─ Checklist/List.cshtml          → Task 2 (Component Rendering)
├─ Shared/_Nav.cshtml             → Task 2 (Component Rendering)
└─ Shared/_Footer.cshtml          → Task 2 (Component Rendering)

wwwroot/js/ (6 files)
├─ checklist.js                   → Task 3 (User Interaction)
├─ form-validation.js             → Task 3 (User Interaction)
├─ ajax-handlers.js               → Task 3 (User Interaction)
├─ state-management.js            → Task 3 (User Interaction)
├─ theme.js                       → Task 6 (Performance & Responsive)
└─ analytics.js                   → Task 4 (API Integration)

wwwroot/css/ (5 files)
├─ bootstrap-theme.css            → Task 6 (Performance & Responsive)
├─ layout.css                     → Task 6 (Performance & Responsive)
├─ components.css                 → Task 2 (Component Rendering)
├─ responsive.css                 → Task 6 (Performance & Responsive)
└─ utilities.css                  → Task 2 (Component Rendering)

Services/ (2 files)
├─ ChecklistService.cs            → Task 4 (API Integration)
└─ NotificationService.cs         → Task 4 (API Integration)
```

### Task Decomposition Output

Orchestrator creates task breakdown and assigns to browser-testing-with-devtools:

```
Task 1: Critical Path Validation
├─ All components must load
├─ Files affected: Layout.cshtml, DashboardController.cs, theme.js
├─ Scenario: Load application, check console for errors
├─ Timeout: 30-60s
└─ Acceptance: No critical errors, page responsive

Task 2: Component Rendering (parallel-safe, depends on Task 1)
├─ All UI components render correctly
├─ Files affected: 8 .cshtml files, components.css, utilities.css
├─ Scenarios: DOM inspection, screenshot validation
├─ Timeout: 60-90s
└─ Acceptance: All components visible, layout correct

Task 3: User Interaction (parallel-safe, depends on Task 1)
├─ Forms and buttons work, state updates
├─ Files affected: 4 .cshtml, 4 .js, ChecklistController.cs
├─ Scenarios: Form fill, button click, validation
├─ Timeout: 60-120s
└─ Acceptance: No console errors, DOM updates, no duplicates

Task 4: API Integration (parallel-safe, depends on Task 1)
├─ Network requests succeed, payloads correct
├─ Files affected: Controllers, Services, Models, ajax-handlers.js
├─ Scenarios: Network monitoring, request/response validation
├─ Timeout: 60-90s
└─ Acceptance: All GET/POST succeed, status 200-299

Task 5: Accessibility (parallel-safe, depends on Task 1)
├─ Keyboard navigation, ARIA labels, heading hierarchy
├─ Files affected: All .cshtml, form-validation.js
├─ Scenarios: Accessibility tree scan, keyboard test
├─ Timeout: 30-60s
└─ Acceptance: No violations, heading hierarchy valid

Task 6: Performance & Responsive (parallel-safe, depends on Task 1)
├─ Core Web Vitals met, mobile layout works
├─ Files affected: responsive.css, layout.css, bootstrap-theme.css, theme.js
├─ Scenarios: Performance trace, multi-viewport screenshots
├─ Timeout: 60-120s
└─ Acceptance: LCP < 2.5s, CLS < 0.1, mobile renders
```

### Execution Timeline

**Sequential Phase (checkpoint required):**
```
0s:     Start Task 1 (Critical Path Validation)
60s:    ✓ Task 1 PASSED
        └─ Checkpoint: Can proceed to parallel tasks

Parallel Phase (no checkpoint required):
60s:    Start Tasks 2, 3, 4, 5, 6 simultaneously
180s:   ✓ Task 2 PASSED (Component Rendering)
180s:   ✓ Task 3 PASSED (User Interaction)
150s:   ✓ Task 5 PASSED (Accessibility)
220s:   ✓ Task 4 PASSED (API Integration)
240s:   ✓ Task 6 PASSED (Performance)

Consolidation Phase:
240s:   All tasks complete → Merge results
270s:   ✓ Final result generated
```

Total execution: ~4-5 minutes for large module (much faster than sequential!)

### Orchestrator Decision Points

```python
def orchestrate_browser_testing(module_metadata, run_input):
    """Orchestrator main entry point."""
    
    file_count = count_files(module_metadata)
    
    if file_count < 10:
        # Single task
        task = create_task(
            skill="browser-testing-with-devtools",
            scenarios=["all"],
            timeout=180,
            depends_on=[]
        )
        queue_task(task)
    
    elif file_count < 20:
        # Two sequential phases
        task_foundation = create_task(
            skill="browser-testing-with-devtools",
            tasks=["critical-path", "rendering"],
            timeout=300,
            depends_on=[]
        )
        queue_task(task_foundation)
        
        # Remaining tasks queued after checkpoint
        task_performance = create_task(
            skill="browser-testing-with-devtools",
            tasks=["interaction", "network", "accessibility", "performance"],
            timeout=300,
            depends_on=[task_foundation],
            allow_parallel=True
        )
        append_to_queue(task_performance)
    
    else:  # file_count > 20
        # Full decomposition with three phases
        # Phase 1: Critical path only
        task_1 = create_task(scenario="critical-path", timeout=60)
        queue_task(task_1)
        
        # Phase 2: Foundation (after Task 1 passes)
        task_2 = create_task(scenario="component-rendering", depends_on=[task_1])
        queue_task(task_2)
        
        # Phase 3: Parallel execution (after Task 1 passes)
        tasks_3_to_6 = [
            create_task(scenario="user-interaction", depends_on=[task_1]),
            create_task(scenario="api-integration", depends_on=[task_1]),
            create_task(scenario="accessibility", depends_on=[task_1]),
            create_task(scenario="performance", depends_on=[task_1])
        ]
        queue_tasks_parallel(tasks_3_to_6)
```

### Result Consolidation

Orchestrator merges individual task results:

```
Input:
├─ task_1_result.json (critical-path)
├─ task_2_result.json (rendering)
├─ task_3_result.json (interaction)
├─ task_4_result.json (network)
├─ task_5_result.json (accessibility)
└─ task_6_result.json (performance)

Consolidation Process:
1. Merge metrics: sum requests, errors, warnings; average timings
2. Aggregate findings: deduplicate, prioritize by severity
3. Generate recommendations: by task, then by priority
4. Produce final result.json with rolled-up status

Output:
{
  "skillName": "browser-testing-with-devtools",
  "status": "passed" (all tasks passed),
  "metrics": {
    "errors": 0,
    "warnings": 2,
    "requests": 18,
    "LCP_ms": 1200,
    "CLS": 0.05,
    "accessibility_violations": 0
  },
  "findings": [...],
  "recommendations": [...]
}
```

## Handling Failures

```python
def handle_firefox_failure(task_result, module_metadata):
    """Orchestrator handles failures intelligently."""
    
    if task_result["status"] == "failed":
        
        if task_result["task"] == "critical-path":
            # If critical path fails, stop immediately
            # Escalate to failure-diagnosis
            escalate_to_failure_diagnosis(module_metadata, task_result)
            return
        
        elif task_result["task"] in ["rendering", "interaction", "network"]:
            # Non-critical: log, continue, but mark as alert
            flag = "medium_priority_fix"
            append_finding(flag, task_result["errors"])
        
        # Continue with remaining tasks (parallelization continues)
```

## Input/Output Contracts

### Input (run-input.json)
```json
{
  "moduleName": "Checklist",
  "baseUrl": "http://localhost:5276",
  "convertedSourceRoot": "/path/to/src",
  "testScenarios": ["critical-path", "rendering", "interaction", "network", "accessibility", "performance"],
  "performanceThresholds": {
    "LCP": 2500,
    "CLS": 0.1,
    "INP": 200
  }
}
```

### Output (artifacts/{ModuleName}/{RunId}/browser-testing-with-devtools/)
```
├── result.json (consolidated, contract v2.0)
├── console-transcript.json
├── network-log.json
├── performance-trace.json
├── accessibility-report.json
├── test-summary.md
├── screenshots/
│   ├── before.png
│   ├── after.png
│   └── mobile_375.png
└── dom-snapshots/
    ├── after_critical_path.html
    └── after_interaction.html
```

## Testing the Integration

### Manual Test

```bash
# 1. Start application
cd src/LegacyModernization.Dashboard.Web
dotnet run

# 2. Create run-input.json
cat > run-inputs/module-run-input.Checklist.test-001.json << EOF
{
  "runId": "test-001",
  "moduleName": "Checklist",
  "baseUrl": "http://localhost:5276",
  "convertedSourceRoot": "src/LegacyModernization.Application",
  "testScenarios": ["critical-path", "rendering", "interaction", "network"],
  "performanceThresholds": {"LCP": 2500, "CLS": 0.1}
}
EOF

# 3. Execute skill manually
python skills/browser-testing-with-devtools/run.py --input run-inputs/module-run-input.Checklist.test-001.json

# 4. Check results
ls artifacts/Checklist/test-001/browser-testing-with-devtools/
cat artifacts/Checklist/test-001/browser-testing-with-devtools/result.json
```

### Orchestrator Test

```python
# Orchestrator workflow simulation
from orchestrator import ModernizationOrchestrator

orchestrator = ModernizationOrchestrator()

# Detect module
module = orchestrator.discover_module("src/LegacyModernization.Application")
print(f"Module files: {len(module.files)}")  # 28 files
print(f"Module type: {module.type}")  # "web"

# Check if browser-testing-with-devtools should be assigned
if orchestrator.should_assign_skill("browser-testing-with-devtools", module):
    print("✓ browser-testing-with-devtools assigned")
    
    # Get task decomposition
    tasks = orchestrator.decompose_browser_testing(module)
    for task in tasks:
        print(f"  Task: {task.name}, files: {len(task.files)}, timeout: {task.timeout}s")
    
    # Execute in phases
    result = orchestrator.execute_browser_testing(module, tasks)
    print(f"Result: {result.status}")
```

---

**Key Takeaway:** The orchestrator automatically handles complex, multi-file modules by:

1. **Detecting** when browser testing is needed
2. **Analyzing** file structure and dependencies
3. **Decomposing** into focused, parallel-safe tasks
4. **Scheduling** efficiently (foundation first, then parallel)
5. **Consolidating** results into final output
6. **Escalating** failures to appropriate downstream skills

This ensures browser testing is **fast**, **reliable**, and **handles large codebases** gracefully.
