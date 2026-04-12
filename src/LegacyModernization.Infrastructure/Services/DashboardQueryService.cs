using System.Text.Json;
using System.Text.Json.Nodes;
using LegacyModernization.Application.Contracts;
using LegacyModernization.Application.DTOs;
using LegacyModernization.Infrastructure.Options;
using Microsoft.Extensions.Options;

namespace LegacyModernization.Infrastructure.Services;

public sealed class DashboardQueryService : IDashboardQueryService
{
    private static readonly string[] StageOrder =
    [
        "discovery",
        "logic-understanding",
        "architecture-review",
        "test-plan",
        "execution",
        "findings",
        "iteration-comparison"
    ];

    private static readonly Dictionary<string, string> StageTitleMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["discovery"] = "Discovery",
        ["logic-understanding"] = "Logic Understanding",
        ["architecture-review"] = "Architecture Review",
        ["test-plan"] = "Test Plan",
        ["execution"] = "Execution",
        ["findings"] = "Findings",
        ["iteration-comparison"] = "Iteration Comparison"
    };

    private readonly SqliteCli _sqlite;
    private readonly PlatformPathsOptions _paths;

    public DashboardQueryService(SqliteCli sqlite, IOptions<PlatformPathsOptions> options)
    {
        _sqlite = sqlite;
        _paths = options.Value;
    }

    public async Task<HomePageDto> GetHomePageAsync(CancellationToken cancellationToken = default)
    {
        var moduleRows = await QueryRowsAsync(@"
SELECT
    m.name,
    COUNT(r.id) AS total_runs,
    COALESCE((SELECT r2.run_id FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), '') AS last_run_id,
    COALESCE((SELECT r2.status FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), 'unknown') AS last_status,
    COALESCE((SELECT r2.ended_at FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), '') AS last_updated_at
FROM modules m
LEFT JOIN runs r ON r.module_id = m.id
GROUP BY m.id
ORDER BY m.name;", cancellationToken);

        var latestRuns = await QueryRowsAsync(@"
SELECT m.name AS module_name, r.run_id, r.status, r.started_at, r.ended_at, r.summary
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
ORDER BY r.started_at DESC
LIMIT 20;", cancellationToken);

        var statsRows = await QueryRowsAsync(@"
SELECT
    COUNT(*) AS total_runs,
    SUM(CASE WHEN LOWER(status)='passed' THEN 1 ELSE 0 END) AS passed_runs,
    SUM(CASE WHEN LOWER(status)='failed' THEN 1 ELSE 0 END) AS failed_runs
FROM runs;", cancellationToken);

        var stats = statsRows.FirstOrDefault();

        return new HomePageDto
        {
            Modules = moduleRows.Select(static row => new ModuleSummaryDto
            {
                Name = row.GetString("name"),
                TotalRuns = row.GetInt("total_runs"),
                LastRunId = row.GetString("last_run_id"),
                LastStatus = row.GetString("last_status"),
                LastUpdatedAt = row.GetString("last_updated_at")
            }).ToList(),
            LatestRuns = latestRuns.Select(static row => new RunSummaryDto
            {
                ModuleName = row.GetString("module_name"),
                RunId = row.GetString("run_id"),
                Status = row.GetString("status"),
                StartedAt = row.GetString("started_at"),
                EndedAt = row.GetString("ended_at"),
                Summary = row.GetString("summary")
            }).ToList(),
            TotalRuns = stats?.GetInt("total_runs") ?? 0,
            PassedRuns = stats?.GetInt("passed_runs") ?? 0,
            FailedRuns = stats?.GetInt("failed_runs") ?? 0
        };
    }

    public async Task<SkillLibraryPageDto> GetSkillLibraryAsync(CancellationToken cancellationToken = default)
    {
        var rows = await QueryRowsAsync(@"
SELECT name, stage, category, purpose, script_entry, summary_output_type, result_contract_version,
required_inputs_json, optional_inputs_json, output_files_json, artifact_folders_json, dependencies_json, skill_markdown
FROM skills
ORDER BY CASE stage
    WHEN 'discovery' THEN 1
    WHEN 'logic-understanding' THEN 2
    WHEN 'architecture-review' THEN 3
    WHEN 'test-plan' THEN 4
    WHEN 'execution' THEN 5
    WHEN 'findings' THEN 6
    WHEN 'iteration-comparison' THEN 7
    ELSE 99
END, name;", cancellationToken);

        return new SkillLibraryPageDto
        {
            Skills = rows.Select(static row => new SkillLibraryItemDto
            {
                Name = row.GetString("name"),
                Stage = row.GetString("stage"),
                Category = row.GetString("category"),
                Purpose = row.GetString("purpose"),
                ScriptEntry = row.GetString("script_entry"),
                SummaryOutputType = row.GetString("summary_output_type"),
                ResultContractVersion = row.GetString("result_contract_version"),
                RequiredInputs = ParseStringArray(row.GetString("required_inputs_json")),
                OptionalInputs = ParseStringArray(row.GetString("optional_inputs_json")),
                OutputFiles = ParseStringArray(row.GetString("output_files_json")),
                ArtifactFolders = ParseStringArray(row.GetString("artifact_folders_json")),
                Dependencies = ParseStringArray(row.GetString("dependencies_json")),
                SkillMarkdown = row.GetString("skill_markdown")
            }).ToList()
        };
    }

    public async Task<RunInputBuilderPageDto> GetRunInputBuilderAsync(CancellationToken cancellationToken = default)
    {
        var skills = await QueryRowsAsync("SELECT name FROM skills ORDER BY name;", cancellationToken);
        var skillNames = skills.Select(static s => s.GetString("name")).Where(static s => !string.IsNullOrWhiteSpace(s)).ToList();
        var draft = new RunInputDraftDto
        {
            SelectedSkills = skillNames
        };

        return new RunInputBuilderPageDto
        {
            Draft = draft,
            AvailableSkills = skillNames,
            GeneratedJson = BuildRunInputJson(draft)
        };
    }

    public async Task<string> SaveRunInputAsync(RunInputDraftDto draft, CancellationToken cancellationToken = default)
    {
        var json = BuildRunInputJson(draft);
        var safeModule = string.IsNullOrWhiteSpace(draft.ModuleName) ? "module" : draft.ModuleName.Trim();
        var safeRun = string.IsNullOrWhiteSpace(draft.RunId) ? DateTime.UtcNow.ToString("yyyyMMddHHmmss") : draft.RunId.Trim();
        var path = Path.Combine(_paths.RunInputsRoot, $"module-run-input.{safeModule}.{safeRun}.json");
        Directory.CreateDirectory(_paths.RunInputsRoot);
        await File.WriteAllTextAsync(path, json, cancellationToken);
        return path;
    }

    public async Task<ModuleRunsPageDto> GetModuleRunsAsync(string? moduleName, CancellationToken cancellationToken = default)
    {
        var filterSql = string.IsNullOrWhiteSpace(moduleName)
            ? string.Empty
            : $"WHERE m.name='{SqliteCli.Escape(moduleName)}'";

        var runs = await QueryRowsAsync($@"
SELECT m.name AS module_name, r.run_id, r.status, r.started_at, r.ended_at, r.summary
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
{filterSql}
ORDER BY r.started_at DESC;", cancellationToken);

        return new ModuleRunsPageDto
        {
            ModuleFilter = moduleName,
            Runs = runs.Select(static r => new RunSummaryDto
            {
                ModuleName = r.GetString("module_name"),
                RunId = r.GetString("run_id"),
                Status = r.GetString("status"),
                StartedAt = r.GetString("started_at"),
                EndedAt = r.GetString("ended_at"),
                Summary = r.GetString("summary")
            }).ToList()
        };
    }

    public async Task<RunPipelinePageDto?> GetRunPipelineAsync(string moduleName, string runId, CancellationToken cancellationToken = default)
    {
        var runRow = await GetRunRowAsync(moduleName, runId, cancellationToken);
        if (runRow is null)
        {
            return null;
        }

        var runFk = runRow.GetLong("id");
        var artifactRoot = runRow.GetString("artifact_root");

        var stageRows = await QueryRowsAsync($@"
SELECT stage,
       COUNT(1) AS skill_count,
       SUM(CASE WHEN LOWER(status)='failed' THEN 1 ELSE 0 END) AS failed_skills
FROM skill_executions
WHERE run_fk={runFk}
GROUP BY stage;", cancellationToken);

        var stageLookup = stageRows.ToDictionary(static r => r.GetString("stage"), static r => r, StringComparer.OrdinalIgnoreCase);

        var stageStatuses = StageOrder.Select(stage =>
        {
            var found = stageLookup.GetValueOrDefault(stage);
            var failed = found?.GetInt("failed_skills") ?? 0;
            var count = found?.GetInt("skill_count") ?? 0;
            var status = count == 0 ? "unknown" : failed > 0 ? "failed" : "passed";
            return new StageStatusDto
            {
                StageId = stage,
                StageTitle = StageTitleMap.GetValueOrDefault(stage, stage),
                Status = status,
                SkillCount = count,
                FailedSkills = failed
            };
        }).ToList();

        var discovery = await BuildDiscoveryStageAsync(artifactRoot, cancellationToken);
        var logic = await BuildLogicStageAsync(artifactRoot, cancellationToken);
        var architecture = await BuildArchitectureStageAsync(artifactRoot, cancellationToken);
        var testPlan = await BuildTestPlanStageAsync(artifactRoot, cancellationToken);
        var execution = await BuildExecutionStageAsync(runFk, artifactRoot, cancellationToken);
        var findings = await BuildFindingsStageAsync(runFk, moduleName, runId, cancellationToken);
        var iteration = await BuildIterationSummaryAsync(moduleName, runId, artifactRoot, cancellationToken);

        return new RunPipelinePageDto
        {
            ModuleName = moduleName,
            RunId = runId,
            Status = runRow.GetString("status"),
            StartedAt = runRow.GetString("started_at"),
            EndedAt = runRow.GetString("ended_at"),
            Summary = runRow.GetString("summary"),
            StageStatuses = stageStatuses,
            Discovery = discovery,
            LogicUnderstanding = logic,
            ArchitectureReview = architecture,
            TestPlan = testPlan,
            Execution = execution,
            Findings = findings,
            IterationComparison = iteration
        };
    }

    public async Task<FindingsPageDto> GetFindingsAsync(string? moduleName, string? runId, CancellationToken cancellationToken = default)
    {
        var whereClauses = new List<string>();
        if (!string.IsNullOrWhiteSpace(moduleName))
        {
            whereClauses.Add($"m.name='{SqliteCli.Escape(moduleName)}'");
        }

        if (!string.IsNullOrWhiteSpace(runId))
        {
            whereClauses.Add($"r.run_id='{SqliteCli.Escape(runId)}'");
        }

        var whereSql = whereClauses.Count > 0 ? $"WHERE {string.Join(" AND ", whereClauses)}" : string.Empty;

        var findingRows = await QueryRowsAsync($@"
SELECT m.name AS module_name, r.run_id, f.stage, f.skill_name, f.scenario, f.issue_type, f.message,
       f.likely_cause, f.evidence, f.severity, f.status, f.confidence, f.resolved_in_run_id,
       f.resolution_notes, f.affected_files_json
FROM finding_records f
INNER JOIN runs r ON r.id = f.run_fk
INNER JOIN modules m ON m.id = r.module_id
{whereSql}
ORDER BY r.run_id DESC, f.id DESC;", cancellationToken);

        var recommendationRows = await QueryRowsAsync($@"
SELECT m.name AS module_name, r.run_id, rec.stage, rec.skill_name, rec.message, rec.priority, rec.evidence
FROM recommendation_records rec
INNER JOIN runs r ON r.id = rec.run_fk
INNER JOIN modules m ON m.id = r.module_id
{whereSql}
ORDER BY r.run_id DESC, rec.id DESC;", cancellationToken);

        return new FindingsPageDto
        {
            ModuleName = moduleName,
            RunId = runId,
            Findings = findingRows.Select(static row => new FindingDto
            {
                ModuleName = row.GetString("module_name"),
                RunId = row.GetString("run_id"),
                Stage = row.GetString("stage"),
                SkillName = row.GetString("skill_name"),
                Scenario = row.GetString("scenario"),
                FindingType = row.GetString("issue_type"),
                Message = row.GetString("message"),
                LikelyCause = row.GetString("likely_cause"),
                Evidence = row.GetString("evidence"),
                Severity = row.GetString("severity"),
                Status = row.GetString("status"),
                Confidence = row.GetDouble("confidence"),
                ResolvedInRunId = row.GetString("resolved_in_run_id"),
                ResolutionNotes = row.GetString("resolution_notes"),
                AffectedFiles = ParseStringArray(row.GetString("affected_files_json"))
            }).ToList(),
            Recommendations = recommendationRows.Select(static row => new RecommendationDto
            {
                ModuleName = row.GetString("module_name"),
                RunId = row.GetString("run_id"),
                Stage = row.GetString("stage"),
                SkillName = row.GetString("skill_name"),
                Message = row.GetString("message"),
                Priority = row.GetString("priority"),
                Evidence = row.GetString("evidence")
            }).ToList()
        };
    }

    public async Task<IterationComparisonPageDto?> GetIterationComparisonAsync(string moduleName, CancellationToken cancellationToken = default)
    {
        var rows = await QueryRowsAsync($@"
SELECT d.run_id, d.previous_run_id, d.tests_added, d.tests_fixed, d.failures_reduced,
       d.new_findings_introduced, d.resolved_findings, d.progression_trend
FROM iteration_deltas d
INNER JOIN modules m ON m.id = d.module_id
WHERE m.name='{SqliteCli.Escape(moduleName)}'
ORDER BY d.run_id;", cancellationToken);

        if (rows.Count == 0)
        {
            return null;
        }

        return new IterationComparisonPageDto
        {
            ModuleName = moduleName,
            Iterations = rows.Select(static row => new IterationPointDto
            {
                RunId = row.GetString("run_id"),
                PreviousRunId = row.GetString("previous_run_id"),
                TestsAdded = row.GetInt("tests_added"),
                TestsFixed = row.GetInt("tests_fixed"),
                FailuresReduced = row.GetInt("failures_reduced"),
                NewFindingsIntroduced = row.GetInt("new_findings_introduced"),
                ResolvedFindings = row.GetInt("resolved_findings"),
                ProgressionTrend = row.GetString("progression_trend")
            }).ToList()
        };
    }

    private async Task<DiscoveryStageDto> BuildDiscoveryStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(artifactRoot, "module-discovery", "discovery-map.json");
        if (!File.Exists(path))
        {
            return new DiscoveryStageDto { SourceArtifactPath = path };
        }

        var node = JsonNode.Parse(await File.ReadAllTextAsync(path, cancellationToken)) as JsonObject;
        if (node is null)
        {
            return new DiscoveryStageDto { SourceArtifactPath = path };
        }

        return new DiscoveryStageDto
        {
            JavaFiles = ParseStringArray(node["javaFiles"]?.ToJsonString() ?? "[]"),
            JspFiles = ParseStringArray(node["jspFiles"]?.ToJsonString() ?? "[]"),
            JsFiles = ParseStringArray(node["jsFiles"]?.ToJsonString() ?? "[]"),
            ConfigFiles = ParseStringArray(node["configFiles"]?.ToJsonString() ?? "[]"),
            Urls = ParseStringArray(node["urls"]?.ToJsonString() ?? "[]"),
            DbTouchpoints = ParseStringArray(node["dbTouchpoints"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = path
        };
    }

    private async Task<LogicUnderstandingStageDto> BuildLogicStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var docPath = Path.Combine(artifactRoot, "module-documentation", "module-analysis.json");
        var logicPath = Path.Combine(artifactRoot, "legacy-logic-extraction", "logic-summary.json");

        JsonObject? node = null;
        var sourcePath = docPath;

        if (File.Exists(docPath))
        {
            node = JsonNode.Parse(await File.ReadAllTextAsync(docPath, cancellationToken)) as JsonObject;
        }
        else if (File.Exists(logicPath))
        {
            sourcePath = logicPath;
            node = JsonNode.Parse(await File.ReadAllTextAsync(logicPath, cancellationToken)) as JsonObject;
        }

        if (node is null)
        {
            return new LogicUnderstandingStageDto { SourceArtifactPath = sourcePath };
        }

        return new LogicUnderstandingStageDto
        {
            ModulePurpose = node["modulePurpose"]?.GetValue<string>() ?? string.Empty,
            ImportantFlows = ParseStringArray(node["importantFlows"]?.ToJsonString() ?? node["userFlows"]?.ToJsonString() ?? "[]"),
            Rules = ParseStringArray(node["rules"]?.ToJsonString() ?? node["businessRules"]?.ToJsonString() ?? "[]"),
            Dependencies = ParseStringArray(node["dependencies"]?.ToJsonString() ?? "[]"),
            MustPreserve = ParseStringArray(node["mustPreserve"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = sourcePath
        };
    }

    private async Task<ArchitectureReviewStageDto> BuildArchitectureStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(artifactRoot, "clean-architecture-assessment", "architecture-review.json");
        if (!File.Exists(path))
        {
            return new ArchitectureReviewStageDto { SourceArtifactPath = path };
        }

        var node = JsonNode.Parse(await File.ReadAllTextAsync(path, cancellationToken)) as JsonObject;
        if (node is null)
        {
            return new ArchitectureReviewStageDto { SourceArtifactPath = path };
        }

        return new ArchitectureReviewStageDto
        {
            CleanArchitectureIssues = ParseArchitectureIssues(node["cleanArchitectureIssues"]),
            NamespaceFolderIssues = ParseArchitectureIssues(node["namespaceFolderIssues"]),
            DiIssues = ParseArchitectureIssues(node["diIssues"]),
            CouplingIssues = ParseArchitectureIssues(node["couplingIssues"]),
            RecommendedStructure = ParseStringArray(node["recommendedStructure"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = path
        };
    }

    private async Task<TestPlanStageDto> BuildTestPlanStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(artifactRoot, "test-plan-generation", "test-plan.json");
        if (!File.Exists(path))
        {
            return new TestPlanStageDto { SourceArtifactPath = path };
        }

        var node = JsonNode.Parse(await File.ReadAllTextAsync(path, cancellationToken)) as JsonObject;
        if (node is null)
        {
            return new TestPlanStageDto { SourceArtifactPath = path };
        }

        var categoryItems = new List<TestCategoryPlanDto>();
        if (node["testCategories"] is JsonArray categories)
        {
            foreach (var item in categories)
            {
                var obj = item as JsonObject;
                if (obj is null)
                {
                    continue;
                }

                categoryItems.Add(new TestCategoryPlanDto
                {
                    Category = obj["category"]?.GetValue<string>() ?? string.Empty,
                    Purpose = obj["purpose"]?.GetValue<string>() ?? string.Empty
                });
            }
        }

        return new TestPlanStageDto
        {
            ExistingTestsFound = ParseStringArray(node["existingTestsFound"]?.ToJsonString() ?? "[]"),
            NewTestsSuggested = ParseStringArray(node["newTestsSuggested"]?.ToJsonString() ?? "[]"),
            TestCategories = categoryItems,
            CoverageSummary = node["coverageSummary"]?.GetValue<string>() ?? string.Empty,
            SourceArtifactPath = path
        };
    }

    private async Task<ExecutionStageDto> BuildExecutionStageAsync(long runFk, string artifactRoot, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync($@"
SELECT category, purpose, scenarios_json, total, passed, failed, warnings, new_tests_added,
       logs_json, artifacts_json, source_skill, stage
FROM test_category_results
WHERE run_fk={runFk}
ORDER BY CASE category
    WHEN 'Unit' THEN 1
    WHEN 'Integration' THEN 2
    WHEN 'E2E' THEN 3
    WHEN 'API' THEN 4
    WHEN 'Edge Case' THEN 5
    WHEN 'Playwright / Browser Verification' THEN 6
    ELSE 99
END;", cancellationToken);

        var categories = rows.Select(static row => new TestCategoryExecutionDto
        {
            Category = row.GetString("category"),
            Purpose = row.GetString("purpose"),
            ScenariosCovered = ParseStringArray(row.GetString("scenarios_json")),
            TotalCount = row.GetInt("total"),
            Passed = row.GetInt("passed"),
            Failed = row.GetInt("failed"),
            Warnings = row.GetInt("warnings"),
            NewTestsAdded = row.GetInt("new_tests_added"),
            SourceSkill = row.GetString("source_skill"),
            Logs = ParseStringArray(row.GetString("logs_json")),
            Artifacts = ParseStringArray(row.GetString("artifacts_json"))
        }).ToList();

        var playwright = await BuildPlaywrightEvidenceAsync(runFk, artifactRoot, cancellationToken);

        return new ExecutionStageDto
        {
            TestCategories = categories,
            Playwright = playwright
        };
    }

    private async Task<PlaywrightEvidenceDto> BuildPlaywrightEvidenceAsync(long runFk, string artifactRoot, CancellationToken cancellationToken)
    {
        var row = (await QueryRowsAsync($@"
SELECT status, summary, metrics_json, artifacts_json
FROM skill_executions
WHERE run_fk={runFk} AND skill_name='playwright-browser-verification'
LIMIT 1;", cancellationToken)).FirstOrDefault();

        if (row is null)
        {
            return new PlaywrightEvidenceDto();
        }

        var metrics = JsonNode.Parse(row.GetString("metrics_json")) as JsonObject;
        var scenarios = new List<PlaywrightScenarioDto>();
        if (metrics?["scenarios"] is JsonArray scenarioArray)
        {
            scenarios = scenarioArray
                .Select(static item => item as JsonObject)
                .Where(static item => item is not null)
                .Select(static item => new PlaywrightScenarioDto
                {
                    Name = item!["name"]?.GetValue<string>() ?? string.Empty,
                    Status = item["status"]?.GetValue<string>() ?? string.Empty,
                    Notes = item["notes"]?.GetValue<string>() ?? string.Empty
                })
                .ToList();
        }

        var consolePath = Path.Combine(artifactRoot, "playwright-browser-verification", "console-logs.json");
        var networkPath = Path.Combine(artifactRoot, "playwright-browser-verification", "network-failures.json");
        var domPath = Path.Combine(artifactRoot, "playwright-browser-verification", "dom-state.json");
        var runtimePath = Path.Combine(artifactRoot, "playwright-browser-verification", "runtime-issues.json");
        var perfPath = Path.Combine(artifactRoot, "playwright-browser-verification", "performance-observations.json");

        var screenshotRoot = Path.Combine(artifactRoot, "playwright-browser-verification", "screenshots");

        var consoleEntries = await ReadStringArrayFileAsync(consolePath, cancellationToken);
        var consoleErrors = consoleEntries.Where(static e => e.Contains("error", StringComparison.OrdinalIgnoreCase) || e.Contains("TypeError", StringComparison.OrdinalIgnoreCase)).ToList();
        var consoleWarnings = consoleEntries.Where(static e => e.Contains("warn", StringComparison.OrdinalIgnoreCase) || e.Contains("warning", StringComparison.OrdinalIgnoreCase)).ToList();

        return new PlaywrightEvidenceDto
        {
            Status = row.GetString("status"),
            Summary = row.GetString("summary"),
            Scenarios = scenarios,
            ConsoleErrors = consoleErrors,
            ConsoleWarnings = consoleWarnings,
            NetworkFailures = await ReadStringArrayFileAsync(networkPath, cancellationToken),
            DomStateChecks = await ReadStringArrayFileAsync(domPath, cancellationToken),
            RuntimeIssues = await ReadStringArrayFileAsync(runtimePath, cancellationToken),
            PerformanceObservations = await ReadStringArrayFileAsync(perfPath, cancellationToken),
            Screenshots = Directory.Exists(screenshotRoot)
                ? Directory.GetFiles(screenshotRoot).OrderBy(static p => p, StringComparer.OrdinalIgnoreCase).ToList()
                : [],
            ArtifactLinks = ParseStringArray(row.GetString("artifacts_json"))
        };
    }

    private async Task<FindingsStageDto> BuildFindingsStageAsync(long runFk, string moduleName, string runId, CancellationToken cancellationToken)
    {
        var findings = await QueryRowsAsync($@"
SELECT stage, skill_name, scenario, issue_type, message, likely_cause, evidence, severity, status,
       confidence, resolved_in_run_id, resolution_notes, affected_files_json
FROM finding_records
WHERE run_fk={runFk}
ORDER BY id DESC;", cancellationToken);

        var recommendations = await QueryRowsAsync($@"
SELECT stage, skill_name, message, priority, evidence
FROM recommendation_records
WHERE run_fk={runFk}
ORDER BY id DESC;", cancellationToken);

        return new FindingsStageDto
        {
            Findings = findings.Select(row => new FindingDto
            {
                ModuleName = moduleName,
                RunId = runId,
                Stage = row.GetString("stage"),
                SkillName = row.GetString("skill_name"),
                Scenario = row.GetString("scenario"),
                FindingType = row.GetString("issue_type"),
                Message = row.GetString("message"),
                LikelyCause = row.GetString("likely_cause"),
                Evidence = row.GetString("evidence"),
                Severity = row.GetString("severity"),
                Status = row.GetString("status"),
                Confidence = row.GetDouble("confidence"),
                ResolvedInRunId = row.GetString("resolved_in_run_id"),
                ResolutionNotes = row.GetString("resolution_notes"),
                AffectedFiles = ParseStringArray(row.GetString("affected_files_json"))
            }).ToList(),
            Recommendations = recommendations.Select(row => new RecommendationDto
            {
                ModuleName = moduleName,
                RunId = runId,
                Stage = row.GetString("stage"),
                SkillName = row.GetString("skill_name"),
                Message = row.GetString("message"),
                Priority = row.GetString("priority"),
                Evidence = row.GetString("evidence")
            }).ToList()
        };
    }

    private async Task<IterationComparisonSummaryDto> BuildIterationSummaryAsync(string moduleName, string runId, string artifactRoot, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync($@"
SELECT d.previous_run_id, d.tests_added, d.tests_fixed, d.failures_reduced,
       d.new_findings_introduced, d.resolved_findings, d.progression_trend
FROM iteration_deltas d
INNER JOIN modules m ON m.id = d.module_id
WHERE m.name='{SqliteCli.Escape(moduleName)}' AND d.run_id='{SqliteCli.Escape(runId)}'
LIMIT 1;", cancellationToken);

        var sourcePath = Path.Combine(artifactRoot, "iteration-comparison", "iteration-delta.json");

        var row = rows.FirstOrDefault();
        if (row is null)
        {
            return new IterationComparisonSummaryDto { SourceArtifactPath = sourcePath };
        }

        return new IterationComparisonSummaryDto
        {
            PreviousRunId = row.GetString("previous_run_id"),
            TestsAdded = row.GetInt("tests_added"),
            TestsFixed = row.GetInt("tests_fixed"),
            FailuresReduced = row.GetInt("failures_reduced"),
            NewFindingsIntroduced = row.GetInt("new_findings_introduced"),
            ResolvedFindings = row.GetInt("resolved_findings"),
            ProgressionTrend = row.GetString("progression_trend"),
            SourceArtifactPath = sourcePath
        };
    }

    private async Task<JsonObject?> GetRunRowAsync(string moduleName, string runId, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync($@"
SELECT r.id, r.artifact_root, r.status, r.summary, r.started_at, r.ended_at
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
WHERE m.name='{SqliteCli.Escape(moduleName)}' AND r.run_id='{SqliteCli.Escape(runId)}'
LIMIT 1;", cancellationToken);
        return rows.FirstOrDefault();
    }

    private string BuildRunInputJson(RunInputDraftDto draft)
    {
        var payload = new
        {
            runId = string.IsNullOrWhiteSpace(draft.RunId) ? "run-001" : draft.RunId.Trim(),
            moduleName = string.IsNullOrWhiteSpace(draft.ModuleName) ? "Checklist" : draft.ModuleName.Trim(),
            legacySourceRoot = draft.LegacySourceRoot.Trim(),
            convertedSourceRoot = draft.ConvertedSourceRoot.Trim(),
            baseUrl = draft.BaseUrl.Trim(),
            brsPath = draft.BrsPath.Trim(),
            moduleHints = new
            {
                relatedFolders = ParseMultiline(draft.RelatedFoldersText),
                knownUrls = ParseMultiline(draft.KnownUrlsText),
                keywords = ParseMultiline(draft.KeywordsText)
            },
            selectedSkills = (draft.SelectedSkills ?? []).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(static s => s).ToList()
        };

        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
    }

    private async Task<List<JsonObject>> QueryRowsAsync(string sql, CancellationToken cancellationToken)
    {
        var json = await _sqlite.ExecuteJsonQueryAsync(sql, cancellationToken);
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        var node = JsonNode.Parse(json) as JsonArray;
        if (node is null)
        {
            return [];
        }

        return node
            .Select(static item => item as JsonObject)
            .Where(static item => item is not null)
            .Select(static item => item!)
            .ToList();
    }

    private static List<string> ParseStringArray(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        try
        {
            var node = JsonNode.Parse(json) as JsonArray;
            if (node is null)
            {
                return [];
            }

            return node
                .Select(static item => item?.GetValue<string>() ?? string.Empty)
                .Where(static item => !string.IsNullOrWhiteSpace(item))
                .ToList();
        }
        catch
        {
            return [];
        }
    }

    private static List<string> ParseMultiline(string input)
    {
        return input
            .Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.RemoveEmptyEntries)
            .Select(static item => item.Trim())
            .Where(static item => !string.IsNullOrWhiteSpace(item))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static List<ArchitectureIssueDto> ParseArchitectureIssues(JsonNode? node)
    {
        if (node is not JsonArray array)
        {
            return [];
        }

        return array
            .Select(static item => item as JsonObject)
            .Where(static item => item is not null)
            .Select(static item => new ArchitectureIssueDto
            {
                Title = item!["title"]?.GetValue<string>() ?? string.Empty,
                Severity = item["severity"]?.GetValue<string>() ?? "medium",
                Evidence = item["evidence"]?.GetValue<string>() ?? string.Empty
            })
            .ToList();
    }

    private static async Task<List<string>> ReadStringArrayFileAsync(string path, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            return [];
        }

        var text = await File.ReadAllTextAsync(path, cancellationToken);
        if (string.IsNullOrWhiteSpace(text))
        {
            return [];
        }

        try
        {
            var node = JsonNode.Parse(text);
            if (node is JsonArray array)
            {
                return array
                    .Select(static item => item?.GetValue<string>() ?? string.Empty)
                    .Where(static item => !string.IsNullOrWhiteSpace(item))
                    .ToList();
            }

            return [text.Trim()];
        }
        catch
        {
            return [text.Trim()];
        }
    }
}

internal static class JsonRowExtensions
{
    public static string GetString(this JsonObject row, string key)
    {
        return row[key]?.GetValue<string>() ?? string.Empty;
    }

    public static int GetInt(this JsonObject row, string key)
    {
        var node = row[key];
        return node is null ? 0 : int.TryParse(node.ToString(), out var parsed) ? parsed : 0;
    }

    public static long GetLong(this JsonObject row, string key)
    {
        var node = row[key];
        return node is null ? 0 : long.TryParse(node.ToString(), out var parsed) ? parsed : 0;
    }

    public static double GetDouble(this JsonObject row, string key)
    {
        var node = row[key];
        return node is null ? 0 : double.TryParse(node.ToString(), out var parsed) ? parsed : 0;
    }
}
