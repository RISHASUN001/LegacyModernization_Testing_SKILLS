using MATE.Dashboard.Web.Models.Pipeline;
using MATE.Dashboard.Web.Options;
using MATE.Dashboard.Web.Services;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Mvc;
using System.Text;
using System.Text.Json;

namespace MATE.Dashboard.Web.Controllers;

public sealed class PipelineController : Controller
{
    private readonly IPipelineArtifactsService _artifacts;
    private readonly MatePathsOptions _paths;
    private readonly ILogger<PipelineController> _logger;
    private readonly string _mateRoot;

    public PipelineController(
        IPipelineArtifactsService artifacts,
        IOptions<MatePathsOptions> pathOptions,
        IWebHostEnvironment env,
        ILogger<PipelineController> logger)
    {
        _artifacts = artifacts;
        _paths = pathOptions.Value;
        _logger = logger;
        _mateRoot = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", ".."));
    }

    [HttpGet("/")]
    [HttpGet("pipeline")]
    public async Task<IActionResult> Index(CancellationToken cancellationToken)
    {
        var model = await _artifacts.GetHomeAsync(cancellationToken);
        return View(model);
    }

    [HttpGet("pipeline/run/{moduleName}/{runId}")]
    public async Task<IActionResult> Run(string moduleName, string runId, CancellationToken cancellationToken)
    {
        var model = await _artifacts.GetRunAsync(moduleName, runId, cancellationToken);
        if (model is null)
        {
            return NotFound();
        }

        return View(model);
    }

    [HttpGet("pipeline/artifact/{moduleName}/{runId}")]
    public IActionResult Artifact(string moduleName, string runId, [FromQuery] string path)
    {
        if (!_artifacts.TryGetArtifactPath(moduleName, runId, path, out var absolutePath))
        {
            return NotFound();
        }

        var ext = Path.GetExtension(absolutePath).ToLowerInvariant();
        var contentType = ext switch
        {
            ".json" => "application/json",
            ".log" or ".txt" or ".md" => "text/plain",
            ".png" => "image/png",
            ".jpg" or ".jpeg" => "image/jpeg",
            ".webp" => "image/webp",
            ".cs" => "text/plain",
            ".ts" => "text/plain",
            ".py" => "text/plain",
            ".mmd" => "text/plain",
            _ => "application/octet-stream"
        };

        if (contentType.StartsWith("text/", StringComparison.OrdinalIgnoreCase) || contentType == "application/json")
        {
            var text = System.IO.File.ReadAllText(absolutePath, Encoding.UTF8);
            return Content(text, contentType, Encoding.UTF8);
        }

        var bytes = System.IO.File.ReadAllBytes(absolutePath);
        return File(bytes, contentType);
    }

    [HttpGet("pipeline/input")]
    public IActionResult Input()
    {
        var model = new MateRunInputModel();
        ViewData["GeneratedJson"] = BuildPreviewJson(model);
        return View(model);
    }

    [HttpPost("pipeline/input")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Input(MateRunInputModel model, string submitAction, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            ViewData["GeneratedJson"] = BuildPreviewJson(model);
            return View(model);
        }

        EnsureRunInputDefaults(model);

        if (string.Equals(submitAction, "preview", StringComparison.OrdinalIgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(model.RunId))
            {
                model.RunId = $"run-{DateTime.UtcNow:yyyyMMdd-HHmmss}";
            }

            ViewData["GeneratedJson"] = BuildPreviewJson(model);
            return View(model);
        }

        var runId = string.IsNullOrWhiteSpace(model.RunId)
            ? $"run-{DateTime.UtcNow:yyyyMMdd-HHmmss}"
            : model.RunId.Trim();
        model.RunId = runId;

        var path = await _artifacts.SaveRunInputAsync(model, cancellationToken);
        TempData["SavedRunInput"] = path;

        // Invoke orchestrator in background to execute skills
        _ = Task.Run(() => InvokeOrchestratorAsync(path, _paths, _mateRoot, _logger), CancellationToken.None);

        return RedirectToAction(nameof(Run), new { moduleName = model.ModuleName, runId = runId });
    }

    private static async Task InvokeOrchestratorAsync(
        string inputPath,
        MatePathsOptions paths,
        string mateRoot,
        ILogger logger)
    {
        try
        {
            var skillsRoot = EnforceMateRootPath(paths.SkillsRoot, mateRoot, "skills");
            var artifactsRoot = EnforceMateRootPath(paths.ArtifactsRoot, mateRoot, "artifacts");
            var orchestratorScript = Path.Combine(skillsRoot, "orchestrator", "run.py");
            if (!System.IO.File.Exists(orchestratorScript))
            {
                logger.LogError("Orchestrator script not found at {OrchestratorScript}", orchestratorScript);
                return;
            }

            var workingDirectory = mateRoot;
            logger.LogInformation(
                "Invoking orchestrator with input={InputPath}, skillsRoot={SkillsRoot}, artifactsRoot={ArtifactsRoot}, workingDirectory={WorkingDirectory}",
                inputPath,
                skillsRoot,
                artifactsRoot,
                workingDirectory);

            var processInfo = new System.Diagnostics.ProcessStartInfo
            {
                FileName = "python3",
                Arguments = $"\"{orchestratorScript}\" --input \"{inputPath}\" --artifacts-root \"{artifactsRoot}\" --skills-root \"{skillsRoot}\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                WorkingDirectory = workingDirectory
            };

            using var process = System.Diagnostics.Process.Start(processInfo);
            if (process is not null)
            {
                var stdOut = await process.StandardOutput.ReadToEndAsync();
                var stdErr = await process.StandardError.ReadToEndAsync();
                await process.WaitForExitAsync();

                logger.LogInformation("Orchestrator exited with code {ExitCode}", process.ExitCode);
                if (!string.IsNullOrWhiteSpace(stdOut))
                {
                    logger.LogInformation("Orchestrator stdout: {StdOut}", stdOut);
                }

                if (!string.IsNullOrWhiteSpace(stdErr))
                {
                    logger.LogWarning("Orchestrator stderr: {StdErr}", stdErr);
                }
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Orchestrator invocation failed.");
        }
    }

    private static string EnforceMateRootPath(string configuredPath, string mateRoot, string expectedLeaf)
    {
        var expected = Path.GetFullPath(Path.Combine(mateRoot, expectedLeaf));
        var actual = string.IsNullOrWhiteSpace(configuredPath)
            ? expected
            : Path.GetFullPath(configuredPath);

        if (!string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException(
                $"Invalid path for '{expectedLeaf}'. Expected '{expected}', but got '{actual}'. " +
                "This dashboard is locked to MATE-only paths.");
        }

        return actual;
    }

    private static void EnsureRunInputDefaults(MateRunInputModel model)
    {
        model.WorkflowNames ??= Array.Empty<string>();
        model.ConvertedRoots ??= Array.Empty<string>();
        model.LegacyBackendRoots ??= Array.Empty<string>();
        model.LegacyFrontendRoots ??= Array.Empty<string>();
        model.ControllerHints ??= Array.Empty<string>();
        model.ViewHints ??= Array.Empty<string>();
        model.Keywords ??= Array.Empty<string>();
        model.ExpectedEndUrls ??= Array.Empty<string>();
        model.RelatedFolders ??= Array.Empty<string>();
        model.KnownUrls ??= Array.Empty<string>();
    }

    private static string BuildPreviewJson(MateRunInputModel model)
    {
        EnsureRunInputDefaults(model);
        return JsonSerializer.Serialize(model, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });
    }
}
