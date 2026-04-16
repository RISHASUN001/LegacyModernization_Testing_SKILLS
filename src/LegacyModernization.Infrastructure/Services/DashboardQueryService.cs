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
        "csharp-discovery",
        "csharp-logic-understanding",
        "java-discovery",
        "legacy-logic-understanding",
        "diagram-generation",
        "functional-parity-and-sql-table-comparison",
        "ai-test-generation",
        "test-execution",
        "clean-architecture-and-findings",
        "pipeline-vanity-check"
    ];

    private static readonly Dictionary<string, string> StageTitleMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["csharp-discovery"] = "1. C# Discovery",
        ["csharp-logic-understanding"] = "2. C# Logic Understanding",
        ["java-discovery"] = "3. Java Discovery",
        ["legacy-logic-understanding"] = "4. Legacy Logic Understanding",
        ["diagram-generation"] = "5. Diagram Generation",
        ["functional-parity-and-sql-table-comparison"] = "6. Functional Parity",
        ["ai-test-generation"] = "7. AI Test Generation",
        ["test-execution"] = "8. Test Execution",
        ["clean-architecture-and-findings"] = "9. Clean Architecture and Findings",
        ["pipeline-vanity-check"] = "10. Pipeline Vanity Check"
    };

    private static bool IsApiCategory(string? category)
    {
        if (string.IsNullOrWhiteSpace(category))
        {
            return false;
        }

        return string.Equals(category.Trim(), "API", StringComparison.OrdinalIgnoreCase)
            || string.Equals(category.Trim(), "Api", StringComparison.OrdinalIgnoreCase)
            || category.Trim().StartsWith("API ", StringComparison.OrdinalIgnoreCase);
    }

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
    WHEN 'csharp-discovery' THEN 1
    WHEN 'csharp-logic-understanding' THEN 2
    WHEN 'java-discovery' THEN 3
    WHEN 'legacy-logic-understanding' THEN 4
    WHEN 'diagram-generation' THEN 5
    WHEN 'functional-parity-and-sql-table-comparison' THEN 6
    WHEN 'ai-test-generation' THEN 7
    WHEN 'test-execution' THEN 8
    WHEN 'clean-architecture-and-findings' THEN 9
    WHEN 'pipeline-vanity-check' THEN 10
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

    public Task<RunInputBuilderPageDto> GetRunInputBuilderAsync(CancellationToken cancellationToken = default)
    {
        var draft = new RunInputDraftDto { StrictModuleOnly = true, EnableUserInputPrompting = true };

        return Task.FromResult(new RunInputBuilderPageDto
        {
            Draft = draft,
            GeneratedJson = BuildRunInputJson(draft)
        });
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
        var summaryStageLookup = await LoadOrchestrationSummaryStagesAsync(artifactRoot, cancellationToken);

        var stageStatuses = StageOrder.Select(stage =>
        {
            var normalizedStage = NormalizeStageId(stage);
            var hasSummary = summaryStageLookup.TryGetValue(normalizedStage, out var summaryStage);

            stageLookup.TryGetValue(stage, out var found);
            if (found is null && !string.Equals(stage, normalizedStage, StringComparison.OrdinalIgnoreCase))
            {
                stageLookup.TryGetValue(normalizedStage, out found);
            }

            var failed = hasSummary
                ? summaryStage!.FailedSkills
                : found?.GetInt("failed_skills") ?? 0;

            var count = hasSummary
                ? summaryStage!.SkillCount
                : found?.GetInt("skill_count") ?? 0;

            var status = hasSummary
                ? summaryStage!.Status
                : count == 0 ? "unknown" : failed > 0 ? "failed" : "passed";

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

    private static string NormalizeStageId(string? stage)
    {
        if (string.IsNullOrWhiteSpace(stage))
        {
            return string.Empty;
        }

        return stage.Equals("java-logic-understanding", StringComparison.OrdinalIgnoreCase)
            ? "legacy-logic-understanding"
            : stage;
    }

    private sealed record SummaryStageSnapshot(string Status, int SkillCount, int FailedSkills);

    private static async Task<Dictionary<string, SummaryStageSnapshot>> LoadOrchestrationSummaryStagesAsync(
        string artifactRoot,
        CancellationToken cancellationToken)
    {
        var summaryPath = Path.Combine(artifactRoot, "orchestration-summary.json");
        if (!File.Exists(summaryPath))
        {
            return new Dictionary<string, SummaryStageSnapshot>(StringComparer.OrdinalIgnoreCase);
        }

        try
        {
            var node = JsonNode.Parse(await File.ReadAllTextAsync(summaryPath, cancellationToken)) as JsonObject;
            if (node?["stages"] is not JsonArray stages)
            {
                return new Dictionary<string, SummaryStageSnapshot>(StringComparer.OrdinalIgnoreCase);
            }

            var map = new Dictionary<string, SummaryStageSnapshot>(StringComparer.OrdinalIgnoreCase);
            foreach (var item in stages)
            {
                if (item is not JsonObject stageNode)
                {
                    continue;
                }

                var stageId = NormalizeStageId(stageNode["stage"]?.GetValue<string>() ?? string.Empty);
                if (string.IsNullOrWhiteSpace(stageId))
                {
                    continue;
                }

                var status = stageNode["status"]?.GetValue<string>() ?? "unknown";
                var skillCount = stageNode["skillCount"]?.GetValue<int>()
                    ?? (stageNode["skills"] as JsonArray)?.Count
                    ?? 0;
                var failedSkills = stageNode["skillsFailed"]?.GetValue<int>()
                    ?? (stageNode["skills"] as JsonArray)?.Count(static s =>
                        !string.Equals((s as JsonObject)?["status"]?.GetValue<string>(), "passed", StringComparison.OrdinalIgnoreCase))
                    ?? 0;

                map[stageId] = new SummaryStageSnapshot(status, skillCount, failedSkills);
            }

            return map;
        }
        catch
        {
            return new Dictionary<string, SummaryStageSnapshot>(StringComparer.OrdinalIgnoreCase);
        }
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
        var csharpModulePath = Path.Combine(artifactRoot, "csharp-module-discovery", "converted-module-map.json");
        var csharpWorkflowsPath = Path.Combine(artifactRoot, "csharp-module-discovery", "converted-workflows.json");
        var csharpRoutePath = Path.Combine(artifactRoot, "csharp-module-discovery", "controller-route-map.json");
        var csharpSqlPath = Path.Combine(artifactRoot, "csharp-module-discovery", "csharp-sql-map.json");
        var csharpTablePath = Path.Combine(artifactRoot, "csharp-module-discovery", "csharp-table-usage.json");

        var csharpWorkflowCount = 0;
        var csharpControllerCount = 0;
        var csharpSqlSignatureCount = 0;
        var csharpTableCount = 0;
        var csharpRoutes = new List<string>();

        if (File.Exists(csharpWorkflowsPath))
        {
            var csharpWorkflowsNode = JsonNode.Parse(await File.ReadAllTextAsync(csharpWorkflowsPath, cancellationToken)) as JsonObject;
            csharpWorkflowCount = (csharpWorkflowsNode?["workflows"] as JsonArray)?.Count ?? 0;
        }

        if (File.Exists(csharpRoutePath))
        {
            var routeNode = JsonNode.Parse(await File.ReadAllTextAsync(csharpRoutePath, cancellationToken)) as JsonObject;
            var controllers = routeNode?["controllers"] as JsonArray;
            csharpControllerCount = controllers?.Count ?? 0;
            if (controllers is not null)
            {
                foreach (var item in controllers)
                {
                    if (item is not JsonObject obj || obj["routes"] is not JsonArray routes)
                    {
                        continue;
                    }

                    foreach (var route in routes)
                    {
                        var value = route?.GetValue<string>() ?? string.Empty;
                        if (!string.IsNullOrWhiteSpace(value))
                        {
                            csharpRoutes.Add(value);
                        }
                    }
                }
            }
        }

        if (File.Exists(csharpSqlPath))
        {
            var sqlNode = JsonNode.Parse(await File.ReadAllTextAsync(csharpSqlPath, cancellationToken)) as JsonObject;
            csharpSqlSignatureCount = (sqlNode?["queries"] as JsonArray)?.Count ?? 0;
        }

        if (File.Exists(csharpTablePath))
        {
            var tableNode = JsonNode.Parse(await File.ReadAllTextAsync(csharpTablePath, cancellationToken)) as JsonObject;
            csharpTableCount = (tableNode?["tables"] as JsonArray)?.Count ?? 0;
        }

        if (!File.Exists(path))
        {
            return new DiscoveryStageDto
            {
                ConvertedWorkflowCount = csharpWorkflowCount,
                ConvertedControllerCount = csharpControllerCount,
                ConvertedSqlSignatureCount = csharpSqlSignatureCount,
                ConvertedTableCount = csharpTableCount,
                ConvertedRoutes = csharpRoutes.Distinct(StringComparer.OrdinalIgnoreCase).Take(20).ToList(),
                ConvertedSourceArtifactPath = File.Exists(csharpModulePath) ? csharpModulePath : string.Empty,
                SourceArtifactPath = path
            };
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
            ScopeContext = ParseScopeContext(node["scopeContext"]),
            ConvertedWorkflowCount = csharpWorkflowCount,
            ConvertedControllerCount = csharpControllerCount,
            ConvertedSqlSignatureCount = csharpSqlSignatureCount,
            ConvertedTableCount = csharpTableCount,
            ConvertedRoutes = csharpRoutes.Distinct(StringComparer.OrdinalIgnoreCase).Take(20).ToList(),
            ConvertedSourceArtifactPath = File.Exists(csharpModulePath) ? csharpModulePath : string.Empty,
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
            ScopeApplied = ParseScopeApplied(node["scopeApplied"]),
            Confidence = ParseDouble(node["confidence"], 0),
            SourceArtifactPath = sourcePath
        };
    }

    private async Task<ArchitectureReviewStageDto> BuildArchitectureStageAsync(string artifactRoot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(artifactRoot, "clean-architecture-assessment", "architecture-review.json");
        var legacyModulePath = Path.Combine(artifactRoot, "java-counterpart-discovery", "legacy-module-map.json");
        var legacyWorkflowsPath = Path.Combine(artifactRoot, "java-counterpart-discovery", "legacy-workflows.json");
        var javaSqlPath = Path.Combine(artifactRoot, "java-counterpart-discovery", "java-sql-map.json");
        var javaExclusionsPath = Path.Combine(artifactRoot, "java-counterpart-discovery", "java-exclusions.json");
        // Prefer current skill output folder, then try compatibility fallbacks.
        var diagramFolderName = "excalidraw-diagram";
        var diagramIndexPath = Path.Combine(artifactRoot, diagramFolderName, "diagram-index.json");
        if (!File.Exists(diagramIndexPath))
        {
            diagramFolderName = "excalidraw";
            diagramIndexPath = Path.Combine(artifactRoot, diagramFolderName, "diagram-index.json");
        }
        if (!File.Exists(diagramIndexPath))
        {
            diagramFolderName = "logic-flow-visualization";
            diagramIndexPath = Path.Combine(artifactRoot, diagramFolderName, "diagram-index.json");
        }

        var javaRelatedFileCount = 0;
        var javaWorkflowCount = 0;
        var javaSqlSignatureCount = 0;
        var javaExclusionCount = 0;
        var javaRelatedSamples = new List<string>();
        var javaExclusionSamples = new List<string>();
        var diagramBundles = new List<DiagramBundleDto>();

        if (File.Exists(legacyModulePath))
        {
            var legacyNode = JsonNode.Parse(await File.ReadAllTextAsync(legacyModulePath, cancellationToken)) as JsonObject;
            javaRelatedFileCount = legacyNode?["relatedFileCount"]?.GetValue<int>() ?? 0;
            javaRelatedSamples = ParseStringArray(legacyNode?["relatedFiles"]?.ToJsonString() ?? "[]").Take(12).ToList();
        }

        if (File.Exists(legacyWorkflowsPath))
        {
            var workflowNode = JsonNode.Parse(await File.ReadAllTextAsync(legacyWorkflowsPath, cancellationToken)) as JsonObject;
            javaWorkflowCount = (workflowNode?["workflows"] as JsonArray)?.Count ?? 0;
        }

        if (File.Exists(javaSqlPath))
        {
            var sqlNode = JsonNode.Parse(await File.ReadAllTextAsync(javaSqlPath, cancellationToken)) as JsonObject;
            javaSqlSignatureCount = (sqlNode?["queries"] as JsonArray)?.Count ?? 0;
        }

        if (File.Exists(javaExclusionsPath))
        {
            var exclusionNode = JsonNode.Parse(await File.ReadAllTextAsync(javaExclusionsPath, cancellationToken)) as JsonObject;
            var exclusions = exclusionNode?["excluded"] as JsonArray;
            javaExclusionCount = exclusions?.Count ?? 0;
            if (exclusions is not null)
            {
                javaExclusionSamples = exclusions
                    .Select(static x => x as JsonObject)
                    .Where(static x => x is not null)
                    .Select(static x => x!["path"]?.GetValue<string>() ?? string.Empty)
                    .Where(static x => !string.IsNullOrWhiteSpace(x))
                    .Take(12)
                    .ToList();
            }
        }

        if (File.Exists(diagramIndexPath))
        {
            var diagramNode = JsonNode.Parse(await File.ReadAllTextAsync(diagramIndexPath, cancellationToken)) as JsonObject;
            if (diagramNode?["items"] is JsonArray items)
            {
                diagramBundles = items
                    .Select(static x => x as JsonObject)
                    .Where(static x => x is not null)
                    .Select(static x => new DiagramBundleDto
                    {
                        Workflow = x!["workflow"]?.GetValue<string>() ?? string.Empty,
                        Group = x["group"]?.GetValue<string>() ?? string.Empty,
                        MermaidPath = x["mermaid"]?.GetValue<string>() ?? string.Empty,
                        ExcalidrawPath = x["excalidraw"]?.GetValue<string>() ?? string.Empty,
                        PreviewPath = x["preview"]?.GetValue<string>() ?? string.Empty,
                    })
                    .Where(static x => !string.IsNullOrWhiteSpace(x.Workflow))
                    .Take(40)
                    .ToList();

                for (var i = 0; i < diagramBundles.Count; i++)
                {
                    var item = diagramBundles[i];
                    diagramBundles[i] = new DiagramBundleDto
                    {
                        Workflow = item.Workflow,
                        Group = item.Group,
                        MermaidPath = string.IsNullOrWhiteSpace(item.MermaidPath)
                            ? string.Empty
                            : Path.Combine(artifactRoot, diagramFolderName, item.MermaidPath),
                        ExcalidrawPath = string.IsNullOrWhiteSpace(item.ExcalidrawPath)
                            ? string.Empty
                            : Path.Combine(artifactRoot, diagramFolderName, item.ExcalidrawPath),
                        PreviewPath = string.IsNullOrWhiteSpace(item.PreviewPath)
                            ? string.Empty
                            : Path.Combine(artifactRoot, diagramFolderName, item.PreviewPath)
                    };
                }
            }
        }

        if (!File.Exists(path))
        {
            return new ArchitectureReviewStageDto
            {
                JavaRelatedFileCount = javaRelatedFileCount,
                JavaExcludedFileCount = javaExclusionCount,
                JavaWorkflowCount = javaWorkflowCount,
                JavaSqlSignatureCount = javaSqlSignatureCount,
                JavaRelatedFileSamples = javaRelatedSamples,
                JavaExclusionSamples = javaExclusionSamples,
                DiagramBundles = diagramBundles,
                SourceArtifactPath = path
            };
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
            ArchitecturePolicy = node["architecturePolicy"]?.GetValue<string>() ?? "module-first",
            Confidence = ParseDouble(node["confidence"], 0),
            RecommendedStructure = ParseStringArray(node["recommendedStructure"]?.ToJsonString() ?? "[]"),
            JavaRelatedFileCount = javaRelatedFileCount,
            JavaExcludedFileCount = javaExclusionCount,
            JavaWorkflowCount = javaWorkflowCount,
            JavaSqlSignatureCount = javaSqlSignatureCount,
            JavaRelatedFileSamples = javaRelatedSamples,
            JavaExclusionSamples = javaExclusionSamples,
            DiagramBundles = diagramBundles,
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

        var workflowLanes = new List<WorkflowLaneDto>();
        var workflowMapPath = Path.Combine(artifactRoot, "test-plan-generation", "workflow-test-map.json");
        if (File.Exists(workflowMapPath))
        {
            var workflowMapNode = JsonNode.Parse(await File.ReadAllTextAsync(workflowMapPath, cancellationToken)) as JsonObject;
            if (workflowMapNode?["workflows"] is JsonArray workflows)
            {
                workflowLanes = workflows
                    .Select(static w => w as JsonObject)
                    .Where(static w => w is not null)
                    .Select(w => new WorkflowLaneDto
                    {
                        WorkflowName = w!["workflowName"]?.GetValue<string>() ?? string.Empty,
                        EntryRoute = w["entryRoute"]?.GetValue<string>() ?? string.Empty,
                        Categories = (w["categories"] as JsonArray)?.Select(static c => c?.GetValue<string>() ?? string.Empty)
                            .Where(static c => !string.IsNullOrWhiteSpace(c)).ToList() ?? [],
                        ProvenanceType = (w["provenance"] as JsonObject)?["type"]?.GetValue<string>() ?? string.Empty,
                        Confidence = ParseDouble((w["provenance"] as JsonObject)?["confidence"], 0)
                    })
                    .Select(w => new WorkflowLaneDto
                    {
                        WorkflowName = w.WorkflowName,
                        EntryRoute = w.EntryRoute,
                        Categories = w.Categories.Where(c => !IsApiCategory(c)).ToList(),
                        ProvenanceType = w.ProvenanceType,
                        Confidence = w.Confidence
                    })
                    .Where(static w => !string.IsNullOrWhiteSpace(w.WorkflowName))
                    .ToList();
            }
        }

        return new TestPlanStageDto
        {
            ExistingTestsFound = existingTestsFound,
            NewTestsSuggested = ParseStringArray(node["newTestsSuggested"]?.ToJsonString() ?? "[]"),
            TestCategories = categoryItems,
            WorkflowLanes = workflowLanes,
            CoverageSummary = node["coverageSummary"]?.GetValue<string>() ?? string.Empty,
            ScopeApplied = ParseScopeApplied(node["scopeApplied"]),
            Confidence = ParseDouble(node["confidence"], 0),
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
    AND LOWER(COALESCE(category, '')) <> 'api'
ORDER BY CASE category
    WHEN 'Unit' THEN 1
    WHEN 'Integration' THEN 2
    WHEN 'E2E' THEN 3
        WHEN 'Edge Case' THEN 4
        WHEN 'Playwright / E2E Browser' THEN 5
        WHEN 'Playwright / Browser Verification' THEN 5
        WHEN 'DevTools Diagnostics' THEN 6
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
        var generatedTestsArtifact = metrics?["generatedTestsArtifact"]?.GetValue<string>() ?? string.Empty;
        var generatedExecutableTest = metrics?["generatedExecutableTest"]?.GetValue<string>() ?? string.Empty;
        var generatedExecutableArtifact = metrics?["generatedExecutableArtifact"]?.GetValue<string>() ?? string.Empty;

        generatedTestsArtifact = NormalizeArtifactPath(artifactRoot, generatedTestsArtifact);
        generatedExecutableTest = NormalizeArtifactPath(artifactRoot, generatedExecutableTest);
        generatedExecutableArtifact = NormalizeArtifactPath(artifactRoot, generatedExecutableArtifact);
        var scenarios = new List<PlaywrightScenarioDto>();
        
        // Try to load generated tests blueprint for rich metadata
        var generatedTestsBlueprint = new Dictionary<string, JsonObject>();
        if (!string.IsNullOrWhiteSpace(generatedTestsArtifact))
        {
            var blueprintPath = Path.Combine(artifactRoot, generatedTestsArtifact);
            var blueprintNode = await ReadJsonObjectFileAsync(blueprintPath, cancellationToken);
            if (blueprintNode?["generatedTests"] is JsonArray generatedTestsArray)
            {
                foreach (var test in generatedTestsArray.OfType<JsonObject>())
                {
                    var testName = test["name"]?.GetValue<string>() ?? string.Empty;
                    if (!string.IsNullOrWhiteSpace(testName))
                    {
                        generatedTestsBlueprint[testName] = test;
                    }
                }
            }
        }
        
        if (metrics?["scenarios"] is JsonArray scenarioArray)
        {
            scenarios = scenarioArray
                .Select(static item => item as JsonObject)
                .Where(static item => item is not null)
                .Select(item => 
                {
                    var name = item!["name"]?.GetValue<string>() ?? string.Empty;
                    var status = item["status"]?.GetValue<string>() ?? string.Empty;
                    var notes = item["notes"]?.GetValue<string>() ?? string.Empty;
                    
                    // Try to enrich with blueprint data
                    string? workflowName = null;
                    string? targetRoute = null;
                    var coverage = new List<string>();
                    var generated = false;
                    var generatedFrom = new List<string>();
                    string? provenanceType = null;
                    double confidence = 0.0;
                    
                    if (generatedTestsBlueprint.TryGetValue(name, out var blueprintTest))
                    {
                        generated = true;
                        
                        if (blueprintTest["coverage"] is JsonArray coverageArray)
                        {
                            coverage = coverageArray
                                .Select(static c => c?.GetValue<string>() ?? string.Empty)
                                .Where(static c => !string.IsNullOrWhiteSpace(c))
                                .ToList();
                        }
                        
                        if (blueprintTest["generatedFrom"] is JsonArray generatedFromArray)
                        {
                            generatedFrom = generatedFromArray
                                .Select(static gf => gf?.GetValue<string>() ?? string.Empty)
                                .Where(static gf => !string.IsNullOrWhiteSpace(gf))
                                .ToList();
                            
                            // Extract target route from generatedFrom
                            targetRoute = generatedFrom.FirstOrDefault(gf => gf.StartsWith("route:"))?.Replace("route:", "").Trim();
                        }
                        
                        if (blueprintTest["provenance"] is JsonObject provenance)
                        {
                            provenanceType = provenance["type"]?.GetValue<string>();
                            if (provenance["confidence"] is JsonValue confValue)
                            {
                                confidence = confValue.TryGetValue(out double conf) ? conf : 0.0;
                            }
                        }
                        
                        // Extract workflow name from coverage or from name structure
                        if (coverage.Any())
                        {
                            workflowName = coverage.FirstOrDefault();
                        }
                    }
                    
                    return new PlaywrightScenarioDto
                    {
                        Name = name,
                        Status = status,
                        Notes = notes,
                        WorkflowName = workflowName,
                        TargetRoute = targetRoute,
                        Coverage = coverage,
                        Generated = generated,
                        GeneratedFrom = generatedFrom,
                        ProvenanceType = provenanceType,
                        Confidence = confidence
                    };
                })
                .ToList();
        }

        var consolePath = Path.Combine(artifactRoot, "playwright-browser-verification", "console-logs.json");
        var networkPath = Path.Combine(artifactRoot, "playwright-browser-verification", "network-failures.json");
        var domPath = Path.Combine(artifactRoot, "playwright-browser-verification", "dom-state.json");
        var runtimePath = Path.Combine(artifactRoot, "playwright-browser-verification", "runtime-issues.json");
        var perfPath = Path.Combine(artifactRoot, "playwright-browser-verification", "performance-observations.json");
        var screenshotRoot = Path.Combine(artifactRoot, "playwright-browser-verification", "screenshots");
        var executionLogPath = Path.Combine(artifactRoot, "playwright-browser-verification", "execution-log.txt");
        var inputOverridesPath = Path.Combine(artifactRoot, "playwright-browser-verification", "user-input-overrides.json");
        var resultPath = Path.Combine(artifactRoot, "playwright-browser-verification", "result.json");

        string executionCommand = string.Empty;
        string executionWorkingDirectory = string.Empty;
        int? executionReturnCode = null;
        var failureSnippets = new List<string>();

        var resultNode = await ReadJsonObjectFileAsync(resultPath, cancellationToken);
        if (resultNode is not null && resultNode["trace"] is JsonObject trace)
        {
            if (trace["command"] is JsonArray commandArray)
            {
                executionCommand = string.Join(' ', commandArray
                    .Select(static token => token?.GetValue<string>() ?? string.Empty)
                    .Where(static token => !string.IsNullOrWhiteSpace(token)));
            }

            executionWorkingDirectory = trace["cwd"]?.GetValue<string>() ?? string.Empty;
            if (trace["returnCode"] is JsonValue returnCodeNode)
            {
                executionReturnCode = returnCodeNode.GetValue<int>();
            }
        }

        if (resultNode is not null && resultNode["findings"] is JsonArray findingsArray)
        {
            failureSnippets = findingsArray
                .Select(static item => item as JsonObject)
                .Where(static item => item is not null)
                .Select(static item => ToFindingSnippet(item!))
                .Where(static item => !string.IsNullOrWhiteSpace(item))
                .Take(5)
                .ToList();
        }

        var consoleEntries = await ReadStringArrayFileAsync(consolePath, cancellationToken);
        var consoleErrors = consoleEntries.Where(static e => e.Contains("error", StringComparison.OrdinalIgnoreCase) || e.Contains("TypeError", StringComparison.OrdinalIgnoreCase)).ToList();
        var consoleWarnings = consoleEntries.Where(static e => e.Contains("warn", StringComparison.OrdinalIgnoreCase) || e.Contains("warning", StringComparison.OrdinalIgnoreCase)).ToList();
        var inputOverridesJson = File.Exists(inputOverridesPath)
            ? await File.ReadAllTextAsync(inputOverridesPath, cancellationToken)
            : string.Empty;
        var needInputKeywords = new[] { "login", "invalid", "valid", "form", "dropdown", "select", "checklist", "report", "submit" };
        var inputOverridesRecommended = string.IsNullOrWhiteSpace(inputOverridesJson)
            && scenarios.Any(s => needInputKeywords.Any(k => s.Name.Contains(k, StringComparison.OrdinalIgnoreCase)));

        return new PlaywrightEvidenceDto
        {
            Status = row.GetString("status"),
            Summary = row.GetString("summary"),
            ExecutionCommand = executionCommand,
            ExecutionWorkingDirectory = executionWorkingDirectory,
            ExecutionReturnCode = executionReturnCode,
            ExecutionLogPath = File.Exists(executionLogPath) ? executionLogPath : string.Empty,
            GeneratedTestsArtifact = generatedTestsArtifact,
            GeneratedExecutableTest = generatedExecutableTest,
            GeneratedExecutableArtifact = generatedExecutableArtifact,
            InputOverridesPath = File.Exists(inputOverridesPath) ? inputOverridesPath : string.Empty,
            InputOverridesJson = inputOverridesJson,
            InputOverridesRecommended = inputOverridesRecommended,
            FailureSnippets = failureSnippets,
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
                .Select(path => NormalizeArtifactPath(artifactRoot, path))
                .Where(static path => !string.IsNullOrWhiteSpace(path))
                .ToList()
        };
    }

    private static string NormalizeArtifactPath(string artifactRoot, string maybePath)
    {
        if (string.IsNullOrWhiteSpace(maybePath))
        {
            return string.Empty;
        }

        try
        {
            if (Path.IsPathRooted(maybePath))
            {
                return Path.GetFullPath(maybePath);
            }

            var combined = Path.GetFullPath(Path.Combine(artifactRoot, maybePath));
            if (File.Exists(combined) || Directory.Exists(combined))
            {
                return combined;
            }

            var rootCombined = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), maybePath));
            return rootCombined;
        }
        catch
        {
            return maybePath;
        }
    }

    private static string ToFindingSnippet(JsonObject finding)
    {
        var findingType = finding["type"]?.GetValue<string>() ?? string.Empty;
        var message = finding["message"]?.GetValue<string>() ?? string.Empty;
        var evidence = finding["evidence"]?.GetValue<string>() ?? string.Empty;

        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(findingType))
        {
            parts.Add($"[{findingType}]");
        }
        if (!string.IsNullOrWhiteSpace(message))
        {
            parts.Add(message.Trim());
        }
        if (!string.IsNullOrWhiteSpace(evidence))
        {
            parts.Add($"evidence: {evidence.Trim()}");
        }

        return string.Join(" ", parts).Trim();
    }

    private static async Task<JsonObject?> ReadJsonObjectFileAsync(string path, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            return null;
        }

        try
        {
            var text = await File.ReadAllTextAsync(path, cancellationToken);
            return JsonNode.Parse(text) as JsonObject;
        }
        catch
        {
            return null;
        }
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
        var workflowPath = Path.Combine(artifactRoot, "parity-verification", "workflow-parity-summary.json");
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
        var workflowParity = await ParseWorkflowParityAsync(workflowPath, cancellationToken);

        return new ParityStageDto
        {
            ParityScore = (int)(node["parityScore"]?.GetValue<double>() ?? 0),
            TotalChecks = checks.Count,
            PassedChecks = Math.Max(0, checks.Count - failed),
            FailedChecks = failed,
            Confidence = ParseDouble(node["confidence"], 0),
            Checks = checks,
            SqlParity = ParseSqlParity(node["sqlParity"]),
            WorkflowParity = workflowParity,
            DependencyParity = ParseDependencyParity(node["dependencyParity"]),
            Gaps = ParseStringArray(node["gaps"]?.ToJsonString() ?? "[]"),
            SourceArtifactPath = path
        };
    }

    private static async Task<List<WorkflowParityDto>> ParseWorkflowParityAsync(string path, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            return [];
        }

        try
        {
            var node = JsonNode.Parse(await File.ReadAllTextAsync(path, cancellationToken)) as JsonObject;
            if (node?["workflows"] is not JsonArray workflows)
            {
                return [];
            }

            return workflows
                .Select(static w => w as JsonObject)
                .Where(static w => w is not null)
                .Select(static w =>
                {
                    var provenance = ParseProvenance(w!["provenance"]);
                    return new WorkflowParityDto
                    {
                        WorkflowName = w["workflowName"]?.GetValue<string>() ?? string.Empty,
                        Status = w["status"]?.GetValue<string>() ?? "unknown",
                        PreservationScore = ParseDouble(w["preservationScore"], 0),
                        CsharpEntryPoint = (w["csharp"] as JsonObject)?["entryPoint"]?.GetValue<string>() ?? string.Empty,
                        JavaWorkflowName = (w["java"] as JsonObject)?["workflowName"]?.GetValue<string>() ?? string.Empty,
                        JavaEntryPoint = (w["java"] as JsonObject)?["entryPoint"]?.GetValue<string>() ?? string.Empty,
                        ProvenanceType = provenance.Type,
                        Confidence = provenance.Confidence
                    };
                })
                .Where(static w => !string.IsNullOrWhiteSpace(w.WorkflowName))
                .ToList();
        }
        catch
        {
            return [];
        }
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
        var workflowNames = ParseMultilineOrCsv(draft.WorkflowNamesText);
        var convertedRoots = ParseMultilineOrCsv(draft.ConvertedRootsText);
        var legacyBackendRoots = ParseMultilineOrCsv(draft.LegacyBackendRootsText);
        var legacyFrontendRoots = ParseMultilineOrCsv(draft.LegacyFrontendRootsText);

        if (convertedRoots.Count == 0 && !string.IsNullOrWhiteSpace(draft.ConvertedSourceRoot))
        {
            convertedRoots.Add(draft.ConvertedSourceRoot.Trim());
        }

        if (legacyBackendRoots.Count == 0)
        {
            var backendFallback = string.IsNullOrWhiteSpace(draft.LegacyBackendRoot)
                ? draft.LegacySourceRoot
                : draft.LegacyBackendRoot;

            if (!string.IsNullOrWhiteSpace(backendFallback))
            {
                legacyBackendRoots.Add(backendFallback.Trim());
            }
        }

        if (legacyFrontendRoots.Count == 0 && !string.IsNullOrWhiteSpace(draft.LegacyFrontendRoot))
        {
            legacyFrontendRoots.Add(draft.LegacyFrontendRoot.Trim());
        }

        var startUrl = ResolveTargetUrl((draft.ModuleStartUrl ?? string.Empty).Trim(), normalizedBaseUrl);
        var dotnetTestTarget = string.IsNullOrWhiteSpace(draft.DotnetTestTarget)
            ? draft.ConvertedModuleRoot.Trim()
            : draft.DotnetTestTarget.Trim();

        var payload = new
        {
            runId = string.IsNullOrWhiteSpace(draft.RunId) ? "run-001" : draft.RunId.Trim(),
            moduleName = draft.ModuleName.Trim(),
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
            keywords = ParseMultilineOrCsv(draft.KeywordsText),
            controllerHints = ParseMultilineOrCsv(draft.ControllerActionHintsText),
            viewHints = ParseMultilineOrCsv(draft.JspFolderHintsText),
            expectedEndUrls = ResolveKnownUrls(ParseMultilineOrCsv(draft.ExpectedTerminalUrlsText), normalizedBaseUrl)
        };

        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
    }

    private static List<string> ParseMultilineOrCsv(string? input)
    {
        return (input ?? string.Empty)
            .Split(new[] { "\r\n", "\n", "\r", "," }, StringSplitOptions.RemoveEmptyEntries)
            .Select(static value => value.Trim())
            .Where(static value => !string.IsNullOrWhiteSpace(value))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
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

    private static ScopeContextDto ParseScopeContext(JsonNode? node)
    {
        if (node is not JsonObject obj)
        {
            return new ScopeContextDto();
        }

        return new ScopeContextDto
        {
            StrictModuleOnly = obj["strictModuleOnly"]?.GetValue<bool>() ?? true,
            ScopeHint = obj["scopeHint"]?.GetValue<string>() ?? string.Empty,
            TargetUrlPath = obj["targetUrlPath"]?.GetValue<string>() ?? string.Empty,
            AllowedCrossModules = ParseStringArray(obj["allowedCrossModules"]?.ToJsonString() ?? "[]"),
            ScopeTokens = ParseStringArray(obj["scopeTokens"]?.ToJsonString() ?? "[]")
        };
    }

    private static ScopeAppliedDto ParseScopeApplied(JsonNode? node)
    {
        if (node is not JsonObject obj)
        {
            return new ScopeAppliedDto();
        }

        return new ScopeAppliedDto
        {
            ScopeTerms = ParseStringArray(obj["scopeTerms"]?.ToJsonString() ?? "[]"),
            TargetUrl = obj["targetUrl"]?.GetValue<string>() ?? string.Empty,
            ScopeHint = obj["scopeHint"]?.GetValue<string>() ?? string.Empty
        };
    }

    private static DependencyParityDto ParseDependencyParity(JsonNode? node)
    {
        if (node is not JsonObject obj)
        {
            return new DependencyParityDto();
        }

        return new DependencyParityDto
        {
            AllowedCrossModules = ParseStringArray(obj["allowedCrossModules"]?.ToJsonString() ?? "[]"),
            Dependencies = ParseStringArray(obj["dependencies"]?.ToJsonString() ?? "[]"),
            Violations = ParseStringArray(obj["violations"]?.ToJsonString() ?? "[]")
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
