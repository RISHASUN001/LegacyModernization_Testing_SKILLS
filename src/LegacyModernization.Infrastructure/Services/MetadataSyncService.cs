using System.Data;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using Dapper;
using LegacyModernization.Application.Contracts;
using LegacyModernization.Infrastructure.Abstractions;
using LegacyModernization.Infrastructure.Options;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace LegacyModernization.Infrastructure.Services;

public sealed class MetadataSyncService : IMetadataSyncService
{
    private static readonly Dictionary<string, string> SkillToStage = new(StringComparer.OrdinalIgnoreCase)
    {
        ["module-discovery"] = "discovery",
        ["legacy-logic-extraction"] = "logic-understanding",
        ["module-documentation"] = "logic-understanding",
        ["clean-architecture-assessment"] = "architecture-review",
        ["test-plan-generation"] = "test-plan",
        ["unit-test-execution"] = "execution",
        ["integration-test-execution"] = "execution",
        ["e2e-test-execution"] = "execution",
        ["api-test-execution"] = "execution",
        ["edge-case-testing"] = "execution",
        ["playwright-browser-verification"] = "execution",
        ["failure-diagnosis"] = "findings",
        ["lessons-learned"] = "findings",
        ["iteration-comparison"] = "iteration-comparison",
        ["parity-verification"] = "findings"
    };

    private static readonly Dictionary<string, (string Category, string Purpose)> TestCategoryBySkill = new(StringComparer.OrdinalIgnoreCase)
    {
        ["unit-test-execution"] = ("Unit", "Validate business logic and domain rules quickly in isolation."),
        ["integration-test-execution"] = ("Integration", "Validate repository, database mapping, and cross-layer behavior."),
        ["e2e-test-execution"] = ("E2E", "Validate full user journeys across services and UI boundaries."),
        ["api-test-execution"] = ("API", "Validate HTTP contract compatibility and endpoint behavior."),
        ["edge-case-testing"] = ("Edge Case", "Validate low-frequency but high-impact behavior and resilience."),
        ["playwright-browser-verification"] = ("Playwright / Browser Verification", "Validate browser behavior with console/network/runtime evidence.")
    };

    private readonly PlatformPathsOptions _paths;
    private readonly ISqliteConnectionFactory _connectionFactory;
    private readonly ILogger<MetadataSyncService> _logger;

    public MetadataSyncService(
        IOptions<PlatformPathsOptions> options,
        ISqliteConnectionFactory connectionFactory,
        ILogger<MetadataSyncService> logger)
    {
        _paths = options.Value;
        _connectionFactory = connectionFactory;
        _logger = logger;
    }

    public async Task SyncAsync(CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(_paths.DataRoot);
        Directory.CreateDirectory(_paths.ArtifactsRoot);
        Directory.CreateDirectory(_paths.SkillsRoot);
        Directory.CreateDirectory(_paths.RunInputsRoot);

        await using var connection = await _connectionFactory.CreateOpenConnectionAsync(cancellationToken);
        await using var transaction = connection.BeginTransaction();

        await connection.ExecuteAsync(new CommandDefinition(GetDropSql(), transaction: transaction, cancellationToken: cancellationToken));
        await connection.ExecuteAsync(new CommandDefinition(GetCreateSql(), transaction: transaction, cancellationToken: cancellationToken));

        await LoadSkillsAsync(connection, transaction, cancellationToken);
        var runBundles = await LoadRunsAsync(cancellationToken);
        await PersistRunsAsync(connection, transaction, runBundles, cancellationToken);
        await PersistIterationDeltasAsync(connection, transaction, cancellationToken);

        transaction.Commit();

        _logger.LogInformation("Metadata sync completed. Runs={Runs}, Skills={Skills}", runBundles.Count, runBundles.Sum(static bundle => bundle.Skills.Count));
    }

    private async Task LoadSkillsAsync(IDbConnection connection, IDbTransaction transaction, CancellationToken cancellationToken)
    {
        if (!Directory.Exists(_paths.SkillsRoot))
        {
            return;
        }

        var skillDirs = Directory.GetDirectories(_paths.SkillsRoot)
            .Where(static dir => !Path.GetFileName(dir).StartsWith("_", StringComparison.OrdinalIgnoreCase))
            .OrderBy(static dir => dir, StringComparer.OrdinalIgnoreCase)
            .ToList();

        const string sql = @"
INSERT INTO skills
(name, stage, category, script_entry, required_inputs_json, optional_inputs_json, output_files_json, artifact_folders_json, dependencies_json, summary_output_type, result_contract_version, purpose, skill_markdown)
VALUES
(@Name, @Stage, @Category, @ScriptEntry, @RequiredInputsJson, @OptionalInputsJson, @OutputFilesJson, @ArtifactFoldersJson, @DependenciesJson, @SummaryOutputType, @ResultContractVersion, @Purpose, @SkillMarkdown);";

        foreach (var skillDir in skillDirs)
        {
            var configPath = Path.Combine(skillDir, "config.json");
            var skillMdPath = Path.Combine(skillDir, "SKILL.md");
            if (!File.Exists(configPath) || !File.Exists(skillMdPath))
            {
                continue;
            }

            var config = JsonNode.Parse(await File.ReadAllTextAsync(configPath, cancellationToken)) as JsonObject;
            if (config is null)
            {
                continue;
            }

            var name = config["name"]?.GetValue<string>() ?? Path.GetFileName(skillDir);
            var stage = config["stage"]?.GetValue<string>() ?? SkillToStage.GetValueOrDefault(name, "execution");

            await connection.ExecuteAsync(new CommandDefinition(sql, new
            {
                Name = name,
                Stage = stage,
                Category = config["category"]?.GetValue<string>() ?? "analysis",
                ScriptEntry = config["scriptEntry"]?.GetValue<string>() ?? "run.py",
                RequiredInputsJson = config["requiredInputs"]?.ToJsonString() ?? "[]",
                OptionalInputsJson = config["optionalInputs"]?.ToJsonString() ?? "[]",
                OutputFilesJson = config["outputFiles"]?.ToJsonString() ?? "[]",
                ArtifactFoldersJson = config["artifactFolders"]?.ToJsonString() ?? "[]",
                DependenciesJson = config["dependencies"]?.ToJsonString() ?? "[]",
                SummaryOutputType = config["summaryOutputType"]?.GetValue<string>() ?? "structured",
                ResultContractVersion = config["resultContractVersion"]?.GetValue<string>() ?? "2.0",
                Purpose = config["purpose"]?.GetValue<string>() ?? string.Empty,
                SkillMarkdown = await File.ReadAllTextAsync(skillMdPath, cancellationToken)
            }, transaction, cancellationToken: cancellationToken));
        }
    }

    private async Task<List<ParsedRunBundle>> LoadRunsAsync(CancellationToken cancellationToken)
    {
        var bundles = new List<ParsedRunBundle>();
        if (!Directory.Exists(_paths.ArtifactsRoot))
        {
            return bundles;
        }

        foreach (var moduleDir in Directory.GetDirectories(_paths.ArtifactsRoot).OrderBy(static dir => dir, StringComparer.OrdinalIgnoreCase))
        {
            var moduleName = Path.GetFileName(moduleDir);

            foreach (var runDir in Directory.GetDirectories(moduleDir).OrderBy(static dir => dir, StringComparer.OrdinalIgnoreCase))
            {
                var bundle = new ParsedRunBundle
                {
                    ModuleName = moduleName,
                    RunId = Path.GetFileName(runDir),
                    ArtifactRoot = runDir
                };

                var runInputPath = Path.Combine(runDir, "module-run-input.json");
                if (File.Exists(runInputPath))
                {
                    var runInput = JsonNode.Parse(await File.ReadAllTextAsync(runInputPath, cancellationToken)) as JsonObject;
                    if (runInput is not null)
                    {
                        bundle.BaseUrl = runInput["baseUrl"]?.GetValue<string>() ?? string.Empty;
                        bundle.BrsPath = runInput["brsPath"]?.GetValue<string>() ?? string.Empty;
                        bundle.LegacySourceRoot = runInput["legacySourceRoot"]?.GetValue<string>() ?? string.Empty;
                        bundle.ConvertedSourceRoot = runInput["convertedSourceRoot"]?.GetValue<string>() ?? string.Empty;
                    }
                }

                foreach (var skillDir in Directory.GetDirectories(runDir).OrderBy(static dir => dir, StringComparer.OrdinalIgnoreCase))
                {
                    var resultPath = Path.Combine(skillDir, "result.json");
                    if (!File.Exists(resultPath))
                    {
                        continue;
                    }

                    var result = JsonNode.Parse(await File.ReadAllTextAsync(resultPath, cancellationToken)) as JsonObject;
                    if (result is null)
                    {
                        continue;
                    }

                    var skillName = result["skillName"]?.GetValue<string>() ?? Path.GetFileName(skillDir);
                    var stage = result["stage"]?.GetValue<string>() ?? SkillToStage.GetValueOrDefault(skillName, "execution");

                    bundle.Skills.Add(new ParsedSkillExecution
                    {
                        SkillName = skillName,
                        Stage = stage,
                        Status = result["status"]?.GetValue<string>() ?? "unknown",
                        StartedAt = result["startedAt"]?.GetValue<string>() ?? DateTime.UtcNow.ToString("O"),
                        EndedAt = result["endedAt"]?.GetValue<string>() ?? DateTime.UtcNow.ToString("O"),
                        Summary = result["summary"]?.GetValue<string>() ?? string.Empty,
                        MetricsJson = result["metrics"]?.ToJsonString() ?? "{}",
                        ArtifactsJson = result["artifacts"]?.ToJsonString() ?? "[]",
                        FindingsJson = result["findings"]?.ToJsonString() ?? "[]",
                        RecommendationsJson = result["recommendations"]?.ToJsonString() ?? "[]",
                        ResultContractVersion = result["resultContractVersion"]?.GetValue<string>() ?? "2.0",
                        ResultJson = result.ToJsonString(),
                        RawResult = result
                    });
                }

                if (bundle.Skills.Count > 0)
                {
                    bundles.Add(bundle);
                }
            }
        }

        return bundles;
    }

    private async Task PersistRunsAsync(IDbConnection connection, IDbTransaction transaction, List<ParsedRunBundle> bundles, CancellationToken cancellationToken)
    {
        const string insertModuleSql = @"
INSERT OR IGNORE INTO modules(name, legacy_source_root, converted_source_root, created_at)
VALUES(@Name, @LegacySourceRoot, @ConvertedSourceRoot, @CreatedAt);";

        const string selectModuleSql = "SELECT id FROM modules WHERE name=@Name LIMIT 1;";

        const string insertRunSql = @"
INSERT INTO runs(module_id, run_id, status, started_at, ended_at, summary, base_url, brs_path, artifact_root, created_at)
VALUES(@ModuleId, @RunId, @Status, @StartedAt, @EndedAt, @Summary, @BaseUrl, @BrsPath, @ArtifactRoot, @CreatedAt);";

        const string selectRunSql = "SELECT id FROM runs WHERE module_id=@ModuleId AND run_id=@RunId LIMIT 1;";

        const string insertSkillSql = @"
INSERT INTO skill_executions
(run_fk, skill_name, stage, status, started_at, ended_at, summary, metrics_json, artifacts_json, findings_json, recommendations_json, result_contract_version, result_json)
VALUES
(@RunFk, @SkillName, @Stage, @Status, @StartedAt, @EndedAt, @Summary, @MetricsJson, @ArtifactsJson, @FindingsJson, @RecommendationsJson, @ResultContractVersion, @ResultJson);";

        foreach (var bundle in bundles)
        {
            await connection.ExecuteAsync(new CommandDefinition(insertModuleSql, new
            {
                Name = bundle.ModuleName,
                LegacySourceRoot = bundle.LegacySourceRoot,
                ConvertedSourceRoot = bundle.ConvertedSourceRoot,
                CreatedAt = DateTime.UtcNow.ToString("O")
            }, transaction, cancellationToken: cancellationToken));

            var moduleId = await connection.ExecuteScalarAsync<long?>(new CommandDefinition(selectModuleSql, new { Name = bundle.ModuleName }, transaction, cancellationToken: cancellationToken));
            if (moduleId is null)
            {
                continue;
            }

            var orderedSkills = bundle.Skills.OrderBy(static s => s.StartedAt, StringComparer.OrdinalIgnoreCase).ToList();
            var startedAt = orderedSkills.FirstOrDefault()?.StartedAt ?? DateTime.UtcNow.ToString("O");
            var endedAt = orderedSkills.LastOrDefault()?.EndedAt ?? DateTime.UtcNow.ToString("O");
            var status = orderedSkills.Any(static s => s.Status.Equals("failed", StringComparison.OrdinalIgnoreCase)) ? "failed" : "passed";
            var summary = $"{orderedSkills.Count(static s => s.Status.Equals("passed", StringComparison.OrdinalIgnoreCase))}/{orderedSkills.Count} skills passed.";

            await connection.ExecuteAsync(new CommandDefinition(insertRunSql, new
            {
                ModuleId = moduleId.Value,
                RunId = bundle.RunId,
                Status = status,
                StartedAt = startedAt,
                EndedAt = endedAt,
                Summary = summary,
                BaseUrl = bundle.BaseUrl,
                BrsPath = bundle.BrsPath,
                ArtifactRoot = bundle.ArtifactRoot,
                CreatedAt = DateTime.UtcNow.ToString("O")
            }, transaction, cancellationToken: cancellationToken));

            var runFk = await connection.ExecuteScalarAsync<long?>(new CommandDefinition(selectRunSql, new { ModuleId = moduleId.Value, RunId = bundle.RunId }, transaction, cancellationToken: cancellationToken));
            if (runFk is null)
            {
                continue;
            }

            foreach (var skill in orderedSkills)
            {
                await connection.ExecuteAsync(new CommandDefinition(insertSkillSql, new
                {
                    RunFk = runFk.Value,
                    SkillName = skill.SkillName,
                    Stage = skill.Stage,
                    Status = skill.Status,
                    StartedAt = skill.StartedAt,
                    EndedAt = skill.EndedAt,
                    Summary = skill.Summary,
                    MetricsJson = skill.MetricsJson,
                    ArtifactsJson = skill.ArtifactsJson,
                    FindingsJson = skill.FindingsJson,
                    RecommendationsJson = skill.RecommendationsJson,
                    ResultContractVersion = skill.ResultContractVersion,
                    ResultJson = skill.ResultJson
                }, transaction, cancellationToken: cancellationToken));

                await PersistFindingsAsync(connection, transaction, runFk.Value, skill, cancellationToken);
                await PersistRecommendationsAsync(connection, transaction, runFk.Value, skill, cancellationToken);
                await PersistTestCategoryIfApplicableAsync(connection, transaction, runFk.Value, skill, cancellationToken);
            }
        }
    }

    private async Task PersistFindingsAsync(IDbConnection connection, IDbTransaction transaction, long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (skill.RawResult["findings"] is not JsonArray findingArray)
        {
            return;
        }

        const string sql = @"
INSERT INTO finding_records
(run_fk, stage, skill_name, scenario, issue_type, message, likely_cause, evidence, severity, status, confidence, affected_files_json, recommendation, resolved_in_run_id, resolution_notes)
VALUES
(@RunFk, @Stage, @SkillName, @Scenario, @IssueType, @Message, @LikelyCause, @Evidence, @Severity, @Status, @Confidence, @AffectedFilesJson, @Recommendation, @ResolvedInRunId, @ResolutionNotes);";

        foreach (var findingNode in findingArray)
        {
            var finding = findingNode as JsonObject;
            await connection.ExecuteAsync(new CommandDefinition(sql, new
            {
                RunFk = runFk,
                Stage = skill.Stage,
                SkillName = skill.SkillName,
                Scenario = finding?["scenario"]?.GetValue<string>() ?? string.Empty,
                IssueType = finding?["type"]?.GetValue<string>() ?? "General",
                Message = finding?["message"]?.GetValue<string>() ?? findingNode?.ToJsonString() ?? string.Empty,
                LikelyCause = finding?["likelyCause"]?.GetValue<string>() ?? finding?["cause"]?.GetValue<string>() ?? string.Empty,
                Evidence = finding?["evidence"]?.GetValue<string>() ?? string.Empty,
                Severity = finding?["severity"]?.GetValue<string>() ?? "medium",
                Status = finding?["status"]?.GetValue<string>() ?? "open",
                Confidence = ParseDouble(finding?["confidence"], 0.65),
                AffectedFilesJson = finding?["affectedFiles"]?.ToJsonString() ?? "[]",
                Recommendation = string.Empty,
                ResolvedInRunId = finding?["resolvedInRunId"]?.GetValue<string>() ?? string.Empty,
                ResolutionNotes = finding?["resolutionNotes"]?.GetValue<string>() ?? string.Empty
            }, transaction, cancellationToken: cancellationToken));
        }
    }

    private async Task PersistRecommendationsAsync(IDbConnection connection, IDbTransaction transaction, long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (skill.RawResult["recommendations"] is not JsonArray recommendationArray)
        {
            return;
        }

        const string sql = @"
INSERT INTO recommendation_records
(run_fk, stage, skill_name, message, priority, evidence)
VALUES
(@RunFk, @Stage, @SkillName, @Message, @Priority, @Evidence);";

        foreach (var recommendationNode in recommendationArray)
        {
            var recommendationObject = recommendationNode as JsonObject;
            await connection.ExecuteAsync(new CommandDefinition(sql, new
            {
                RunFk = runFk,
                Stage = skill.Stage,
                SkillName = skill.SkillName,
                Message = recommendationObject?["message"]?.GetValue<string>() ?? recommendationNode?.GetValue<string>() ?? recommendationNode?.ToJsonString() ?? string.Empty,
                Priority = recommendationObject?["priority"]?.GetValue<string>() ?? "medium",
                Evidence = recommendationObject?["evidence"]?.GetValue<string>() ?? string.Empty
            }, transaction, cancellationToken: cancellationToken));
        }
    }

    private async Task PersistTestCategoryIfApplicableAsync(IDbConnection connection, IDbTransaction transaction, long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (!TestCategoryBySkill.TryGetValue(skill.SkillName, out var testInfo))
        {
            return;
        }

        var metrics = ParseMetrics(skill.MetricsJson);
        const string sql = @"
INSERT INTO test_category_results
(run_fk, category, purpose, scenarios_json, total, passed, failed, warnings, new_tests_added, logs_json, artifacts_json, source_skill, stage)
VALUES
(@RunFk, @Category, @Purpose, @ScenariosJson, @Total, @Passed, @Failed, @Warnings, @NewTestsAdded, @LogsJson, @ArtifactsJson, @SourceSkill, @Stage);";

        await connection.ExecuteAsync(new CommandDefinition(sql, new
        {
            RunFk = runFk,
            Category = testInfo.Category,
            Purpose = testInfo.Purpose,
            ScenariosJson = ExtractScenarioJson(skill.RawResult),
            Total = metrics.GetValueOrDefault("total"),
            Passed = metrics.GetValueOrDefault("passed"),
            Failed = metrics.GetValueOrDefault("failed"),
            Warnings = metrics.GetValueOrDefault("warnings"),
            NewTestsAdded = metrics.GetValueOrDefault("newTestsAdded"),
            LogsJson = BuildLogsJson(skill.ArtifactsJson),
            ArtifactsJson = skill.ArtifactsJson,
            SourceSkill = skill.SkillName,
            Stage = skill.Stage
        }, transaction, cancellationToken: cancellationToken));
    }

    private async Task PersistIterationDeltasAsync(IDbConnection connection, IDbTransaction transaction, CancellationToken cancellationToken)
    {
        var modules = await QueryRowsAsync(connection, "SELECT id, name FROM modules ORDER BY name;", null, transaction, cancellationToken);

        foreach (var module in modules)
        {
            var moduleId = module["id"]?.GetValue<long>() ?? 0;
            var runs = await QueryRowsAsync(connection, "SELECT id, run_id FROM runs WHERE module_id=@ModuleId ORDER BY run_id;", new { ModuleId = moduleId }, transaction, cancellationToken);

            JsonObject? previousRun = null;
            var previousFindingTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var previousTotalFailed = 0;

            foreach (var run in runs)
            {
                var runFk = run["id"]?.GetValue<long>() ?? 0;
                var runId = run["run_id"]?.GetValue<string>() ?? string.Empty;

                var testsAdded = (await connection.ExecuteScalarAsync<long?>(new CommandDefinition("SELECT COALESCE(SUM(new_tests_added),0) FROM test_category_results WHERE run_fk=@RunFk;", new { RunFk = runFk }, transaction, cancellationToken: cancellationToken))) ?? 0;
                var totalFailed = (int)((await connection.ExecuteScalarAsync<long?>(new CommandDefinition("SELECT COALESCE(SUM(failed),0) FROM test_category_results WHERE run_fk=@RunFk;", new { RunFk = runFk }, transaction, cancellationToken: cancellationToken))) ?? 0);
                var resolvedFindings = (await connection.ExecuteScalarAsync<long?>(new CommandDefinition("SELECT COUNT(1) FROM finding_records WHERE run_fk=@RunFk AND LOWER(status)='resolved';", new { RunFk = runFk }, transaction, cancellationToken: cancellationToken))) ?? 0;

                var currentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                var currentTypeRows = await QueryRowsAsync(connection, "SELECT DISTINCT issue_type FROM finding_records WHERE run_fk=@RunFk;", new { RunFk = runFk }, transaction, cancellationToken);
                foreach (var typeRow in currentTypeRows)
                {
                    var type = typeRow["issue_type"]?.GetValue<string>();
                    if (!string.IsNullOrWhiteSpace(type))
                    {
                        currentTypes.Add(type);
                    }
                }

                var newFindings = currentTypes.Except(previousFindingTypes, StringComparer.OrdinalIgnoreCase).Count();
                var testsFixed = previousRun is null ? 0 : Math.Max(0, previousTotalFailed - totalFailed);
                var failuresReduced = previousRun is null ? 0 : Math.Max(0, previousTotalFailed - totalFailed);
                var trend = ComputeTrend(previousRun is null, failuresReduced, newFindings, (int)resolvedFindings);
                var previousRunId = previousRun?["run_id"]?.GetValue<string>() ?? string.Empty;

                var deltaJson = JsonSerializer.Serialize(new
                {
                    testsAdded,
                    testsFixed,
                    failuresReduced,
                    newFindingsIntroduced = newFindings,
                    resolvedFindings,
                    progressionTrend = trend
                });

                await connection.ExecuteAsync(new CommandDefinition(@"
INSERT INTO iteration_deltas
(module_id, run_id, previous_run_id, tests_added, tests_fixed, failures_reduced, new_findings_introduced, resolved_findings, progression_trend, delta_json)
VALUES
(@ModuleId, @RunId, @PreviousRunId, @TestsAdded, @TestsFixed, @FailuresReduced, @NewFindingsIntroduced, @ResolvedFindings, @ProgressionTrend, @DeltaJson);",
                    new
                    {
                        ModuleId = moduleId,
                        RunId = runId,
                        PreviousRunId = previousRunId,
                        TestsAdded = testsAdded,
                        TestsFixed = testsFixed,
                        FailuresReduced = failuresReduced,
                        NewFindingsIntroduced = newFindings,
                        ResolvedFindings = resolvedFindings,
                        ProgressionTrend = trend,
                        DeltaJson = deltaJson
                    }, transaction, cancellationToken: cancellationToken));

                previousRun = run;
                previousTotalFailed = totalFailed;
                previousFindingTypes = currentTypes;
            }
        }
    }

    private static string ComputeTrend(bool isFirstRun, int failuresReduced, int newFindings, int resolvedFindings)
    {
        if (isFirstRun)
        {
            return "baseline";
        }

        if (failuresReduced > 0 && resolvedFindings >= newFindings)
        {
            return "improving";
        }

        if (newFindings > resolvedFindings)
        {
            return "regressing";
        }

        return "stable";
    }

    private static async Task<List<JsonObject>> QueryRowsAsync(IDbConnection connection, string sql, object? parameters, IDbTransaction transaction, CancellationToken cancellationToken)
    {
        var rows = await connection.QueryAsync(new CommandDefinition(sql, parameters, transaction, cancellationToken: cancellationToken));
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

    private static Dictionary<string, int> ParseMetrics(string json)
    {
        try
        {
            var node = JsonNode.Parse(json) as JsonObject;
            if (node is null)
            {
                return new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            }

            var result = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (var property in node)
            {
                if (property.Value is null)
                {
                    continue;
                }

                if (int.TryParse(property.Value.ToString(), out var parsed))
                {
                    result[property.Key] = parsed;
                }
            }

            return result;
        }
        catch
        {
            return new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        }
    }

    private static double ParseDouble(JsonNode? node, double fallback)
    {
        if (node is null)
        {
            return fallback;
        }

        return double.TryParse(node.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var value)
            ? value
            : fallback;
    }

    private static string ExtractScenarioJson(JsonObject rawResult)
    {
        if (rawResult["metrics"] is not JsonObject metrics || metrics["scenarios"] is not JsonArray scenarios)
        {
            return "[]";
        }

        var names = new JsonArray();
        foreach (var scenario in scenarios)
        {
            if (scenario is JsonObject objectScenario)
            {
                var name = objectScenario["name"]?.GetValue<string>() ?? string.Empty;
                if (!string.IsNullOrWhiteSpace(name))
                {
                    names.Add(name);
                }
            }
            else if (scenario is JsonValue value)
            {
                var text = value.GetValue<string>();
                if (!string.IsNullOrWhiteSpace(text))
                {
                    names.Add(text);
                }
            }
        }

        return names.ToJsonString();
    }

    private static string BuildLogsJson(string artifactsJson)
    {
        try
        {
            var artifacts = JsonNode.Parse(artifactsJson) as JsonArray;
            if (artifacts is null)
            {
                return "[]";
            }

            var logs = new JsonArray();
            foreach (var artifact in artifacts)
            {
                var path = artifact?.GetValue<string>() ?? string.Empty;
                if (string.IsNullOrWhiteSpace(path))
                {
                    continue;
                }

                if (path.EndsWith(".log", StringComparison.OrdinalIgnoreCase) ||
                    path.EndsWith(".txt", StringComparison.OrdinalIgnoreCase) ||
                    path.EndsWith("console-logs.json", StringComparison.OrdinalIgnoreCase) ||
                    path.EndsWith("network-failures.json", StringComparison.OrdinalIgnoreCase))
                {
                    logs.Add(path);
                }
            }

            return logs.ToJsonString();
        }
        catch
        {
            return "[]";
        }
    }

    private static string GetDropSql()
    {
        return @"
DROP TABLE IF EXISTS iteration_deltas;
DROP TABLE IF EXISTS recommendation_records;
DROP TABLE IF EXISTS finding_records;
DROP TABLE IF EXISTS test_category_results;
DROP TABLE IF EXISTS skill_executions;
DROP TABLE IF EXISTS runs;
DROP TABLE IF EXISTS modules;
DROP TABLE IF EXISTS skills;";
    }

    private static string GetCreateSql()
    {
        return @"
CREATE TABLE modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    legacy_source_root TEXT NOT NULL,
    converted_source_root TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    base_url TEXT NOT NULL,
    brs_path TEXT NOT NULL,
    artifact_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(module_id, run_id),
    FOREIGN KEY(module_id) REFERENCES modules(id)
);

CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    stage TEXT NOT NULL,
    category TEXT NOT NULL,
    script_entry TEXT NOT NULL,
    required_inputs_json TEXT NOT NULL,
    optional_inputs_json TEXT NOT NULL,
    output_files_json TEXT NOT NULL,
    artifact_folders_json TEXT NOT NULL,
    dependencies_json TEXT NOT NULL,
    summary_output_type TEXT NOT NULL,
    result_contract_version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    skill_markdown TEXT NOT NULL
);

CREATE TABLE skill_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_fk INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    artifacts_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    recommendations_json TEXT NOT NULL,
    result_contract_version TEXT NOT NULL,
    result_json TEXT NOT NULL,
    FOREIGN KEY(run_fk) REFERENCES runs(id)
);

CREATE TABLE test_category_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_fk INTEGER NOT NULL,
    category TEXT NOT NULL,
    purpose TEXT NOT NULL,
    scenarios_json TEXT NOT NULL,
    total INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    warnings INTEGER NOT NULL,
    new_tests_added INTEGER NOT NULL,
    logs_json TEXT NOT NULL,
    artifacts_json TEXT NOT NULL,
    source_skill TEXT NOT NULL,
    stage TEXT NOT NULL,
    FOREIGN KEY(run_fk) REFERENCES runs(id)
);

CREATE TABLE finding_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_fk INTEGER NOT NULL,
    stage TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    scenario TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    message TEXT NOT NULL,
    likely_cause TEXT NOT NULL,
    evidence TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    affected_files_json TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    resolved_in_run_id TEXT NOT NULL,
    resolution_notes TEXT NOT NULL,
    FOREIGN KEY(run_fk) REFERENCES runs(id)
);

CREATE TABLE recommendation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_fk INTEGER NOT NULL,
    stage TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    message TEXT NOT NULL,
    priority TEXT NOT NULL,
    evidence TEXT NOT NULL,
    FOREIGN KEY(run_fk) REFERENCES runs(id)
);

CREATE TABLE iteration_deltas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    previous_run_id TEXT NOT NULL,
    tests_added INTEGER NOT NULL,
    tests_fixed INTEGER NOT NULL,
    failures_reduced INTEGER NOT NULL,
    new_findings_introduced INTEGER NOT NULL,
    resolved_findings INTEGER NOT NULL,
    progression_trend TEXT NOT NULL,
    delta_json TEXT NOT NULL,
    FOREIGN KEY(module_id) REFERENCES modules(id)
);";
    }

    private sealed class ParsedRunBundle
    {
        public string ModuleName { get; init; } = string.Empty;
        public string RunId { get; init; } = string.Empty;
        public string LegacySourceRoot { get; set; } = string.Empty;
        public string ConvertedSourceRoot { get; set; } = string.Empty;
        public string BaseUrl { get; set; } = string.Empty;
        public string BrsPath { get; set; } = string.Empty;
        public string ArtifactRoot { get; init; } = string.Empty;
        public List<ParsedSkillExecution> Skills { get; } = [];
    }

    private sealed class ParsedSkillExecution
    {
        public string SkillName { get; init; } = string.Empty;
        public string Stage { get; init; } = string.Empty;
        public string Status { get; init; } = string.Empty;
        public string StartedAt { get; init; } = string.Empty;
        public string EndedAt { get; init; } = string.Empty;
        public string Summary { get; init; } = string.Empty;
        public string MetricsJson { get; init; } = "{}";
        public string ArtifactsJson { get; init; } = "[]";
        public string FindingsJson { get; init; } = "[]";
        public string RecommendationsJson { get; init; } = "[]";
        public string ResultContractVersion { get; init; } = "2.0";
        public string ResultJson { get; init; } = "{}";
        public JsonObject RawResult { get; init; } = [];
    }
}
