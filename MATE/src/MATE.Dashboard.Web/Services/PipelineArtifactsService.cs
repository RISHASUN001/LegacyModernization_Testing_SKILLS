using System.Text.Json;
using MATE.Dashboard.Web.Models.Pipeline;
using MATE.Dashboard.Web.Options;
using Microsoft.Extensions.Options;

namespace MATE.Dashboard.Web.Services;

public class PipelineArtifactsService : IPipelineArtifactsService
{
    private readonly string _artifactsRoot;
    private readonly string _runInputsRoot;
    private readonly string _mateRoot;
    private readonly ILogger<PipelineArtifactsService> _logger;

    public PipelineArtifactsService(
        IWebHostEnvironment env,
        IOptions<MatePathsOptions> pathOptions,
        ILogger<PipelineArtifactsService> logger)
    {
        _logger = logger;

        _mateRoot = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", ".."));
        var configured = pathOptions.Value;

        _artifactsRoot = ResolveMatePath(configured.ArtifactsRoot, _mateRoot, "artifacts");
        _runInputsRoot = ResolveMatePath(configured.RunInputsRoot, _mateRoot, "run-inputs");

        Directory.CreateDirectory(_artifactsRoot);
        Directory.CreateDirectory(_runInputsRoot);

        _logger.LogInformation(
            "Pipeline artifacts service initialized with mateRoot={MateRoot}, artifactsRoot={ArtifactsRoot}, runInputsRoot={RunInputsRoot}",
            _mateRoot,
            _artifactsRoot,
            _runInputsRoot);
    }

    public Task<PipelineHomeDto> GetHomeAsync(CancellationToken cancellationToken)
    {
        var dto = new PipelineHomeDto();

        if (!Directory.Exists(_artifactsRoot))
        {
            return Task.FromResult(dto);
        }

        try
        {
            foreach (var moduleDir in Directory.GetDirectories(_artifactsRoot))
            {
                var moduleName = Path.GetFileName(moduleDir);
                var runDirs = Directory.GetDirectories(moduleDir)
                    .Select(path => new DirectoryInfo(path))
                    .ToList();

                if (runDirs.Count == 0)
                {
                    continue;
                }

                var latestRun = runDirs
                    .OrderByDescending(GetRunSortTime)
                    .First();

                var latestSummary = TryReadOrchestrationSummary(latestRun.FullName);

                dto.Modules.Add(new ModuleRunSummaryDto
                {
                    ModuleName = moduleName,
                    RunCount = runDirs.Count,
                    LatestRunId = latestRun.Name,
                    LatestStatus = latestSummary?.Status ?? "unknown",
                    LatestEndedAt = latestSummary?.EndedAt ?? latestRun.LastWriteTimeUtc.ToString("u")
                });
            }

            dto.Modules = dto.Modules
                .OrderByDescending(x => x.RunCount)
                .ThenBy(x => x.ModuleName, StringComparer.OrdinalIgnoreCase)
                .ToList();

            dto.TotalRuns = dto.Modules.Sum(m => m.RunCount);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error loading pipeline home data from {ArtifactsRoot}", _artifactsRoot);
        }

        return Task.FromResult(dto);
    }

    public Task<PipelineRunDto?> GetRunAsync(string moduleName, string runId, CancellationToken cancellationToken)
    {
        var runRoot = Path.Combine(_artifactsRoot, moduleName, runId);
        if (!Directory.Exists(runRoot))
        {
            return Task.FromResult<PipelineRunDto?>(null);
        }

        var dto = new PipelineRunDto
        {
            ModuleName = moduleName,
            RunId = runId
        };

        try
        {
            var summary = TryReadOrchestrationSummary(runRoot);
            if (summary is not null)
            {
                dto.Status = summary.Status;
                dto.Summary = summary.Summary;
                dto.StartedAt = summary.StartedAt;
                dto.EndedAt = summary.EndedAt;

                foreach (var stage in summary.Stages)
                {
                    var stageDto = new StageStatusDto
                    {
                        StageIndex = stage.StageIndex,
                        StageId = stage.Stage,
                        StageTitle = stage.StageTitle,
                        StageObjective = stage.StageObjective,
                        Status = stage.Status
                    };

                    foreach (var skill in stage.Skills)
                    {
                        var skillDto = new SkillResultDto
                        {
                            SkillName = skill.Skill,
                            Status = skill.Status,
                            Summary = skill.Summary,
                            ReturnCode = skill.ReturnCode,
                            Reused = skill.Reused,
                            StdErr = skill.Stderr,
                            Metrics = skill.Metrics
                        };

                        foreach (var rawArtifact in skill.Artifacts)
                        {
                            var relative = NormalizeArtifactPath(rawArtifact, moduleName, runId, runRoot);
                            if (string.IsNullOrWhiteSpace(relative))
                            {
                                continue;
                            }

                            var fullPath = Path.Combine(runRoot, relative);
                            skillDto.ArtifactPaths.Add(relative);
                            skillDto.Artifacts.Add(new ArtifactDto
                            {
                                Name = Path.GetFileName(relative),
                                RelativePath = relative.Replace('\\', '/'),
                                Kind = GetArtifactKind(relative),
                                Exists = File.Exists(fullPath)
                            });
                        }

                        stageDto.Skills.Add(skillDto);
                    }

                    dto.StageStatuses.Add(stageDto);
                }
            }
            else
            {
                // Fallback for older runs without orchestration-summary.json.
                BuildFallbackRunModel(dto, runRoot, moduleName, runId);
            }

            if (string.IsNullOrWhiteSpace(dto.Status))
            {
                dto.Status = AggregateStatus(dto.StageStatuses.Select(x => x.Status));
            }

            if (string.IsNullOrWhiteSpace(dto.Summary))
            {
                dto.Summary = $"Pipeline run for {moduleName}: {dto.StageStatuses.Count} stages";
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error loading run {RunId} for module {ModuleName}", runId, moduleName);
            dto.Status = "error";
            dto.Summary = "Failed to load orchestration artifacts for this run.";
        }

        return Task.FromResult<PipelineRunDto?>(dto);
    }

    public async Task<string> SaveRunInputAsync(MateRunInputModel model, CancellationToken cancellationToken)
    {
        var timestamp = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss");
        var filename = $"run-input.{model.ModuleName}.{timestamp}.json";
        var filepath = Path.Combine(_runInputsRoot, filename);

        var json = JsonSerializer.Serialize(model, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });
        await File.WriteAllTextAsync(filepath, json, cancellationToken);

        _logger.LogInformation("Saved run input to {Path}", filepath);
        return filepath;
    }

    public bool TryGetArtifactPath(string moduleName, string runId, string path, out string absolutePath)
    {
        absolutePath = string.Empty;

        if (string.IsNullOrWhiteSpace(path))
        {
            return false;
        }

        if (path.Contains("..", StringComparison.Ordinal) || path.StartsWith("/", StringComparison.Ordinal) || path.StartsWith("\\", StringComparison.Ordinal))
        {
            return false;
        }

        var runRoot = Path.GetFullPath(Path.Combine(_artifactsRoot, moduleName, runId));
        var combined = Path.Combine(runRoot, path.Replace('/', Path.DirectorySeparatorChar));
        var canonical = Path.GetFullPath(combined);

        if (!canonical.StartsWith(runRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) &&
            !string.Equals(canonical, runRoot, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        if (!File.Exists(canonical))
        {
            return false;
        }

        absolutePath = canonical;
        return true;
    }

    private static string ResolveMatePath(string configuredPath, string mateRoot, string expectedLeaf)
    {
        var expected = Path.GetFullPath(Path.Combine(mateRoot, expectedLeaf));
        var actual = string.IsNullOrWhiteSpace(configuredPath)
            ? expected
            : Path.GetFullPath(configuredPath);

        if (!string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException(
                $"Invalid MATE path for '{expectedLeaf}'. Expected '{expected}', but got '{actual}'.");
        }

        return actual;
    }

    private DateTime GetRunSortTime(DirectoryInfo runDir)
    {
        var summary = TryReadOrchestrationSummary(runDir.FullName);
        if (summary is not null && DateTime.TryParse(summary.EndedAt, out var endedAt))
        {
            return endedAt;
        }

        return runDir.LastWriteTimeUtc;
    }

    private static string AggregateStatus(IEnumerable<string> statuses)
    {
        var normalized = statuses
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Select(s => s.Trim().ToLowerInvariant())
            .ToList();

        if (normalized.Any(s => s == "failed" || s == "error"))
        {
            return "failed";
        }

        if (normalized.Any(s => s == "in-progress" || s == "running"))
        {
            return "in-progress";
        }

        if (normalized.All(s => s == "passed") && normalized.Count > 0)
        {
            return "passed";
        }

        return "unknown";
    }

    private void BuildFallbackRunModel(PipelineRunDto dto, string runRoot, string moduleName, string runId)
    {
        var stageContextFiles = Directory
            .GetFiles(Path.Combine(runRoot, "orchestration"), "stage-*-context.json", SearchOption.TopDirectoryOnly)
            .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
            .ToList();

        foreach (var contextFile in stageContextFiles)
        {
            using var contextDoc = JsonDocument.Parse(File.ReadAllText(contextFile));
            var root = contextDoc.RootElement;

            var stageDto = new StageStatusDto
            {
                StageIndex = root.TryGetProperty("stageIndex", out var idxEl) && idxEl.TryGetInt32(out var idx) ? idx : 0,
                StageId = root.TryGetProperty("stage", out var stageEl) ? stageEl.GetString() ?? string.Empty : string.Empty,
                StageTitle = root.TryGetProperty("title", out var titleEl) ? titleEl.GetString() ?? string.Empty : string.Empty,
                StageObjective = root.TryGetProperty("objective", out var objEl) ? objEl.GetString() ?? string.Empty : string.Empty,
                Status = "unknown"
            };

            if (root.TryGetProperty("contracts", out var contractsEl) && contractsEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var contract in contractsEl.EnumerateArray())
                {
                    if (!contract.TryGetProperty("skill", out var skillEl))
                    {
                        continue;
                    }

                    var skillName = skillEl.GetString() ?? string.Empty;
                    var resultFile = Path.Combine(runRoot, skillName, "result.json");
                    var skillDto = LoadSkillFromResultFile(resultFile, skillName, moduleName, runId, runRoot);
                    stageDto.Skills.Add(skillDto);
                }
            }

            stageDto.Status = AggregateStatus(stageDto.Skills.Select(s => s.Status));
            dto.StageStatuses.Add(stageDto);
        }

        dto.StartedAt = string.Empty;
        dto.EndedAt = Directory.GetLastWriteTimeUtc(runRoot).ToString("u");
        dto.Status = AggregateStatus(dto.StageStatuses.Select(x => x.Status));
    }

    private SkillResultDto LoadSkillFromResultFile(string resultFile, string skillName, string moduleName, string runId, string runRoot)
    {
        var dto = new SkillResultDto
        {
            SkillName = skillName,
            Status = "pending"
        };

        if (!File.Exists(resultFile))
        {
            return dto;
        }

        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(resultFile));
            var root = doc.RootElement;

            dto.Status = root.TryGetProperty("status", out var statusEl) ? statusEl.GetString() ?? "unknown" : "unknown";
            dto.Summary = root.TryGetProperty("summary", out var summaryEl) ? summaryEl.GetString() ?? string.Empty : string.Empty;
            dto.ReturnCode = 0;

            if (root.TryGetProperty("metrics", out var metricsEl) && metricsEl.ValueKind == JsonValueKind.Object)
            {
                foreach (var prop in metricsEl.EnumerateObject())
                {
                    dto.Metrics[prop.Name] = ToMetricValue(prop.Value);
                }
            }

            if (root.TryGetProperty("artifacts", out var artifactsEl) && artifactsEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var artifact in artifactsEl.EnumerateArray())
                {
                    if (artifact.ValueKind != JsonValueKind.String)
                    {
                        continue;
                    }

                    var relative = NormalizeArtifactPath(artifact.GetString() ?? string.Empty, moduleName, runId, runRoot);
                    if (string.IsNullOrWhiteSpace(relative))
                    {
                        continue;
                    }

                    var fullPath = Path.Combine(runRoot, relative);
                    dto.ArtifactPaths.Add(relative);
                    dto.Artifacts.Add(new ArtifactDto
                    {
                        Name = Path.GetFileName(relative),
                        RelativePath = relative.Replace('\\', '/'),
                        Kind = GetArtifactKind(relative),
                        Exists = File.Exists(fullPath)
                    });
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Could not parse skill result file {ResultFile}", resultFile);
        }

        return dto;
    }

    private OrchestrationSummary? TryReadOrchestrationSummary(string runRoot)
    {
        var summaryPath = Path.Combine(runRoot, "orchestration-summary.json");
        if (!File.Exists(summaryPath))
        {
            return null;
        }

        try
        {
            var json = File.ReadAllText(summaryPath);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            var summary = new OrchestrationSummary
            {
                Status = root.TryGetProperty("status", out var statusEl) ? statusEl.GetString() ?? "unknown" : "unknown",
                Summary = root.TryGetProperty("summary", out var summaryEl) ? summaryEl.GetString() ?? string.Empty : string.Empty,
                StartedAt = root.TryGetProperty("startedAt", out var startEl) ? startEl.GetString() ?? string.Empty : string.Empty,
                EndedAt = root.TryGetProperty("endedAt", out var endEl) ? endEl.GetString() ?? string.Empty : string.Empty
            };

            if (root.TryGetProperty("stages", out var stagesEl) && stagesEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var stageEl in stagesEl.EnumerateArray())
                {
                    var stage = new OrchestrationStage
                    {
                        Stage = stageEl.TryGetProperty("stage", out var stageNameEl) ? stageNameEl.GetString() ?? string.Empty : string.Empty,
                        StageIndex = stageEl.TryGetProperty("stageIndex", out var stageIndexEl) && stageIndexEl.TryGetInt32(out var idx) ? idx : 0,
                        StageTitle = stageEl.TryGetProperty("stageTitle", out var titleEl) ? titleEl.GetString() ?? string.Empty : string.Empty,
                        StageObjective = stageEl.TryGetProperty("stageObjective", out var objectiveEl) ? objectiveEl.GetString() ?? string.Empty : string.Empty,
                        Status = stageEl.TryGetProperty("status", out var stageStatusEl) ? stageStatusEl.GetString() ?? "unknown" : "unknown"
                    };

                    if (stageEl.TryGetProperty("skills", out var skillsEl) && skillsEl.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var skillEl in skillsEl.EnumerateArray())
                        {
                            var skill = new OrchestrationSkill
                            {
                                Skill = skillEl.TryGetProperty("skill", out var skillNameEl) ? skillNameEl.GetString() ?? string.Empty : string.Empty,
                                Status = skillEl.TryGetProperty("status", out var skillStatusEl) ? skillStatusEl.GetString() ?? "unknown" : "unknown",
                                Summary = skillEl.TryGetProperty("summary", out var skillSummaryEl) ? skillSummaryEl.GetString() ?? string.Empty : string.Empty,
                                Reused = skillEl.TryGetProperty("reused", out var reusedEl) && reusedEl.ValueKind == JsonValueKind.True,
                                ReturnCode = skillEl.TryGetProperty("returnCode", out var codeEl) && codeEl.TryGetInt32(out var code) ? code : 0,
                                Stderr = skillEl.TryGetProperty("stderr", out var stderrEl) ? stderrEl.GetString() ?? string.Empty : string.Empty
                            };

                            if (skillEl.TryGetProperty("metrics", out var metricsEl) && metricsEl.ValueKind == JsonValueKind.Object)
                            {
                                foreach (var metric in metricsEl.EnumerateObject())
                                {
                                    skill.Metrics[metric.Name] = ToMetricValue(metric.Value);
                                }
                            }

                            if (skillEl.TryGetProperty("artifacts", out var artifactsEl) && artifactsEl.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var artifactEl in artifactsEl.EnumerateArray())
                                {
                                    if (artifactEl.ValueKind == JsonValueKind.String)
                                    {
                                        skill.Artifacts.Add(artifactEl.GetString() ?? string.Empty);
                                    }
                                }
                            }

                            stage.Skills.Add(skill);
                        }
                    }

                    summary.Stages.Add(stage);
                }
            }

            return summary;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Unable to parse orchestration summary at {SummaryPath}", summaryPath);
            return null;
        }
    }

    private static object ToMetricValue(JsonElement element)
    {
        return element.ValueKind switch
        {
            JsonValueKind.Number when element.TryGetInt64(out var i) => i,
            JsonValueKind.Number when element.TryGetDouble(out var d) => d,
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.String => element.GetString() ?? string.Empty,
            _ => element.GetRawText()
        };
    }

    private static string NormalizeArtifactPath(string raw, string moduleName, string runId, string runRoot)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return string.Empty;
        }

        var normalized = raw.Replace('\\', '/').Trim();
        if (Path.IsPathRooted(normalized))
        {
            var runRootNormalized = Path.GetFullPath(runRoot).Replace('\\', '/').TrimEnd('/');
            var absoluteNormalized = Path.GetFullPath(normalized).Replace('\\', '/');
            if (absoluteNormalized.StartsWith(runRootNormalized + "/", StringComparison.OrdinalIgnoreCase))
            {
                return absoluteNormalized[(runRootNormalized.Length + 1)..];
            }

            return string.Empty;
        }

        var markers = new[]
        {
            $"MATE/artifacts/{moduleName}/{runId}/",
            $"artifacts/{moduleName}/{runId}/",
            $"/{moduleName}/{runId}/"
        };

        foreach (var marker in markers)
        {
            var idx = normalized.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (idx >= 0)
            {
                return normalized[(idx + marker.Length)..].TrimStart('/');
            }
        }

        return normalized.TrimStart('/');
    }

    private static string GetArtifactKind(string relativePath)
    {
        var ext = Path.GetExtension(relativePath).ToLowerInvariant();
        return ext switch
        {
            ".json" => "json",
            ".md" => "markdown",
            ".mmd" => "mermaid",
            ".png" or ".jpg" or ".jpeg" or ".webp" => "image",
            ".txt" or ".log" => "text",
            ".py" or ".cs" or ".js" => "code",
            _ => "other"
        };
    }

    private sealed class OrchestrationSummary
    {
        public string Status { get; set; } = "unknown";
        public string Summary { get; set; } = string.Empty;
        public string StartedAt { get; set; } = string.Empty;
        public string EndedAt { get; set; } = string.Empty;
        public List<OrchestrationStage> Stages { get; set; } = new();
    }

    private sealed class OrchestrationStage
    {
        public string Stage { get; set; } = string.Empty;
        public int StageIndex { get; set; }
        public string StageTitle { get; set; } = string.Empty;
        public string StageObjective { get; set; } = string.Empty;
        public string Status { get; set; } = "unknown";
        public List<OrchestrationSkill> Skills { get; set; } = new();
    }

    private sealed class OrchestrationSkill
    {
        public string Skill { get; set; } = string.Empty;
        public string Status { get; set; } = "unknown";
        public string Summary { get; set; } = string.Empty;
        public int ReturnCode { get; set; }
        public bool Reused { get; set; }
        public string Stderr { get; set; } = string.Empty;
        public Dictionary<string, object> Metrics { get; set; } = new();
        public List<string> Artifacts { get; set; } = new();
    }
}
