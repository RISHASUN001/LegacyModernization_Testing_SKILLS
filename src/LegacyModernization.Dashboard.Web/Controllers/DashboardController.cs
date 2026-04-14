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
    public async Task<IActionResult> RunInputBuilder(RunInputDraftDto draft, string submitAction, CancellationToken cancellationToken)
    {
        draft.SelectedSkills ??= [];
        var generated = await _dashboard.GetRunInputBuilderAsync(cancellationToken);

        var rebuilt = new RunInputBuilderPageDto
        {
            Draft = draft,
            AvailableSkills = generated.AvailableSkills,
            GeneratedJson = BuildJsonPreview(draft)
        };

        if (string.Equals(submitAction, "save", StringComparison.OrdinalIgnoreCase))
        {
            var savedPath = await _dashboard.SaveRunInputAsync(draft, cancellationToken);
            rebuilt = new RunInputBuilderPageDto
            {
                Draft = rebuilt.Draft,
                AvailableSkills = rebuilt.AvailableSkills,
                GeneratedJson = rebuilt.GeneratedJson,
                SavedPath = savedPath
            };

            return View("RunInputBuilder", new RunInputBuilderFormModel
            {
                Page = rebuilt,
                Message = $"Run input saved to {savedPath}"
            });
        }

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
        var testApiEndpoint = string.IsNullOrWhiteSpace(normalizedBaseUrl)
            ? string.Empty
            : $"{normalizedBaseUrl}/api/test";

        var knownUrls = ResolveKnownUrls(SplitLines(draft.KnownUrlsText), normalizedBaseUrl);

        var payload = new
        {
            runId = string.IsNullOrWhiteSpace(draft.RunId) ? "run-001" : draft.RunId.Trim(),
            moduleName = (draft.ModuleName ?? string.Empty).Trim(),
            legacySourceRoot = (draft.LegacySourceRoot ?? string.Empty).Trim(),
            convertedSourceRoot = (draft.ConvertedSourceRoot ?? string.Empty).Trim(),
            baseUrl,
            testApiEndpoint,
            targetUrl = ResolveTargetUrl((draft.TargetUrl ?? string.Empty).Trim(), normalizedBaseUrl),
            strictModuleOnly = draft.StrictModuleOnly,
            allowedCrossModules = SplitLines(draft.AllowedCrossModulesText),
            architecturePolicy = NormalizeArchitecturePolicy((draft.ArchitecturePolicy ?? string.Empty).Trim()),
            generateModuleClaudeMd = draft.GenerateModuleClaudeMd,
            brsPath = (draft.BrsPath ?? string.Empty).Trim(),
            moduleHints = new
            {
                relatedFolders = SplitLines(draft.RelatedFoldersText),
                knownUrls,
                keywords = SplitLines(draft.KeywordsText),
                scopeHint = NormalizeScopeHint((draft.ModuleScopeHint ?? string.Empty).Trim())
            },
            testCommands = new
            {
                unit = (draft.UnitCommand ?? string.Empty).Trim(),
                integration = (draft.IntegrationCommand ?? string.Empty).Trim(),
                api = (draft.ApiCommand ?? string.Empty).Trim(),
                e2e = (draft.E2eCommand ?? string.Empty).Trim(),
                edgeCase = (draft.EdgeCaseCommand ?? string.Empty).Trim(),
                playwright = (draft.PlaywrightCommand ?? string.Empty).Trim()
            },
            selectedSkills = draft.SelectedSkills ?? []
        };

        return System.Text.Json.JsonSerializer.Serialize(payload, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
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
            _ => "application/octet-stream"
        };
    }
}
