using LegacyModernization.Application.Contracts;
using LegacyModernization.Application.DTOs;
using LegacyModernization.Dashboard.Web.Models;
using Microsoft.AspNetCore.Mvc;

namespace LegacyModernization.Dashboard.Web.Controllers;

public sealed class DashboardController : Controller
{
    private readonly IDashboardQueryService _dashboard;

    public DashboardController(IDashboardQueryService dashboard)
    {
        _dashboard = dashboard;
    }

    [HttpGet("/")]
    [HttpGet("home")]
    public async Task<IActionResult> Index(CancellationToken cancellationToken)
    {
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
        var model = await _dashboard.GetModuleRunsAsync(module, cancellationToken);
        return View("ModuleRuns", model);
    }

    [HttpGet("pipeline/{moduleName}/{runId}")]
    public async Task<IActionResult> Pipeline(string moduleName, string runId, CancellationToken cancellationToken)
    {
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
        var model = await _dashboard.GetFindingsAsync(module, runId, cancellationToken);
        return View("Findings", model);
    }

    [HttpGet("iteration-comparison/{moduleName}")]
    public async Task<IActionResult> IterationComparison(string moduleName, CancellationToken cancellationToken)
    {
        var model = await _dashboard.GetIterationComparisonAsync(moduleName, cancellationToken);
        if (model is null)
        {
            return NotFound();
        }

        return View("IterationComparison", model);
    }

    private static string BuildJsonPreview(RunInputDraftDto draft)
    {
        var payload = new
        {
            runId = draft.RunId,
            moduleName = draft.ModuleName,
            legacySourceRoot = draft.LegacySourceRoot,
            convertedSourceRoot = draft.ConvertedSourceRoot,
            baseUrl = draft.BaseUrl,
            brsPath = draft.BrsPath,
            moduleHints = new
            {
                relatedFolders = SplitLines(draft.RelatedFoldersText),
                knownUrls = SplitLines(draft.KnownUrlsText),
                keywords = SplitLines(draft.KeywordsText)
            },
            selectedSkills = draft.SelectedSkills
        };

        return System.Text.Json.JsonSerializer.Serialize(payload, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
    }

    private static List<string> SplitLines(string input)
    {
        return input
            .Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.RemoveEmptyEntries)
            .Select(static value => value.Trim())
            .Where(static value => !string.IsNullOrWhiteSpace(value))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }
}
