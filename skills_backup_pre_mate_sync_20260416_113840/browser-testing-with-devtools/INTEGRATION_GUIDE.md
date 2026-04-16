# Browser Testing Skill - Complete Integration Guide

This document describes the complete browser testing skill implementation with database persistence and frontend integration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                          │
│  (RunInputBuilder.cshtml + Results Display Components)          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ queries
                     │ DashboardQueryService.GetBrowserTestingResultsAsync()
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         DashboardQueryService (Infrastructure)                  │
│  - Queries browser_devtools_* tables                           │
│  - Maps to DTOs (BrowserTestingResultsDto, etc.)               │
│  - Returns complete testing results                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite Database                               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_devtools_sessions                           │      │
│  │ - id, base_url, start/end_timestamp                 │      │
│  │ - total/passed/failed_scenarios                      │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_console_logs                                │      │
│  │ - level, message, source_file, source_line          │      │
│  │ - stack_trace                                        │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_network_requests                            │      │
│  │ - method, url, status_code                          │      │
│  │ - request/response_payload, response_time_ms        │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_performance_metrics                         │      │
│  │ - metric_name, metric_value, target_threshold       │      │
│  │ - meets_threshold                                    │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_accessibility_issues                        │      │
│  │ - issue_type, severity, element_selector            │      │
│  │ - issue_description, recommendation                 │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_screenshots                                 │      │
│  │ - filename, artifact_path, viewport_*               │      │
│  │ - scenario_context, captured_at                     │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ browser_dom_snapshots                               │      │
│  │ - filename, artifact_path, element_count            │      │
│  │ - scenario_context, captured_at                     │      │
│  └──────────────────────────────────────────────────────┘      │
└────────────────────┬────────────────────────────────────────────┘
                     ▲
                     │
                     │ persists results
                     │
┌─────────────────────────────────────────────────────────────────┐
│          Skill Runtime (run.py)                                 │
│  - BrowserDevToolsResultsPersister                              │
│  - parse_console_logs() → INSERT INTO browser_console_logs     │
│  - parse_network_requests() → INSERT INTO browser_network_*   │
│  - parse_metrics() → INSERT INTO browser_performance_metrics   │
│  - parse_issues() → INSERT INTO browser_accessibility_issues  │
│  - save_screenshots() → INSERT INTO browser_screenshots        │
│  - save_dom_snapshots() → INSERT INTO browser_dom_snapshots   │
└────────────────────┬────────────────────────────────────────────┘
                     ▲
                     │
                     │ task results
                     │
┌─────────────────────────────────────────────────────────────────┐
│              Task Implementations (tasks/*.py)                  │
│  ┌────────────────────────────────────────────────────┐        │
│  │ critical_path_validation.py                       │        │
│  │ - Validates page load, console, initial network   │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ component_rendering.py                            │        │
│  │ - DOM structure, CSS rendering, Bootstrap         │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ network_integration.py                            │        │
│  │ - API calls, CORS, response validation            │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ accessibility_scan.py                             │        │
│  │ - WCAG 2.1, ARIA labels, keyboard navigation      │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ performance_profiling.py                          │        │
│  │ - Core Web Vitals: LCP, CLS, INP, TTFB, FCP       │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ user_interaction.py                               │        │
│  │ - Forms, user flows, focus management             │        │
│  └────────────────────────────────────────────────────┘        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Chrome DevTools MCP calls
                     │
┌─────────────────────────────────────────────────────────────────┐
│         Chrome DevTools Protocol (MCP)                          │
│  - localhost:9222 (when Chrome DevTools Protocol enabled)      │
│  - Captures DOM, console, network, performance                 │
│  - Pseudo-implementations until real MCP available             │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Skill Execution Flow

```
Skill starts with run.py
    │
    ├─ Load module-run-input.json (module_name, base_url, database_path)
    │
    ├─ Orchestrate task execution:
    │   ├─ critical_path_validation(base_url, module_name)
    │   ├─ component_rendering(base_url, module_name)
    │   ├─ network_integration(base_url, module_name)
    │   ├─ accessibility_scan(base_url, module_name)
    │   ├─ performance_profiling(base_url, module_name)
    │   └─ user_interaction(base_url, module_name)
    │
    ├─ Parse aggregate results from all tasks
    │
    └─ Persist to SQLite via BrowserDevToolsResultsPersister
        ├─ create_browser_session()
        ├─ persist_console_logs()
        ├─ persist_network_requests()
        ├─ persist_performance_metrics()
        ├─ persist_accessibility_issues()
        ├─ persist_screenshots()
        └─ persist_dom_snapshots()
```

### 2. Frontend Query Flow

```
Frontend calls DashboardController.GetBrowserTestingResults(moduleName, runId)
    │
    ├─ Calls DashboardQueryService.GetBrowserTestingResultsAsync()
    │
    ├─ Queries browser_devtools_sessions (finds session_fk)
    │
    ├─ Queries related tables (console_logs, network_requests, etc.)
    │
    ├─ Maps SQL results to DTOs:
    │   ├─ BrowserTestingResultsDto (aggregated)
    │   ├─ BrowserSessionDto[]
    │   ├─ BrowserConsoleLogDto[]
    │   ├─ BrowserNetworkRequestDto[]
    │   ├─ BrowserPerformanceMetricDto[]
    │   ├─ BrowserAccessibilityIssueDto[]
    │   ├─ BrowserScreenshotDto[]
    │   └─ BrowserDomSnapshotDto[]
    │
    └─ Returns to controller, serialized to JSON for frontend
```

## Individual Task Specifications

### Critical Path Validation

**Purpose**: Verify the application's critical user journey

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- console_logs: Captured console output (optional)
- network_requests: Captured network requests (optional)

**Outputs**:
- Page load time
- Critical error count
- Initial request success rate
- Findings: console errors, failed requests, early loading issues

**CLI**:
```bash
python tasks/critical_path_validation.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --console-logs console.json \
  --network-requests network.json
```

### Component Rendering

**Purpose**: Validate UI components render and style correctly

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- dom_elements: DOM structure analysis
- css_metrics: CSS loading and layout metrics
- accessibility_data: Accessibility tree info

**Outputs**:
- Components found count
- CSS issues count
- Layout shift score (CLS)
- Interactive elements count
- Findings: missing alt text, high CLS, failed CSS loads, semantic HTML issues

**CLI**:
```bash
python tasks/component_rendering.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --dom-elements dom.json \
  --css-metrics css.json \
  --accessibility accessibility.json
```

### Network Integration

**Purpose**: Validate API calls and network behavior

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- network_requests: List of network requests captured
- response_validation: Schema validation results
- performance_targets: Expected thresholds

**Outputs**:
- Total requests, successful, failed counts
- Avg response time
- CORS errors, timeout errors
- Findings: failed API calls, CORS misconfiguration, slow requests, high request count

**CLI**:
```bash
python tasks/network_integration.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --network-requests network.json \
  --response-validation responses.json \
  --performance-targets thresholds.json
```

### Accessibility Scan

**Purpose**: Verify WCAG 2.1 compliance

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- accessibility_report: Axe/accessibility tool report
- wcag_level: A, AA, or AAA (default: AA)

**Outputs**:
- Violations, warnings, passes counts
- Color contrast issues
- ARIA labeling issues
- Keyboard navigation issues
- Findings: WCAG violations, missing alt text, invalid heading hierarchy

**CLI**:
```bash
python tasks/accessibility_scan.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --report accessibility.json \
  --wcag-level AA
```

### Performance Profiling

**Purpose**: Capture and analyze Core Web Vitals

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- performance_data: Captured metrics (LCP, INP, CLS, TTFB, FCP)
- custom_thresholds: Custom performance targets

**Outputs**:
- All Core Web Vitals metrics
- Vitals passing/failing count
- JavaScript execution time
- Long task detection
- Findings: metrics exceeding thresholds, slow JS, main thread blocking

**CLI**:
```bash
python tasks/performance_profiling.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --performance-data perf.json \
  --custom-thresholds thresholds.json
```

### User Interaction

**Purpose**: Validate user interaction flows (forms, navigation, etc.)

**Inputs**:
- base_url: Application URL
- module_name: Module being tested
- interaction_flows: List of user journey scenarios
- form_validation: Form handling validation results

**Outputs**:
- Flows tested/passed/failed counts
- Forms tested count
- Valid/invalid interactions count
- Findings: failed flows, missing form validation, unclear error messages, focus management issues

**CLI**:
```bash
python tasks/user_interaction.py \
  --base-url http://localhost:5276 \
  --module MyModule \
  --flows flows.json \
  --forms forms.json
```

## Database Schema

### browser_devtools_sessions
Main session record linking to skill execution and run.

```sql
CREATE TABLE browser_devtools_sessions (
    id INTEGER PRIMARY KEY,
    skill_execution_fk INTEGER NOT NULL,  -- FK to skill_executions
    run_fk INTEGER NOT NULL,              -- FK to runs
    base_url TEXT NOT NULL,
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    total_scenarios INTEGER NOT NULL,
    passed_scenarios INTEGER NOT NULL,
    failed_scenarios INTEGER NOT NULL,
    viewport_sizes TEXT NOT NULL          -- JSON array
);
```

### browser_console_logs
Application console output captured during testing.

```sql
CREATE TABLE browser_console_logs (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,          -- FK to browser_devtools_sessions
    level TEXT NOT NULL,                  -- error, warn, info, debug
    message TEXT NOT NULL,
    source_file TEXT,
    source_line INTEGER,
    timestamp TEXT NOT NULL,
    stack_trace TEXT
);
```

### browser_network_requests
HTTP requests/responses captured during testing.

```sql
CREATE TABLE browser_network_requests (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,
    method TEXT NOT NULL,                 -- GET, POST, etc.
    url TEXT NOT NULL,
    status_code INTEGER,
    request_payload TEXT,
    response_payload TEXT,
    response_time_ms INTEGER,
    content_type TEXT,
    timestamp TEXT NOT NULL
);
```

### browser_performance_metrics
Core Web Vitals and other performance metrics.

```sql
CREATE TABLE browser_performance_metrics (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,
    metric_name TEXT NOT NULL,            -- LCP, CLS, INP, TTFB, FCP
    metric_value REAL NOT NULL,
    target_threshold REAL,
    meets_threshold BOOLEAN,
    timestamp TEXT NOT NULL
);
```

### browser_accessibility_issues
Accessibility compliance issues found.

```sql
CREATE TABLE browser_accessibility_issues (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,
    issue_type TEXT NOT NULL,             -- color-contrast, aria, keyboard-nav, etc.
    severity TEXT NOT NULL,               -- critical, high, medium, low
    element_selector TEXT,
    issue_description TEXT NOT NULL,
    recommendation TEXT,
    timestamp TEXT NOT NULL
);
```

### browser_screenshots
Screenshots captured during testing.

```sql
CREATE TABLE browser_screenshots (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,
    filename TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    viewport_width INTEGER,
    viewport_height INTEGER,
    scenario_context TEXT,
    captured_at TEXT NOT NULL
);
```

### browser_dom_snapshots
DOM structure snapshots captured during testing.

```sql
CREATE TABLE browser_dom_snapshots (
    id INTEGER PRIMARY KEY,
    session_fk INTEGER NOT NULL,
    filename TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    scenario_context TEXT,
    element_count INTEGER,
    captured_at TEXT NOT NULL
);
```

## Frontend Integration

### 1. Skill Selection
The browser-testing-with-devtools skill automatically appears in RunInputBuilder.cshtml once metadata is synced:

```html
<!-- Auto-populated from skill_library table -->
@foreach (var skill in Model.Page.AvailableSkills)
{
    <input type="checkbox" id="@skill.Name" name="SelectedSkills" value="@skill.Name" />
    <label for="@skill.Name">@skill.Name</label>
}
```

### 2. Results Display
Create a controller action to retrieve browser testing results:

```csharp
[HttpGet("run/{moduleName}/{runId}/browser-testing")]
public async Task<IActionResult> GetBrowserTestingResults(
    string moduleName,
    string runId,
    CancellationToken cancellationToken)
{
    var results = await _dashboardQueryService.GetBrowserTestingResultsAsync(
        moduleName,
        runId,
        cancellationToken);
    
    if (results is null)
    {
        return NotFound();
    }
    
    return Ok(results);
}
```

### 3. Razor View (example)
```html
@model BrowserTestingResultsDto

<h2>Browser Testing Results for @Model.ModuleName (@Model.RunId)</h2>

<div class="alert alert-@ToCssClass(Model.Status)">
    @Model.Status.ToUpper()
</div>

<!-- Console Logs Section -->
<section>
    <h3>Console Logs (@Model.ConsoleLogs.Count)</h3>
    <table>
        <tr>
            <th>Level</th>
            <th>Message</th>
            <th>Source</th>
            <th>Time</th>
        </tr>
        @foreach (var log in Model.ConsoleLogs.Where(l => l.Level == "error").Take(10))
        {
            <tr class="@(log.Level)">
                <td>@log.Level</td>
                <td>@log.Message</td>
                <td>@log.SourceFile:@log.SourceLine</td>
                <td>@log.Timestamp</td>
            </tr>
        }
    </table>
</section>

<!-- Performance Metrics Section -->
<section>
    <h3>Core Web Vitals</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Threshold</th>
            <th>Status</th>
        </tr>
        @foreach (var metric in Model.PerformanceMetrics)
        {
            <tr>
                <td>@metric.MetricName</td>
                <td>@metric.MetricValue.ToString("F2")</td>
                <td>@metric.TargetThreshold.ToString("F2")</td>
                <td>@(metric.MeetsThreshold ? "✓" : "✗")</td>
            </tr>
        }
    </table>
</section>

<!-- Accessibility Issues Section -->
<section>
    <h3>Accessibility Issues (@Model.AccessibilityIssues.Count)</h3>
    @foreach (var group in Model.AccessibilityIssues.GroupBy(i => i.Severity))
    {
        <h4>@group.Key Severity</h4>
        <ul>
            @foreach (var issue in group)
            {
                <li>@issue.IssueType: @issue.IssueDescription</li>
            }
        </ul>
    }
</section>
```

## Configuration

### module-run-input.json
The skill runner reads module configuration:

```json
{
  "moduleName": "MyModule",
  "baseUrl": "http://localhost:5276",
  "convertedSourceRoot": "/path/to/converted/src",
  "legacySourceRoot": "/path/to/legacy/src",
  "brsPath": "/path/to/brs/document.docx",
  "databasePath": "/path/to/modernization.db",
  "testScenarios": [
    "critical-path",
    "component-rendering",
    "network-integration",
    "accessibility",
    "performance",
    "user-interaction"
  ]
}
```

## Next Steps for Production

1. **Replace Pseudo-Implementations**: Update tasks/*.py to use real Chrome DevTools Protocol calls instead of mocked data
2. **Add MCP Integration**: Implement Chrome DevTools MCP server integration
3. **Error Handling**: Add comprehensive error handling and retry logic
4. **Async Task Decomposition**: Implement orchestrator logic for large modules (20-30 files) with task batching
5. **Frontend UI**: Build Bootstrap-based result display components
6. **Artifact Linking**: Store screenshot/snapshot references and create artifact viewers
7. **Reporting**: Add PDF/HTML report generation from database results
8. **Caching**: Implement result caching for repeated runs
9. **Alerting**: Send notifications for critical findings (WCAG violations, performance regressions)
10. **Trending**: Track metrics over iterations to show progress/regressions

## Troubleshooting

### Skill doesn't appear in frontend
- Ensure skill metadata is synced: check that browser-testing-with-devtools appears in `skills` table
- Verify SKILL.md and config.json exist in the skill folder
- Restart the application to trigger MetadataSyncService

### Results not persisting to database
- Check that database connection string is valid in module-run-input.json
- Verify tables exist: `SELECT name FROM sqlite_master WHERE type='table' LIKE 'browser_%'`
- Check application logs for SQL errors

### Tasks not completing
- Ensure Chrome is running with DevTools Protocol enabled: `chrome --remote-debugging-port=9222`
- Check that base_url is accessible
- Look for network errors in console logs

## References

- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [Web Performance APIs](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Core Web Vitals](https://web.dev/vitals/)
