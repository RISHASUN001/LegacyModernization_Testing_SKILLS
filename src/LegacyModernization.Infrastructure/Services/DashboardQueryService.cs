using System.Data;
using System.Text.Json;
using System.Text.Json.Nodes;
using Dapper;
using LegacyModernization.Application.Contracts;
using LegacyModernization.Application.DTOs;
using LegacyModernization.Infrastructure.Abstractions;
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

    private readonly ISqliteConnectionFactory _connectionFactory;
    private readonly PlatformPathsOptions _paths;

    public DashboardQueryService(ISqliteConnectionFactory connectionFactory, IOptions<PlatformPathsOptions> options)
    {
        _connectionFactory = connectionFactory;
        _paths = options.Value;
    }

    public async Task<HomePageDto> GetHomePageAsync(CancellationToken cancellationToken = default)
    {
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var moduleRows = await QueryRowsAsync(connection, @"
SELECT
    m.name,
    COUNT(r.id) AS total_runs,
    COALESCE((SELECT r2.run_id FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), '') AS last_run_id,
    COALESCE((SELECT r2.status FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), 'unknown') AS last_status,
    COALESCE((SELECT r2.ended_at FROM runs r2 WHERE r2.module_id = m.id ORDER BY r2.run_id DESC LIMIT 1), '') AS last_updated_at
FROM modules m
LEFT JOIN runs r ON r.module_id = m.id
GROUP BY m.id
ORDER BY m.name;", null, cancellationToken);

        var latestRuns = await QueryRowsAsync(connection, @"
SELECT m.name AS module_name, r.run_id, r.status, r.started_at, r.ended_at, r.summary
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
ORDER BY r.started_at DESC
LIMIT 20;", null, cancellationToken);

        var statsRows = await QueryRowsAsync(connection, @"
SELECT
    COUNT(*) AS total_runs,
    SUM(CASE WHEN LOWER(status)='passed' THEN 1 ELSE 0 END) AS passed_runs,
    SUM(CASE WHEN LOWER(status)='failed' THEN 1 ELSE 0 END) AS failed_runs
FROM runs;", null, cancellationToken);

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
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var rows = await QueryRowsAsync(connection, @"
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
END, name;", null, cancellationToken);

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
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var skills = await QueryRowsAsync(
            connection,
            "SELECT name FROM skills WHERE name <> 'legacy-modernization-orchestrator' ORDER BY name;",
            null,
            cancellationToken);
        var skillNames = skills.Select(static s => s.GetString("name")).Where(static s => !string.IsNullOrWhiteSpace(s)).ToList();
        var draft = new RunInputDraftDto { SelectedSkills = skillNames };

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
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        string sql;
        object? parameters;
        if (string.IsNullOrWhiteSpace(moduleName))
        {
            sql = @"
SELECT m.name AS module_name, r.run_id, r.status, r.started_at, r.ended_at, r.summary
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
ORDER BY r.started_at DESC;";
            parameters = null;
        }
        else
        {
            sql = @"
SELECT m.name AS module_name, r.run_id, r.status, r.started_at, r.ended_at, r.summary
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
WHERE m.name=@ModuleName
ORDER BY r.started_at DESC;";
            parameters = new { ModuleName = moduleName };
        }

        var runs = await QueryRowsAsync(connection, sql, parameters, cancellationToken);

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
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var runRow = await GetRunRowAsync(connection, moduleName, runId, cancellationToken);
        if (runRow is null)
        {
            return null;
        }

        var runFk = runRow.GetLong("id");
        var artifactRoot = runRow.GetString("artifact_root");

        var stageRows = await QueryRowsAsync(connection, @"
SELECT stage,
       COUNT(1) AS skill_count,
       SUM(CASE WHEN LOWER(status)='failed' THEN 1 ELSE 0 END) AS failed_skills
FROM skill_executions
WHERE run_fk=@RunFk
GROUP BY stage;", new { RunFk = runFk }, cancellationToken);

        var stageLookup = stageRows.ToDictionary(static r => r.GetString("stage"), static r => r, StringComparer.OrdinalIgnoreCase);

        var stageStatuses = StageOrder.Select(stage =>
        {
            stageLookup.TryGetValue(stage, out var found);
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
        var execution = await BuildExecutionStageAsync(connection, runFk, artifactRoot, cancellationToken);
        var parity = await BuildParityStageAsync(artifactRoot, cancellationToken);
        var findings = await BuildFindingsStageAsync(connection, runFk, moduleName, runId, cancellationToken);
        var keyLearnings = await BuildKeyLearningsAsync(artifactRoot, cancellationToken);
        var iteration = await BuildIterationSummaryAsync(connection, moduleName, runId, artifactRoot, cancellationToken);

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
            Parity = parity,
            Findings = findings,
            KeyLearnings = keyLearnings,
            IterationComparison = iteration
        };
    }

    public async Task<FindingsPageDto> GetFindingsAsync(string? moduleName, string? runId, CancellationToken cancellationToken = default)
    {
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var whereClauses = new List<string>();
        var parameters = new DynamicParameters();

        if (!string.IsNullOrWhiteSpace(moduleName))
        {
            whereClauses.Add("m.name=@ModuleName");
            parameters.Add("ModuleName", moduleName);
        }

        if (!string.IsNullOrWhiteSpace(runId))
        {
            whereClauses.Add("r.run_id=@RunId");
            parameters.Add("RunId", runId);
        }

        var whereSql = whereClauses.Count > 0 ? $"WHERE {string.Join(" AND ", whereClauses)}" : string.Empty;

        var findingRows = await QueryRowsAsync(connection, $@"
SELECT m.name AS module_name, r.run_id, f.stage, f.skill_name, f.scenario, f.issue_type, f.message,
       f.likely_cause, f.evidence, f.severity, f.status, f.confidence, f.resolved_in_run_id,
       f.resolution_notes, f.affected_files_json
FROM finding_records f
INNER JOIN runs r ON r.id = f.run_fk
INNER JOIN modules m ON m.id = r.module_id
{whereSql}
ORDER BY r.run_id DESC, f.id DESC;", parameters, cancellationToken);

        var recommendationRows = await QueryRowsAsync(connection, $@"
SELECT m.name AS module_name, r.run_id, rec.stage, rec.skill_name, rec.message, rec.priority, rec.evidence
FROM recommendation_records rec
INNER JOIN runs r ON r.id = rec.run_fk
INNER JOIN modules m ON m.id = r.module_id
{whereSql}
ORDER BY r.run_id DESC, rec.id DESC;", parameters, cancellationToken);

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
                ProvenanceType = "code-evidence",
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
                Evidence = row.GetString("evidence"),
                ProvenanceType = "code-evidence"
            }).ToList()
        };
    }

    public async Task<IterationComparisonPageDto?> GetIterationComparisonAsync(string moduleName, CancellationToken cancellationToken = default)
    {
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        var rows = await QueryRowsAsync(connection, @"
SELECT d.run_id, d.previous_run_id, d.tests_added, d.tests_fixed, d.failures_reduced,
       d.new_findings_introduced, d.resolved_findings, d.progression_trend
FROM iteration_deltas d
INNER JOIN modules m ON m.id = d.module_id
WHERE m.name=@ModuleName
ORDER BY d.run_id;", new { ModuleName = moduleName }, cancellationToken);

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
            UrlDetails = ParseRouteDetails(node["routeCandidates"]),
            DbTouchpointDetails = ParseNamedProvenancedDetails(node["dbTouchpointsDetailed"], "name"),
            EntrypointHints = ParseNamedProvenancedDetails(node["entrypointHints"], "value"),
            Confidence = ParseDouble(node["confidence"], 0),
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

        var modulePurpose = node["modulePurpose"] as JsonObject;
        var modulePurposeText = modulePurpose?["text"]?.GetValue<string>()
            ?? node["modulePurpose"]?.GetValue<string>()
            ?? node["modulePurposeText"]?.GetValue<string>()
            ?? string.Empty;

        return new LogicUnderstandingStageDto
        {
            ModulePurpose = modulePurposeText,
            ImportantFlows = ParseStringArray(node["importantFlows"]?.ToJsonString() ?? node["userFlows"]?.ToJsonString() ?? "[]"),
            Rules = ParseStringArray(node["rules"]?.ToJsonString() ?? node["businessRules"]?.ToJsonString() ?? "[]"),
            Dependencies = ParseStringArray(node["dependencies"]?.ToJsonString() ?? "[]"),
            MustPreserve = ParseStringArray(node["mustPreserve"]?.ToJsonString() ?? "[]"),
            FlowDetails = ParseNamedProvenancedDetails(node["workflows"], "name"),
            RuleDetails = ParseNamedProvenancedDetails(node["businessRules"], "rule"),
            Unknowns = ParseStringArray(node["unknowns"]?.ToJsonString() ?? "[]"),
            Confidence = ParseDouble(node["confidence"], 0),
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
                    Purpose = obj["purpose"]?.GetValue<string>() ?? string.Empty,
                    Scenarios = ParseScenarioPlans(obj["scenarios"])
                });
            }
        }

        var existingTestsFound = new List<string>();
        if (node["existingTestsFound"] is JsonObject existing)
        {
            existingTestsFound.Add($"Total Files: {existing["totalFiles"]?.GetValue<int>() ?? 0}");
            existingTestsFound.Add($"Unit: {existing["unit"]?.GetValue<int>() ?? 0}");
            existingTestsFound.Add($"Integration: {existing["integration"]?.GetValue<int>() ?? 0}");
            existingTestsFound.Add($"API: {existing["api"]?.GetValue<int>() ?? 0}");
            existingTestsFound.Add($"E2E: {existing["e2e"]?.GetValue<int>() ?? 0}");
        }
        else
        {
            existingTestsFound = ParseStringArray(node["existingTestsFound"]?.ToJsonString() ?? "[]");
        }

        return new TestPlanStageDto
        {
            ExistingTestsFound = existingTestsFound,
            NewTestsSuggested = ParseStringArray(node["newTestsSuggested"]?.ToJsonString() ?? "[]"),
            TestCategories = categoryItems,
            CoverageSummary = node["coverageSummary"]?.GetValue<string>() ?? string.Empty,
            SourceArtifactPath = path
        };
    }

    private async Task<ExecutionStageDto> BuildExecutionStageAsync(IDbConnection connection, long runFk, string artifactRoot, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync(connection, @"
SELECT category, purpose, scenarios_json, total, passed, failed, warnings, new_tests_added,
       logs_json, artifacts_json, source_skill, stage
FROM test_category_results
WHERE run_fk=@RunFk
ORDER BY CASE category
    WHEN 'Unit' THEN 1
    WHEN 'Integration' THEN 2
    WHEN 'E2E' THEN 3
    WHEN 'API' THEN 4
    WHEN 'Edge Case' THEN 5
    WHEN 'Playwright / E2E Browser' THEN 6
    WHEN 'Playwright / Browser Verification' THEN 6
    WHEN 'DevTools Diagnostics' THEN 7
    ELSE 99
END;", new { RunFk = runFk }, cancellationToken);

        var categories = rows.Select(static row => {
            var scenarioDetails = ParseExecutionScenarioDetails(row.GetString("scenarios_json"));
            var preflight = ParsePreflightFromArtifacts(ParseStringArray(row.GetString("artifacts_json")));
            return new TestCategoryExecutionDto
            {
                Category = row.GetString("category"),
                Purpose = row.GetString("purpose"),
                ScenariosCovered = scenarioDetails.Select(static s => s.Name).Where(static s => !string.IsNullOrWhiteSpace(s)).ToList(),
                ScenarioDetails = scenarioDetails,
                TotalCount = row.GetInt("total"),
                Passed = row.GetInt("passed"),
                Failed = row.GetInt("failed"),
                Warnings = row.GetInt("warnings"),
                NewTestsAdded = row.GetInt("new_tests_added"),
                SourceSkill = row.GetString("source_skill"),
                PreflightStatus = preflight.ok ? "ok" : "failed",
                PreflightReason = preflight.reason,
                ScenarioConfidence = scenarioDetails.Count == 0 ? 0 : scenarioDetails.Average(static s => s.Confidence),
                Logs = ParseStringArray(row.GetString("logs_json")),
                Artifacts = ParseStringArray(row.GetString("artifacts_json"))
            };
        }).ToList();

        var playwright = await BuildPlaywrightEvidenceAsync(connection, runFk, artifactRoot, cancellationToken);

        return new ExecutionStageDto
        {
            TestCategories = categories,
            Playwright = playwright
        };
    }

    private async Task<PlaywrightEvidenceDto> BuildPlaywrightEvidenceAsync(IDbConnection connection, long runFk, string artifactRoot, CancellationToken cancellationToken)
    {
        var row = (await QueryRowsAsync(connection, @"
SELECT status, summary, metrics_json, artifacts_json
FROM skill_executions
WHERE run_fk=@RunFk AND skill_name='playwright-browser-verification'
LIMIT 1;", new { RunFk = runFk }, cancellationToken)).FirstOrDefault();

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
        var testApiStatusPath = Path.Combine(artifactRoot, "playwright-browser-verification", "test-api-status.json");
        var screenshotRoot = Path.Combine(artifactRoot, "playwright-browser-verification", "screenshots");

        var consoleEntries = await ReadStringArrayFileAsync(consolePath, cancellationToken);
        var consoleErrors = consoleEntries.Where(static e => e.Contains("error", StringComparison.OrdinalIgnoreCase) || e.Contains("TypeError", StringComparison.OrdinalIgnoreCase)).ToList();
        var consoleWarnings = consoleEntries.Where(static e => e.Contains("warn", StringComparison.OrdinalIgnoreCase) || e.Contains("warning", StringComparison.OrdinalIgnoreCase)).ToList();

        var testApiEndpoint = string.Empty;
        var testApiStatus = "unknown";
        var testApiReason = string.Empty;
        var testApiSource = string.Empty;
        var testApiAutoProvisioned = false;
        if (File.Exists(testApiStatusPath))
        {
            try
            {
                var apiNode = JsonNode.Parse(await File.ReadAllTextAsync(testApiStatusPath, cancellationToken)) as JsonObject;
                if (apiNode is not null)
                {
                    testApiEndpoint = apiNode["endpoint"]?.GetValue<string>() ?? string.Empty;
                    testApiStatus = apiNode["status"]?.GetValue<string>() ?? "unknown";
                    testApiReason = apiNode["reason"]?.GetValue<string>() ?? string.Empty;
                    testApiSource = apiNode["source"]?.GetValue<string>() ?? string.Empty;
                    testApiAutoProvisioned = apiNode["autoProvisioned"]?.GetValue<bool>() ?? false;
                }
            }
            catch
            {
                testApiStatus = "unknown";
                testApiReason = "test-api-status-read-failed";
            }
        }

        return new PlaywrightEvidenceDto
        {
            Status = row.GetString("status"),
            Summary = row.GetString("summary"),
            TestApiEndpoint = testApiEndpoint,
            TestApiStatus = testApiStatus,
            TestApiReason = testApiReason,
            TestApiSource = testApiSource,
            TestApiAutoProvisioned = testApiAutoProvisioned,
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

    private async Task<FindingsStageDto> BuildFindingsStageAsync(IDbConnection connection, long runFk, string moduleName, string runId, CancellationToken cancellationToken)
    {
        var findings = await QueryRowsAsync(connection, @"
SELECT stage, skill_name, scenario, issue_type, message, likely_cause, evidence, severity, status,
       confidence, resolved_in_run_id, resolution_notes, affected_files_json
FROM finding_records
WHERE run_fk=@RunFk
ORDER BY id DESC;", new { RunFk = runFk }, cancellationToken);

        var recommendations = await QueryRowsAsync(connection, @"
SELECT stage, skill_name, message, priority, evidence
FROM recommendation_records
WHERE run_fk=@RunFk
ORDER BY id DESC;", new { RunFk = runFk }, cancellationToken);

        var findingDtos = findings.Select(row => new FindingDto
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
                ProvenanceType = "code-evidence",
                ResolvedInRunId = row.GetString("resolved_in_run_id"),
                ResolutionNotes = row.GetString("resolution_notes"),
                AffectedFiles = ParseStringArray(row.GetString("affected_files_json"))
            })
            .ToList();

        var recommendationDtos = recommendations.Select(row => new RecommendationDto
            {
                ModuleName = moduleName,
                RunId = runId,
                Stage = row.GetString("stage"),
                SkillName = row.GetString("skill_name"),
                Message = row.GetString("message"),
                Priority = row.GetString("priority"),
                Evidence = row.GetString("evidence"),
                ProvenanceType = "code-evidence"
            })
            .ToList();

        return new FindingsStageDto
        {
            Findings = DeduplicateFindings(findingDtos),
            Recommendations = DeduplicateRecommendations(recommendationDtos)
        };
    }

    private async Task<ParityStageDto> BuildParityStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(artifactRoot, "parity-verification", "parity-diff.json");
        if (!File.Exists(path))
        {
            return new ParityStageDto { SourceArtifactPath = path };
        }

        var node = JsonNode.Parse(await File.ReadAllTextAsync(path, cancellationToken)) as JsonObject;
        if (node is null)
        {
            return new ParityStageDto { SourceArtifactPath = path };
        }

        var checks = ParseParityChecks(node["checks"]);
        var failed = checks.Count(static c => !string.Equals(c.Status, "passed", StringComparison.OrdinalIgnoreCase));

        return new ParityStageDto
        {
            ParityScore = (int)(node["parityScore"]?.GetValue<double>() ?? 0),
            TotalChecks = checks.Count,
            PassedChecks = Math.Max(0, checks.Count - failed),
            FailedChecks = failed,
            Confidence = ParseDouble(node["confidence"], 0),
            Checks = checks,
            SqlParity = ParseSqlParity(node["sqlParity"]),
            Gaps = ParseStringArray(node["gaps"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = path
        };
    }

    private async Task<KeyLearningsDto> BuildKeyLearningsAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var lessonsPath = Path.Combine(artifactRoot, "lessons-learned", "lessons-learned.json");
        var kbPath = Path.Combine(Path.GetDirectoryName(artifactRoot) ?? string.Empty, "_knowledge-base", "lessons-kb.json");

        var lessonsNode = File.Exists(lessonsPath)
            ? JsonNode.Parse(await File.ReadAllTextAsync(lessonsPath, cancellationToken)) as JsonObject
            : null;
        var kbNode = File.Exists(kbPath)
            ? JsonNode.Parse(await File.ReadAllTextAsync(kbPath, cancellationToken)) as JsonObject
            : null;

        return new KeyLearningsDto
        {
            RecurringSignatures = ParseStringArray(kbNode?["recurringSignatures"]?.ToJsonString() ?? "[]"),
            KnownPitfalls = ParseStringArray(kbNode?["knownPitfalls"]?.ToJsonString() ?? "[]"),
            NewIssues = ParseStringArray(lessonsNode?["newIssues"]?.ToJsonString() ?? "[]"),
            RecurringIssues = ParseStringArray(lessonsNode?["recurringIssues"]?.ToJsonString() ?? "[]"),
            ResolvedIssues = ParseStringArray(lessonsNode?["resolvedIssues"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = File.Exists(lessonsPath) ? lessonsPath : kbPath
        };
    }

    private static List<FindingDto> DeduplicateFindings(List<FindingDto> findings)
    {
        return findings
            .GroupBy(static f => string.Join("|",
                NormalizeKey(f.Stage),
                NormalizeKey(f.SkillName),
                NormalizeKey(f.Scenario),
                NormalizeKey(f.FindingType),
                NormalizeKey(f.Message)), StringComparer.Ordinal)
            .Select(static g => g
                .OrderByDescending(x => x.Confidence)
                .ThenByDescending(x => SeverityRank(x.Severity))
                .First())
            .OrderByDescending(static x => SeverityRank(x.Severity))
            .ThenBy(static x => x.Stage, StringComparer.OrdinalIgnoreCase)
            .ThenBy(static x => x.SkillName, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static List<RecommendationDto> DeduplicateRecommendations(List<RecommendationDto> recommendations)
    {
        return recommendations
            .GroupBy(static r => string.Join("|",
                NormalizeKey(r.Stage),
                NormalizeKey(r.SkillName),
                NormalizeKey(r.Priority),
                NormalizeKey(r.Message)), StringComparer.Ordinal)
            .Select(static g => g.First())
            .OrderByDescending(static x => PriorityRank(x.Priority))
            .ThenBy(static x => x.Stage, StringComparer.OrdinalIgnoreCase)
            .ThenBy(static x => x.SkillName, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static string NormalizeKey(string? value)
    {
        return (value ?? string.Empty).Trim().ToLowerInvariant();
    }

    private static int SeverityRank(string? severity)
    {
        return NormalizeKey(severity) switch
        {
            "critical" => 4,
            "high" => 3,
            "medium" => 2,
            "low" => 1,
            _ => 0
        };
    }

    private static int PriorityRank(string? priority)
    {
        return NormalizeKey(priority) switch
        {
            "high" => 3,
            "medium" => 2,
            "low" => 1,
            _ => 0
        };
    }

    private async Task<IterationComparisonSummaryDto> BuildIterationSummaryAsync(IDbConnection connection, string moduleName, string runId, string artifactRoot, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync(connection, @"
SELECT d.previous_run_id, d.tests_added, d.tests_fixed, d.failures_reduced,
       d.new_findings_introduced, d.resolved_findings, d.progression_trend
FROM iteration_deltas d
INNER JOIN modules m ON m.id = d.module_id
WHERE m.name=@ModuleName AND d.run_id=@RunId
LIMIT 1;", new { ModuleName = moduleName, RunId = runId }, cancellationToken);

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

    private async Task<JsonObject?> GetRunRowAsync(IDbConnection connection, string moduleName, string runId, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync(connection, @"
SELECT r.id, r.artifact_root, r.status, r.summary, r.started_at, r.ended_at
FROM runs r
INNER JOIN modules m ON m.id = r.module_id
WHERE m.name=@ModuleName AND r.run_id=@RunId
ORDER BY r.id DESC
LIMIT 1;", new { ModuleName = moduleName, RunId = runId }, cancellationToken);

        return rows.FirstOrDefault();
    }

    private string BuildRunInputJson(RunInputDraftDto draft)
    {
        var baseUrl = NormalizeBaseUrlForRunInput((draft.BaseUrl ?? string.Empty).Trim());
        var normalizedBaseUrl = baseUrl.TrimEnd('/');
        var testApiEndpoint = string.IsNullOrWhiteSpace(normalizedBaseUrl)
            ? string.Empty
            : $"{normalizedBaseUrl}/api/test";
        var knownUrls = ResolveKnownUrls(ParseMultiline(draft.KnownUrlsText), normalizedBaseUrl);

        var payload = new
        {
            runId = string.IsNullOrWhiteSpace(draft.RunId) ? "run-001" : draft.RunId.Trim(),
            moduleName = draft.ModuleName.Trim(),
            legacySourceRoot = draft.LegacySourceRoot.Trim(),
            convertedSourceRoot = draft.ConvertedSourceRoot.Trim(),
            baseUrl,
            testApiEndpoint,
            brsPath = draft.BrsPath.Trim(),
            moduleHints = new
            {
                relatedFolders = ParseMultiline(draft.RelatedFoldersText),
                knownUrls,
                keywords = ParseMultiline(draft.KeywordsText)
            },
            testCommands = new
            {
                unit = draft.UnitCommand.Trim(),
                integration = draft.IntegrationCommand.Trim(),
                api = draft.ApiCommand.Trim(),
                e2e = draft.E2eCommand.Trim(),
                edgeCase = draft.EdgeCaseCommand.Trim(),
                playwright = draft.PlaywrightCommand.Trim()
            },
            selectedSkills = (draft.SelectedSkills ?? []).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(static s => s).ToList()
        };

        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
    }

    private static async Task<List<JsonObject>> QueryRowsAsync(IDbConnection connection, string sql, object? parameters, CancellationToken cancellationToken)
    {
        var rows = await connection.QueryAsync(new CommandDefinition(sql, parameters, cancellationToken: cancellationToken));
        var result = new List<JsonObject>();

        foreach (var row in rows)
        {
            if (row is not IDictionary<string, object?> dictionary)
            {
                continue;
            }

            var obj = new JsonObject();
            foreach (var (key, value) in dictionary)
            {
                obj[key] = ToJsonNode(value);
            }
            result.Add(obj);
        }

        return result;
    }

    private static JsonNode? ToJsonNode(object? value)
    {
        if (value is null || value is DBNull)
        {
            return null;
        }

        return value switch
        {
            string s => JsonValue.Create(s),
            int i => JsonValue.Create(i),
            long l => JsonValue.Create(l),
            short s16 => JsonValue.Create(s16),
            byte b => JsonValue.Create(b),
            double d => JsonValue.Create(d),
            float f => JsonValue.Create(f),
            decimal dec => JsonValue.Create(dec),
            bool bo => JsonValue.Create(bo),
            DateTime dt => JsonValue.Create(dt.ToString("O")),
            DateTimeOffset dto => JsonValue.Create(dto.ToString("O")),
            byte[] bytes => JsonValue.Create(Convert.ToBase64String(bytes)),
            _ => JsonValue.Create(value.ToString())
        };
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
                .Select(static item =>
                {
                    if (item is null)
                    {
                        return string.Empty;
                    }

                    if (item is JsonValue value)
                    {
                        return value.GetValue<string>();
                    }

                    if (item is JsonObject obj)
                    {
                        return obj["name"]?.GetValue<string>()
                            ?? obj["value"]?.GetValue<string>()
                            ?? obj["rule"]?.GetValue<string>()
                            ?? obj["behavior"]?.GetValue<string>()
                            ?? obj["path"]?.GetValue<string>()
                            ?? string.Empty;
                    }

                    return string.Empty;
                })
                .Where(static item => !string.IsNullOrWhiteSpace(item))
                .ToList();
        }
        catch
        {
            return [];
        }
    }

    private static double ParseDouble(JsonNode? node, double fallback)
    {
        if (node is null)
        {
            return fallback;
        }

        return double.TryParse(node.ToString(), out var parsed) ? parsed : fallback;
    }

    private static (string Type, double Confidence, List<string> Sources) ParseProvenance(JsonNode? node)
    {
        if (node is not JsonObject obj)
        {
            return ("inferred", 0.5, []);
        }

        var type = obj["type"]?.GetValue<string>() ?? "inferred";
        var confidence = ParseDouble(obj["confidence"], 0.5);
        var sources = ParseStringArray(obj["sources"]?.ToJsonString() ?? "[]");
        return (type, confidence, sources);
    }

    private static List<ProvenancedValueDto> ParseNamedProvenancedDetails(JsonNode? node, string valueKey)
    {
        if (node is not JsonArray array)
        {
            return [];
        }

        var output = new List<ProvenancedValueDto>();
        foreach (var item in array)
        {
            if (item is not JsonObject obj)
            {
                continue;
            }

            var value = obj[valueKey]?.GetValue<string>() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(value))
            {
                continue;
            }

            var provenance = ParseProvenance(obj["provenance"]);
            output.Add(new ProvenancedValueDto
            {
                Value = value,
                ProvenanceType = provenance.Type,
                Confidence = provenance.Confidence,
                Sources = provenance.Sources
            });
        }

        return output;
    }

    private static List<ProvenancedValueDto> ParseRouteDetails(JsonNode? node)
    {
        if (node is not JsonArray array)
        {
            return [];
        }

        var output = new List<ProvenancedValueDto>();
        foreach (var item in array)
        {
            if (item is not JsonObject obj)
            {
                continue;
            }

            var value = obj["route"]?.GetValue<string>() ?? obj["normalizedRoute"]?.GetValue<string>() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(value))
            {
                continue;
            }

            var provenance = ParseProvenance(obj["provenance"]);
            output.Add(new ProvenancedValueDto
            {
                Value = value,
                ProvenanceType = provenance.Type,
                Confidence = provenance.Confidence,
                Sources = provenance.Sources
            });
        }

        return output;
    }

    private static List<TestScenarioPlanDto> ParseScenarioPlans(JsonNode? node)
    {
        if (node is not JsonArray array)
        {
            return [];
        }

        var output = new List<TestScenarioPlanDto>();
        foreach (var item in array)
        {
            if (item is JsonValue value)
            {
                var text = value.GetValue<string>();
                if (string.IsNullOrWhiteSpace(text))
                {
                    continue;
                }

                output.Add(new TestScenarioPlanDto
                {
                    Name = text,
                    Coverage = [],
                    ProvenanceType = "inferred",
                    Confidence = 0.5
                });
                continue;
            }

            if (item is not JsonObject obj)
            {
                continue;
            }

            var scenarioName = obj["name"]?.GetValue<string>() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(scenarioName))
            {
                continue;
            }

            var provenance = ParseProvenance(obj["provenance"]);
            output.Add(new TestScenarioPlanDto
            {
                Name = scenarioName,
                Coverage = ParseStringArray(obj["coverage"]?.ToJsonString() ?? "[]"),
                ProvenanceType = provenance.Type,
                Confidence = provenance.Confidence
            });
        }

        return output;
    }

    private static List<TestScenarioExecutionDto> ParseExecutionScenarioDetails(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        try
        {
            var node = JsonNode.Parse(json);
            if (node is not JsonArray array)
            {
                return [];
            }

            var output = new List<TestScenarioExecutionDto>();
            foreach (var item in array)
            {
                if (item is JsonValue value)
                {
                    var text = value.GetValue<string>();
                    if (string.IsNullOrWhiteSpace(text))
                    {
                        continue;
                    }
                    output.Add(new TestScenarioExecutionDto
                    {
                        Name = text,
                        Status = "unknown",
                        Notes = string.Empty,
                        Coverage = [],
                        Generated = false,
                        GeneratedFrom = [],
                        ProvenanceType = "inferred",
                        Confidence = 0.5
                    });
                    continue;
                }

                if (item is not JsonObject obj)
                {
                    continue;
                }

                var provenance = ParseProvenance(obj["provenance"]);
                output.Add(new TestScenarioExecutionDto
                {
                    Name = obj["name"]?.GetValue<string>() ?? string.Empty,
                    Status = obj["status"]?.GetValue<string>() ?? "unknown",
                    Notes = obj["notes"]?.GetValue<string>() ?? string.Empty,
                    Coverage = ParseStringArray(obj["coverage"]?.ToJsonString() ?? "[]"),
                    Generated = obj["generated"]?.GetValue<bool>() ?? false,
                    GeneratedFrom = ParseStringArray(obj["generatedFrom"]?.ToJsonString() ?? "[]"),
                    ProvenanceType = provenance.Type,
                    Confidence = provenance.Confidence
                });
            }

            return output;
        }
        catch
        {
            return [];
        }
    }

    private static List<ParityCheckDto> ParseParityChecks(JsonNode? node)
    {
        if (node is not JsonArray array)
        {
            return [];
        }

        var output = new List<ParityCheckDto>();
        foreach (var item in array)
        {
            if (item is not JsonObject obj)
            {
                continue;
            }

            var evidenceLines = new List<string>();
            if (obj["evidence"] is JsonObject evidence)
            {
                if (evidence["failedExecutionSkills"] is JsonArray failedSkills)
                {
                    var values = ParseStringArray(failedSkills.ToJsonString());
                    if (values.Count > 0)
                    {
                        evidenceLines.Add($"Failed execution skills: {string.Join(", ", values)}");
                    }
                }

                if (evidence["relatedUrls"] is JsonArray urls)
                {
                    var values = ParseStringArray(urls.ToJsonString());
                    if (values.Count > 0)
                    {
                        evidenceLines.Add($"Related URLs: {string.Join(", ", values.Take(5))}");
                    }
                }

                if (evidence["relatedDbTouchpoints"] is JsonArray dbTouchpoints)
                {
                    var values = ParseStringArray(dbTouchpoints.ToJsonString());
                    if (values.Count > 0)
                    {
                        evidenceLines.Add($"DB touchpoints: {string.Join(", ", values.Take(5))}");
                    }
                }

                foreach (var entry in evidence)
                {
                    if (entry.Value is JsonValue value &&
                        !string.Equals(entry.Key, "legacyQueryCount", StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(entry.Key, "convertedQueryCount", StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(entry.Key, "matchedCount", StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(entry.Key, "missingCount", StringComparison.OrdinalIgnoreCase))
                    {
                        evidenceLines.Add($"{entry.Key}: {value}");
                    }
                }

                var legacyCount = evidence["legacyQueryCount"]?.GetValue<int>();
                var convertedCount = evidence["convertedQueryCount"]?.GetValue<int>();
                var matchedCount = evidence["matchedCount"]?.GetValue<int>();
                var missingCount = evidence["missingCount"]?.GetValue<int>();
                if (legacyCount.HasValue || convertedCount.HasValue || matchedCount.HasValue || missingCount.HasValue)
                {
                    evidenceLines.Add($"SQL summary: legacy={legacyCount ?? 0}, converted={convertedCount ?? 0}, matched={matchedCount ?? 0}, missing={missingCount ?? 0}");
                }
            }

            var provenance = ParseProvenance(obj["provenance"]);
            output.Add(new ParityCheckDto
            {
                Name = obj["name"]?.GetValue<string>() ?? string.Empty,
                Status = obj["status"]?.GetValue<string>() ?? "unknown",
                EvidenceLines = evidenceLines,
                ProvenanceType = provenance.Type,
                Confidence = provenance.Confidence
            });
        }

        return output;
    }

    private static SqlParityDto ParseSqlParity(JsonNode? node)
    {
        if (node is not JsonObject obj)
        {
            return new SqlParityDto();
        }

        var tables = new List<TableParityDto>();
        if (obj["tableMatches"] is JsonArray tableArray)
        {
            foreach (var item in tableArray)
            {
                if (item is not JsonObject table)
                {
                    continue;
                }

                tables.Add(new TableParityDto
                {
                    Table = table["table"]?.GetValue<string>() ?? string.Empty,
                    LegacyOccurrences = table["legacyOccurrences"]?.GetValue<int>() ?? 0,
                    ConvertedOccurrences = table["convertedOccurrences"]?.GetValue<int>() ?? 0,
                    Status = table["status"]?.GetValue<string>() ?? "unknown"
                });
            }
        }

        var beforeAfter = new List<SqlBeforeAfterDto>();
        if (obj["beforeAfter"] is JsonArray beforeAfterArray)
        {
            foreach (var item in beforeAfterArray)
            {
                if (item is not JsonObject map)
                {
                    continue;
                }

                beforeAfter.Add(new SqlBeforeAfterDto
                {
                    Status = map["status"]?.GetValue<string>() ?? "unknown",
                    LegacyFile = map["legacyFile"]?.GetValue<string>() ?? string.Empty,
                    LegacyQuery = map["legacyQuery"]?.GetValue<string>() ?? string.Empty,
                    LegacyTables = ParseStringArray(map["legacyTables"]?.ToJsonString() ?? "[]"),
                    ConvertedFile = map["convertedFile"]?.GetValue<string>() ?? string.Empty,
                    ConvertedQuery = map["convertedQuery"]?.GetValue<string>() ?? string.Empty,
                    ConvertedTables = ParseStringArray(map["convertedTables"]?.ToJsonString() ?? "[]"),
                    Confidence = ParseDouble(map["confidence"], 0)
                });
            }
        }

        return new SqlParityDto
        {
            LegacyQueryCount = obj["legacyQueryCount"]?.GetValue<int>() ?? 0,
            ConvertedQueryCount = obj["convertedQueryCount"]?.GetValue<int>() ?? 0,
            MatchedCount = obj["matchedCount"]?.GetValue<int>() ?? 0,
            Tables = tables,
            BeforeAfter = beforeAfter
        };
    }

    private static (bool ok, string reason) ParsePreflightFromArtifacts(List<string> artifacts)
    {
        var preflightPath = artifacts.FirstOrDefault(static a => a.EndsWith("preflight.json", StringComparison.OrdinalIgnoreCase));
        if (string.IsNullOrWhiteSpace(preflightPath) || !File.Exists(preflightPath))
        {
            return (false, "missing-preflight-artifact");
        }

        try
        {
            var node = JsonNode.Parse(File.ReadAllText(preflightPath)) as JsonObject;
            if (node is null)
            {
                return (false, "invalid-preflight-json");
            }

            var failedReasons = new List<string>();
            if ((node["baseUrl"] as JsonObject)?["ok"]?.GetValue<bool>() == false)
            {
                failedReasons.Add("baseUrl");
            }
            if ((node["reachability"] as JsonObject)?["ok"]?.GetValue<bool>() == false)
            {
                failedReasons.Add("reachability");
            }
            var commandsNode = node["commands"] as JsonObject;
            if (commandsNode is not null && commandsNode["ok"]?.GetValue<bool>() == false)
            {
                failedReasons.Add("commands");
            }

            return failedReasons.Count == 0
                ? (true, "ok")
                : (false, string.Join(",", failedReasons));
        }
        catch
        {
            return (false, "preflight-read-failed");
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
                    .Select(static item =>
                    {
                        if (item is null)
                        {
                            return string.Empty;
                        }

                        if (item is JsonValue value)
                        {
                            return value.GetValue<string>();
                        }

                        if (item is JsonObject obj)
                        {
                            return obj["message"]?.GetValue<string>()
                                ?? obj["url"]?.GetValue<string>()
                                ?? obj["name"]?.GetValue<string>()
                                ?? obj.ToJsonString();
                        }

                        return item.ToJsonString();
                    })
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

    /// <summary>
    /// Retrieves browser testing results for a given module and run.
    /// </summary>
    public async Task<BrowserTestingResultsDto?> GetBrowserTestingResultsAsync(
        string moduleName,
        string runId,
        CancellationToken cancellationToken = default)
    {
        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);

        // Get the run_fk
        var runRow = await GetRunRowAsync(connection, moduleName, runId, cancellationToken);
        if (runRow is null)
        {
            return null;
        }

        var runFk = runRow.GetLong("id");

        // Query browser_devtools_sessions
        var sessionsRows = await QueryRowsAsync(connection, @"
SELECT id, base_url, start_timestamp, end_timestamp, total_scenarios, 
       passed_scenarios, failed_scenarios, viewport_sizes
FROM browser_devtools_sessions
WHERE run_fk = @RunFk;", new { RunFk = runFk }, cancellationToken);

        if (sessionsRows.Count == 0)
        {
            return new BrowserTestingResultsDto
            {
                ModuleName = moduleName,
                RunId = runId,
                Status = "not_executed",
                Sessions = [],
                ConsoleLogs = [],
                NetworkRequests = [],
                PerformanceMetrics = [],
                AccessibilityIssues = [],
                Screenshots = [],
                DomSnapshots = []
            };
        }

        var results = new BrowserTestingResultsDto
        {
            ModuleName = moduleName,
            RunId = runId,
            Status = "completed",
            Sessions = sessionsRows.Select(static row => new BrowserSessionDto
            {
                Id = row.GetLong("id"),
                BaseUrl = row.GetString("base_url"),
                StartTimestamp = row.GetString("start_timestamp"),
                EndTimestamp = row.GetString("end_timestamp"),
                TotalScenarios = row.GetInt("total_scenarios"),
                PassedScenarios = row.GetInt("passed_scenarios"),
                FailedScenarios = row.GetInt("failed_scenarios"),
                ViewportSizes = row.GetString("viewport_sizes")
            }).ToList(),
            ConsoleLogs = [],
            NetworkRequests = [],
            PerformanceMetrics = [],
            AccessibilityIssues = [],
            Screenshots = [],
            DomSnapshots = []
        };

        // Get console logs for each session
        foreach (var session in results.Sessions)
        {
            var logsRows = await QueryRowsAsync(connection, @"
SELECT level, message, source_file, source_line, timestamp, stack_trace
FROM browser_console_logs
WHERE session_fk = @SessionFk
ORDER BY timestamp;", new { SessionFk = session.Id }, cancellationToken);

            results.ConsoleLogs.AddRange(logsRows.Select(static row => new BrowserConsoleLogDto
            {
                Level = row.GetString("level"),
                Message = row.GetString("message"),
                SourceFile = row.GetString("source_file"),
                SourceLine = row.GetInt("source_line"),
                Timestamp = row.GetString("timestamp"),
                StackTrace = row.GetString("stack_trace")
            }));
        }

        // Get network requests
        foreach (var session in results.Sessions)
        {
            var requestsRows = await QueryRowsAsync(connection, @"
SELECT method, url, status_code, request_payload, response_payload, 
       response_time_ms, content_type, timestamp
FROM browser_network_requests
WHERE session_fk = @SessionFk
ORDER BY timestamp;", new { SessionFk = session.Id }, cancellationToken);

            results.NetworkRequests.AddRange(requestsRows.Select(static row => new BrowserNetworkRequestDto
            {
                Method = row.GetString("method"),
                Url = row.GetString("url"),
                StatusCode = row.GetInt("status_code"),
                RequestPayload = row.GetString("request_payload"),
                ResponsePayload = row.GetString("response_payload"),
                ResponseTimeMs = row.GetInt("response_time_ms"),
                ContentType = row.GetString("content_type"),
                Timestamp = row.GetString("timestamp")
            }));
        }

        // Get performance metrics
        foreach (var session in results.Sessions)
        {
            var metricsRows = await QueryRowsAsync(connection, @"
SELECT metric_name, metric_value, target_threshold, meets_threshold, timestamp
FROM browser_performance_metrics
WHERE session_fk = @SessionFk
ORDER BY timestamp;", new { SessionFk = session.Id }, cancellationToken);

            results.PerformanceMetrics.AddRange(metricsRows.Select(static row => new BrowserPerformanceMetricDto
            {
                MetricName = row["metric_name"]?.GetValue<string>() ?? string.Empty,
                MetricValue = row["metric_value"]?.GetValue<double>() ?? 0,
                TargetThreshold = row["target_threshold"]?.GetValue<double>() ?? 0,
                MeetsThreshold = row["meets_threshold"]?.GetValue<bool>() ?? false,
                Timestamp = row["timestamp"]?.GetValue<string>() ?? string.Empty
            }));
        }

        // Get accessibility issues
        foreach (var session in results.Sessions)
        {
            var issuesRows = await QueryRowsAsync(connection, @"
SELECT issue_type, severity, element_selector, issue_description, recommendation, timestamp
FROM browser_accessibility_issues
WHERE session_fk = @SessionFk
ORDER BY timestamp;", new { SessionFk = session.Id }, cancellationToken);

            results.AccessibilityIssues.AddRange(issuesRows.Select(static row => new BrowserAccessibilityIssueDto
            {
                IssueType = row.GetString("issue_type"),
                Severity = row.GetString("severity"),
                ElementSelector = row.GetString("element_selector"),
                IssueDescription = row.GetString("issue_description"),
                Recommendation = row.GetString("recommendation"),
                Timestamp = row.GetString("timestamp")
            }));
        }

        // Get screenshots
        foreach (var session in results.Sessions)
        {
            var screenshotsRows = await QueryRowsAsync(connection, @"
SELECT filename, artifact_path, viewport_width, viewport_height, scenario_context, captured_at
FROM browser_screenshots
WHERE session_fk = @SessionFk
ORDER BY captured_at;", new { SessionFk = session.Id }, cancellationToken);

            results.Screenshots.AddRange(screenshotsRows.Select(static row => new BrowserScreenshotDto
            {
                Filename = row.GetString("filename"),
                ArtifactPath = row.GetString("artifact_path"),
                ViewportWidth = row.GetInt("viewport_width"),
                ViewportHeight = row.GetInt("viewport_height"),
                ScenarioContext = row.GetString("scenario_context"),
                CapturedAt = row.GetString("captured_at")
            }));
        }

        // Get DOM snapshots
        foreach (var session in results.Sessions)
        {
            var snapshotsRows = await QueryRowsAsync(connection, @"
SELECT filename, artifact_path, scenario_context, element_count, captured_at
FROM browser_dom_snapshots
WHERE session_fk = @SessionFk
ORDER BY captured_at;", new { SessionFk = session.Id }, cancellationToken);

            results.DomSnapshots.AddRange(snapshotsRows.Select(static row => new BrowserDomSnapshotDto
            {
                Filename = row.GetString("filename"),
                ArtifactPath = row.GetString("artifact_path"),
                ScenarioContext = row.GetString("scenario_context"),
                ElementCount = row.GetInt("element_count"),
                CapturedAt = row.GetString("captured_at")
            }));
        }

        return results;
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
