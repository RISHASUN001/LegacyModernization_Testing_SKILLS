using LegacyModernization.Application.Contracts;
using LegacyModernization.Application.DTOs;
using LegacyModernization.Dashboard.Web.Models;
using LegacyModernization.Infrastructure.Options;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

namespace LegacyModernization.Dashboard.Web.Controllers;

public sealed class DashboardController : Controller
{
    private readonly IDashboardQueryService _dashboard;
    private readonly IMetadataSyncService _metadataSync;
    private readonly PlatformPathsOptions _paths;

    public DashboardController(IDashboardQueryService dashboard, IMetadataSyncService metadataSync, IOptions<PlatformPathsOptions> paths)
    {
        _dashboard = dashboard;
        _metadataSync = metadataSync;
        _paths = paths.Value;
    }

    [HttpGet("/")]
    [HttpGet("home")]
    public async Task<IActionResult> Index(CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);
        var model = await _dashboard.GetHomePageAsync(cancellationToken);
        return View("Index", model);
    }

    [HttpGet("skill-library")]
    public async Task<IActionResult> SkillLibrary(CancellationToken cancellationToken)
    {
        var model = await _dashboard.GetSkillLibraryAsync(cancellationToken);
        return View("SkillLibrary", model);
    }

    [HttpGet("run-input-builder")]
    public async Task<IActionResult> RunInputBuilder(CancellationToken cancellationToken)
    {
        var page = await _dashboard.GetRunInputBuilderAsync(cancellationToken);
        return View("RunInputBuilder", new RunInputBuilderFormModel { Page = page });
    }

    [HttpPost("run-input-builder")]
    [ValidateAntiForgeryToken]
    public IActionResult RunInputBuilder(RunInputDraftDto draft, string submitAction, CancellationToken cancellationToken)
    {
        var rebuilt = new RunInputBuilderPageDto
        {
            Draft = draft,
            GeneratedJson = BuildJsonPreview(draft)
        };

        return View("RunInputBuilder", new RunInputBuilderFormModel { Page = rebuilt });
    }

    [HttpGet("module-runs")]
    public async Task<IActionResult> ModuleRuns([FromQuery] string? module, CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);
        var model = await _dashboard.GetModuleRunsAsync(module, cancellationToken);
        return View("ModuleRuns", model);
    }

    [HttpGet("pipeline/{moduleName}/{runId}")]
    public async Task<IActionResult> Pipeline(string moduleName, string runId, CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);
        var model = await _dashboard.GetRunPipelineAsync(moduleName, runId, cancellationToken);
        if (model is null)
        {
            return NotFound();
        }

        return View("Pipeline", model);
    }

    [HttpPost("pipeline/{moduleName}/{runId}/playwright-inputs")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> SavePlaywrightInputs(string moduleName, string runId, [FromForm] string? inputOverridesJson, CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);

        var raw = (inputOverridesJson ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(raw))
        {
            TempData["PipelineMessage"] = "Playwright input overrides cleared (empty payload).";
            return RedirectToAction("Pipeline", new { moduleName, runId });
        }

        try
        {
            using var _ = System.Text.Json.JsonDocument.Parse(raw);
        }
        catch
        {
            TempData["PipelineMessage"] = "Invalid JSON. Provide a valid JSON payload for Playwright input overrides.";
            return RedirectToAction("Pipeline", new { moduleName, runId });
        }

        var outputPath = Path.GetFullPath(Path.Combine(_paths.ArtifactsRoot, moduleName, runId, "playwright-browser-verification", "user-input-overrides.json"));
        var rootPath = Path.GetFullPath(_paths.ArtifactsRoot);
        if (!outputPath.StartsWith(rootPath, StringComparison.Ordinal))
        {
            return BadRequest("Invalid output path for Playwright input overrides.");
        }

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        await System.IO.File.WriteAllTextAsync(outputPath, raw, cancellationToken);

        TempData["PipelineMessage"] = "Playwright input overrides saved. Re-run pipeline (or Playwright stage) to apply them.";
        return RedirectToAction("Pipeline", new { moduleName, runId });
    }

    [HttpGet("findings")]
    public async Task<IActionResult> Findings([FromQuery] string? module, [FromQuery] string? runId, CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);
        var model = await _dashboard.GetFindingsAsync(module, runId, cancellationToken);
        return View("Findings", model);
    }

    [HttpGet("help-guide")]
    public IActionResult HelpGuide()
    {
        return View("HelpGuide");
    }

    [HttpGet("iteration-comparison/{moduleName}")]
    public async Task<IActionResult> IterationComparison(string moduleName, CancellationToken cancellationToken)
    {
        await _metadataSync.SyncAsync(cancellationToken);
        var model = await _dashboard.GetIterationComparisonAsync(moduleName, cancellationToken);
        if (model is null)
        {
            return NotFound();
        }

        return View("IterationComparison", model);
    }

    [HttpGet("artifacts/file")]
    public IActionResult ArtifactFile([FromQuery] string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return BadRequest("Missing artifact path.");
        }

        var artifactsRoot = Path.GetFullPath(_paths.ArtifactsRoot);
        var requestedPath = Path.GetFullPath(path);

        if (!requestedPath.StartsWith(artifactsRoot, StringComparison.Ordinal))
        {
            return BadRequest("Artifact path is outside the allowed root.");
        }

        if (!System.IO.File.Exists(requestedPath))
        {
            return NotFound();
        }

        var contentType = GetContentType(requestedPath);
        return PhysicalFile(requestedPath, contentType, enableRangeProcessing: true);
    }

    private static string BuildJsonPreview(RunInputDraftDto draft)
    {
        draft ??= new RunInputDraftDto();
        var baseUrl = NormalizeBaseUrlForRunInput((draft.BaseUrl ?? string.Empty).Trim());
        var normalizedBaseUrl = baseUrl.TrimEnd('/');

        var workflowNames = SplitList(draft.WorkflowNamesText);
        var convertedRoots = SplitList(draft.ConvertedRootsText);
        var legacyBackendRoots = SplitList(draft.LegacyBackendRootsText);
        var legacyFrontendRoots = SplitList(draft.LegacyFrontendRootsText);

        if (convertedRoots.Count == 0 && !string.IsNullOrWhiteSpace(draft.ConvertedSourceRoot))
        {
            convertedRoots.Add(draft.ConvertedSourceRoot.Trim());
        }

        if (legacyBackendRoots.Count == 0)
        {
            var fallbackBackend = string.IsNullOrWhiteSpace(draft.LegacyBackendRoot)
                ? draft.LegacySourceRoot
                : draft.LegacyBackendRoot;
            if (!string.IsNullOrWhiteSpace(fallbackBackend))
            {
                legacyBackendRoots.Add(fallbackBackend.Trim());
            }
        }

        if (legacyFrontendRoots.Count == 0 && !string.IsNullOrWhiteSpace(draft.LegacyFrontendRoot))
        {
            legacyFrontendRoots.Add(draft.LegacyFrontendRoot.Trim());
        }

        var startUrl = ResolveTargetUrl((draft.ModuleStartUrl ?? string.Empty).Trim(), normalizedBaseUrl);

        var dotnetTestTarget = string.IsNullOrWhiteSpace(draft.DotnetTestTarget)
            ? (draft.ConvertedModuleRoot ?? string.Empty).Trim()
            : draft.DotnetTestTarget.Trim();

        var payload = new
        {
            runId = string.IsNullOrWhiteSpace(draft.RunId) ? "run-001" : draft.RunId.Trim(),
            moduleName = (draft.ModuleName ?? string.Empty).Trim(),
            workflowNames,
            convertedRoots,
            legacyBackendRoots,
            legacyFrontendRoots,
            baseUrl,
            startUrl,
            dotnetTestTarget,
            strictModuleOnly = draft.StrictModuleOnly,
            strictAIGeneration = draft.StrictAIGeneration,
            enableUserInputPrompting = draft.EnableUserInputPrompting,
            keywords = SplitList(draft.KeywordsText),
            controllerHints = SplitList(draft.ControllerActionHintsText),
            viewHints = SplitList(draft.JspFolderHintsText),
            expectedEndUrls = ResolveKnownUrls(SplitList(draft.ExpectedTerminalUrlsText), normalizedBaseUrl)
        };

        return System.Text.Json.JsonSerializer.Serialize(payload, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
    }

    private static List<string> SplitList(string? input)
    {
        return (input ?? string.Empty)
            .Split(new[] { "\r\n", "\n", "\r", "," }, StringSplitOptions.RemoveEmptyEntries)
            .Select(static value => value.Trim())
            .Where(static value => !string.IsNullOrWhiteSpace(value))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static List<string> SplitLines(string? input)
    {
        return (input ?? string.Empty)
            .Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.RemoveEmptyEntries)
            .Select(static value => value.Trim())
            .Where(static value => !string.IsNullOrWhiteSpace(value))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static string NormalizeBaseUrlForRunInput(string baseUrl)
    {
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            return string.Empty;
        }

        if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri))
        {
            return baseUrl;
        }

        var host = uri.Host == "0.0.0.0" ? "localhost" : uri.Host;
        var builder = new UriBuilder(uri.Scheme, host, uri.Port);
        return builder.Uri.ToString().TrimEnd('/');
    }

    private static List<string> ResolveKnownUrls(List<string> knownUrls, string normalizedBaseUrl)
    {
        if (string.IsNullOrWhiteSpace(normalizedBaseUrl))
        {
            return knownUrls;
        }

        var resolved = new List<string>();
        foreach (var value in knownUrls)
        {
            if (Uri.TryCreate(value, UriKind.Absolute, out var absolute))
            {
                var host = absolute.Host == "0.0.0.0" ? "localhost" : absolute.Host;
                resolved.Add(new UriBuilder(absolute.Scheme, host, absolute.Port, absolute.AbsolutePath).Uri.ToString().TrimEnd('/'));
                continue;
            }

            if (value.StartsWith('/'))
            {
                resolved.Add($"{normalizedBaseUrl}{value}");
                continue;
            }

            resolved.Add(value);
        }

        return resolved.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    private static string ResolveTargetUrl(string targetUrl, string normalizedBaseUrl)
    {
        if (string.IsNullOrWhiteSpace(targetUrl))
        {
            return string.Empty;
        }

        if (Uri.TryCreate(targetUrl, UriKind.Absolute, out var absolute))
        {
            var host = absolute.Host == "0.0.0.0" ? "localhost" : absolute.Host;
            return new UriBuilder(absolute.Scheme, host, absolute.Port, absolute.AbsolutePath).Uri.ToString().TrimEnd('/');
        }

        if (!string.IsNullOrWhiteSpace(normalizedBaseUrl) && targetUrl.StartsWith('/'))
        {
            return $"{normalizedBaseUrl}{targetUrl}";
        }

        return targetUrl;
    }

    private static string NormalizeScopeHint(string scopeHint)
    {
        if (string.IsNullOrWhiteSpace(scopeHint))
        {
            return string.Empty;
        }

        var words = scopeHint
            .Split(new[] { ' ', '\t', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
            .Take(20)
            .ToArray();
        return string.Join(' ', words);
    }

    private static string NormalizeArchitecturePolicy(string policy)
    {
        var normalized = (policy ?? string.Empty).Trim().ToLowerInvariant();
        return normalized switch
        {
            "module-first" or "balanced" or "clean-architecture" => normalized,
            _ => "module-first"
        };
    }

    private static string GetContentType(string path)
    {
        var extension = Path.GetExtension(path).ToLowerInvariant();
        return extension switch
        {
            ".png" => "image/png",
            ".jpg" or ".jpeg" => "image/jpeg",
            ".webp" => "image/webp",
            ".gif" => "image/gif",
            ".svg" => "image/svg+xml",
            ".json" => "application/json",
            ".txt" or ".log" => "text/plain",
            ".ts" => "text/plain",
            _ => "application/octet-stream"
        };
    }
}
