using Microsoft.AspNetCore.Mvc;
using System.Text.Json;

namespace LegacyModernization.Dashboard.Web.Controllers;

/// <summary>
/// Test controller for browser testing skill development and validation.
/// Provides mock API endpoints that simulate real application behavior.
/// </summary>
[ApiController]
[Route("api/test")]
public class TestApiController : ControllerBase
{
    private static readonly string[] ConsoleMessages = new[]
    {
        "Application initialized successfully",
        "Module loaded",
        "Bootstrap framework v5.3.0 loaded",
        "Authentication token validated",
        "WebSocket connection established"
    };

    private static readonly string[] WarningMessages = new[]
    {
        "Deprecation warning: Use new API endpoint",
        "Performance: Consider caching this request"
    };

    private static readonly string[] DebugMessages = new[]
    {
        "Service initialized",
        "Database connection pooled",
        "Configuration loaded"
    };

    /// <summary>
    /// Returns mock console logs for testing console analysis.
    /// </summary>
    [HttpGet("console-logs")]
    public IActionResult GetConsoleLogs()
    {
        var context = GetRequestContext();
        var logs = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            messages = new object[]
            {
                new { level = "info", message = ConsoleMessages[0], source = "app.js", line = 1 },
                new { level = "info", message = $"{ConsoleMessages[1]}: {context.moduleName}", source = "modules.js", line = 25 },
                new { level = "info", message = ConsoleMessages[2], source = "styles.css", line = 0 },
                new { level = "info", message = ConsoleMessages[3], source = "auth.ts", line = 120 },
                new { level = "info", message = ConsoleMessages[4], source = "websocket.ts", line = 45 },
                new { level = "warn", message = WarningMessages[0], source = "legacy-api.js", line = 88 },
                new { level = "warn", message = WarningMessages[1], source = "data-service.ts", line = 234 },
                new { level = "debug", message = DebugMessages[0], source = "bootstrap.js", line = 12 },
                new { level = "debug", message = DebugMessages[1], source = "db-pool.ts", line = 56 },
                new { level = "debug", message = DebugMessages[2], source = "config.ts", line = 78 }
            },
            summary = new { errors = 0, warnings = 2, infos = 5, debugs = 3 }
        };

        return Ok(logs);
    }

    /// <summary>
    /// Returns mock network requests for testing network analysis.
    /// </summary>
    [HttpGet("network-requests")]
    public IActionResult GetNetworkRequests()
    {
        var context = GetRequestContext();
        var baseUrl = string.IsNullOrWhiteSpace(Request.Host.Value) ? "http://localhost:5276" : $"{Request.Scheme}://{Request.Host}";
        var requests = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            total = 12,
            requests = new object[]
            {
                new { method = "GET", url = $"{baseUrl}/", status = 200, responseTime = 245, contentType = "text/html" },
                new { method = "GET", url = $"{baseUrl}/css/bootstrap.min.css", status = 200, responseTime = 89, contentType = "text/css" },
                new { method = "GET", url = $"{baseUrl}/js/app.js", status = 200, responseTime = 156, contentType = "application/javascript" },
                new { method = "GET", url = $"{baseUrl}/api/modules", status = 200, responseTime = 432, contentType = "application/json" },
                new { method = "POST", url = $"{baseUrl}/api/auth/login", status = 200, responseTime = 312, contentType = "application/json" },
                new { method = "GET", url = $"{baseUrl}/api/runs/{context.moduleName}/{context.runId}", status = 200, responseTime = 178, contentType = "application/json" },
                new { method = "GET", url = $"{baseUrl}/css/app.css", status = 200, responseTime = 67, contentType = "text/css" },
                new { method = "GET", url = $"{baseUrl}/images/logo.png", status = 200, responseTime = 45, contentType = "image/png" },
                new { method = "GET", url = $"{baseUrl}/api/skills", status = 200, responseTime = 523, contentType = "application/json" },
                new { method = "GET", url = $"{baseUrl}/fonts/roboto.woff2", status = 200, responseTime = 34, contentType = "font/woff2" },
                new { method = "GET", url = $"{baseUrl}/api/dashboard/home", status = 200, responseTime = 267, contentType = "application/json" },
                new { method = "GET", url = $"{baseUrl}/js/vendor/moment.min.js", status = 200, responseTime = 112, contentType = "application/javascript" }
            },
            failed = 0,
            avgResponseTime = 186
        };

        return Ok(requests);
    }

    /// <summary>
    /// Returns mock performance metrics for testing Core Web Vitals.
    /// </summary>
    [HttpGet("performance-metrics")]
    public IActionResult GetPerformanceMetrics()
    {
        var metrics = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            metrics = new
            {
                LCP_ms = 1245,          // Largest Contentful Paint (target: < 2500ms)
                INP_ms = 85,            // Interaction to Next Paint (target: < 200ms)
                CLS = 0.042,            // Cumulative Layout Shift (target: < 0.1)
                TTFB_ms = 412,          // Time to First Byte (target: < 600ms)
                FCP_ms = 892,           // First Contentful Paint (target: < 1800ms)
                DOMContentLoaded = 1156,
                LoadComplete = 2134
            },
            thresholds = new
            {
                LCP = 2500,
                INP = 200,
                CLS = 0.1,
                TTFB = 600,
                FCP = 1800
            },
            allPassing = true
        };

        return Ok(metrics);
    }

    /// <summary>
    /// Returns mock accessibility report for testing WCAG compliance.
    /// </summary>
    [HttpGet("accessibility-report")]
    public IActionResult GetAccessibilityReport()
    {
        var report = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            wcagLevel = "AA",
            summary = new
            {
                violations = 2,
                warnings = 3,
                passes = 28
            },
            violations = new object[]
            {
                new
                {
                    id = "color-contrast",
                    description = "Text color contrast is below AA standard",
                    impact = "serious",
                    nodes = new[] { ".form-label-secondary", ".help-text-muted" },
                    help = "Ensure text contrast ratio is at least 4.5:1"
                },
                new
                {
                    id = "form-field-multiple-labels",
                    description = "Form field without associated label",
                    impact = "critical",
                    nodes = new[] { "#user-search-input" },
                    help = "Associate a label with this form field"
                }
            },
            warnings = new object[]
            {
                new { id = "heading-order", message = "Heading hierarchy skipped levels" },
                new { id = "image-alt-text", message = "Consider adding descriptive alt text" },
                new { id = "link-name", message = "Link text is not descriptive" }
            },
            passes = new[] { "buttons-have-accessible-name", "frame-title", "html-has-lang" }
        };

        return Ok(report);
    }

    /// <summary>
    /// Returns mock DOM structure information.
    /// </summary>
    [HttpGet("dom-structure")]
    public IActionResult GetDomStructure()
    {
        var structure = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            elementCount = 847,
            structure = new
            {
                html = new { count = 1 },
                head = new { count = 1 },
                body = new { count = 1 },
                divs = new { count = 342 },
                spans = new { count = 156 },
                buttons = new { count = 28 },
                forms = new { count = 5 },
                inputs = new { count = 64 },
                links = new { count = 89 },
                images = new { count = 34 },
                lists = new { count = 23 },
                tables = new { count = 8 }
            },
            semanticElements = new { nav = 3, main = 1, section = 12, article = 2, aside = 1, footer = 1 },
            headings = new { h1 = 1, h2 = 8, h3 = 24, h4 = 12, h5 = 3, h6 = 1 }
        };

        return Ok(structure);
    }

    /// <summary>
    /// Health check endpoint to verify application is running.
    /// </summary>
    [HttpGet("health")]
    public IActionResult HealthCheck()
    {
        return Ok(new
        {
            status = "healthy",
            timestamp = DateTime.UtcNow.ToString("O"),
            services = new
            {
                database = "connected",
                cache = "available",
                authentication = "ready",
                api = "responding"
            }
        });
    }

    /// <summary>
    /// Simulates user interaction form submission.
    /// </summary>
    [HttpPost("form-submit")]
    public IActionResult SubmitForm([FromBody] JsonElement formData)
    {
        return Ok(new
        {
            success = true,
            message = "Form submitted successfully",
            timestamp = DateTime.UtcNow.ToString("O"),
            processingTime = "145ms"
        });
    }

    /// <summary>
    /// Returns interaction flow simulation data.
    /// </summary>
    [HttpGet("interaction-flows")]
    public IActionResult GetInteractionFlows()
    {
        var flows = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            flows = new object[]
            {
                new
                {
                    name = "Critical Path - Page Load",
                    status = "passed",
                    duration = 2150,
                    steps = new object[]
                    {
                        new { name = "Navigate", duration = 245, status = "passed" },
                        new { name = "DOM Interactive", duration = 892, status = "passed" },
                        new { name = "Page Complete", duration = 1013, status = "passed" }
                    }
                },
                new
                {
                    name = "Form Interaction",
                    status = "passed",
                    duration = 3420,
                    steps = new object[]
                    {
                        new { name = "Focus Input", duration = 45, status = "passed" },
                        new { name = "Type Content", duration = 1200, status = "passed" },
                        new { name = "Submit", duration = 156, status = "passed" },
                        new { name = "Receive Response", duration = 2019, status = "passed" }
                    }
                },
                new
                {
                    name = "Navigation",
                    status = "passed",
                    duration = 1560,
                    steps = new object[]
                    {
                        new { name = "Click Link", duration = 67, status = "passed" },
                        new { name = "Wait for Load", duration = 1493, status = "passed" }
                    }
                }
            }
        };

        return Ok(flows);
    }

    /// <summary>
    /// Returns all test data in a single aggregated response.
    /// </summary>
    [HttpGet("all-data")]
    public IActionResult GetAllTestData([FromQuery] string? moduleName, [FromQuery] string? runId)
    {
        var context = GetRequestContext(moduleName, runId);
        var allData = new
        {
            timestamp = DateTime.UtcNow.ToString("O"),
            module = context.moduleName,
            runId = context.runId,
            data = new
            {
                consoleLogs = GetConsoleLogs() as OkObjectResult ?? new OkObjectResult(null),
                networkRequests = GetNetworkRequests() as OkObjectResult ?? new OkObjectResult(null),
                performanceMetrics = GetPerformanceMetrics() as OkObjectResult ?? new OkObjectResult(null),
                accessibility = GetAccessibilityReport() as OkObjectResult ?? new OkObjectResult(null),
                domStructure = GetDomStructure() as OkObjectResult ?? new OkObjectResult(null),
                interactionFlows = GetInteractionFlows() as OkObjectResult ?? new OkObjectResult(null)
            }
        };

        return Ok(allData);
    }

    private (string moduleName, string runId) GetRequestContext(string? moduleName = null, string? runId = null)
    {
        var effectiveModule = !string.IsNullOrWhiteSpace(moduleName)
            ? moduleName
            : (Request.Query["moduleName"].ToString() is { Length: > 0 } queryModule ? queryModule : "module-from-query");
        var effectiveRun = !string.IsNullOrWhiteSpace(runId)
            ? runId
            : (Request.Query["runId"].ToString() is { Length: > 0 } queryRun ? queryRun : "run-from-query");
        return (effectiveModule, effectiveRun);
    }
}
