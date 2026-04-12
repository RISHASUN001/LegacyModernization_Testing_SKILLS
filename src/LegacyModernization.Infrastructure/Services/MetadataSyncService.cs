using System.Text.Json;
using System.Text.Json.Nodes;
using LegacyModernization.Application.Contracts;
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
    private readonly SqliteCli _sqlite;
    private readonly ILogger<MetadataSyncService> _logger;

    public MetadataSyncService(IOptions<PlatformPathsOptions> options, SqliteCli sqlite, ILogger<MetadataSyncService> logger)
    {
        _paths = options.Value;
        _sqlite = sqlite;
        _logger = logger;
    }

    public async Task SyncAsync(CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(_paths.DataRoot);
        Directory.CreateDirectory(_paths.ArtifactsRoot);
        Directory.CreateDirectory(_paths.SkillsRoot);
        Directory.CreateDirectory(_paths.RunInputsRoot);

        await _sqlite.ExecuteNonQueryAsync(GetDropSql(), cancellationToken);
        await _sqlite.ExecuteNonQueryAsync(GetCreateSql(), cancellationToken);

        await LoadSkillsAsync(cancellationToken);
        var runBundles = await LoadRunsAsync(cancellationToken);
        await PersistRunsAsync(runBundles, cancellationToken);
        await PersistIterationDeltasAsync(cancellationToken);

        _logger.LogInformation("Metadata sync completed. Runs={Runs} Skills={Skills}", runBundles.Count, runBundles.Sum(static bundle => bundle.Skills.Count));
    }

    private async Task LoadSkillsAsync(CancellationToken cancellationToken)
    {
        if (!Directory.Exists(_paths.SkillsRoot))
        {
            return;
        }

        var skillDirs = Directory.GetDirectories(_paths.SkillsRoot)
            .Where(static dir => !Path.GetFileName(dir).StartsWith("_", StringComparison.OrdinalIgnoreCase))
            .OrderBy(static dir => dir, StringComparer.OrdinalIgnoreCase)
            .ToList();

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
            var category = config["category"]?.GetValue<string>() ?? "analysis";
            var scriptEntry = config["scriptEntry"]?.GetValue<string>() ?? config["script_entry"]?.GetValue<string>() ?? "run.py";
            var purpose = config["purpose"]?.GetValue<string>() ?? string.Empty;
            var summaryOutputType = config["summaryOutputType"]?.GetValue<string>() ?? "structured";
            var resultContractVersion = config["resultContractVersion"]?.GetValue<string>() ?? "2.0";

            var requiredInputs = config["requiredInputs"]?.ToJsonString() ?? "[]";
            var optionalInputs = config["optionalInputs"]?.ToJsonString() ?? "[]";
            var outputFiles = config["outputFiles"]?.ToJsonString() ?? config["expectedOutputs"]?.ToJsonString() ?? "[]";
            var artifactFolders = config["artifactFolders"]?.ToJsonString() ?? config["artifactPaths"]?.ToJsonString() ?? "[]";
            var dependencies = config["dependencies"]?.ToJsonString() ?? "[]";

            var markdown = await File.ReadAllTextAsync(skillMdPath, cancellationToken);

            var sql = $@"
INSERT INTO skills
(name, stage, category, script_entry, required_inputs_json, optional_inputs_json, output_files_json, artifact_folders_json, dependencies_json, summary_output_type, result_contract_version, purpose, skill_markdown)
VALUES
('{SqliteCli.Escape(name)}', '{SqliteCli.Escape(stage)}', '{SqliteCli.Escape(category)}', '{SqliteCli.Escape(scriptEntry)}', '{SqliteCli.Escape(requiredInputs)}', '{SqliteCli.Escape(optionalInputs)}', '{SqliteCli.Escape(outputFiles)}', '{SqliteCli.Escape(artifactFolders)}', '{SqliteCli.Escape(dependencies)}', '{SqliteCli.Escape(summaryOutputType)}', '{SqliteCli.Escape(resultContractVersion)}', '{SqliteCli.Escape(purpose)}', '{SqliteCli.Escape(markdown)}');";

            await _sqlite.ExecuteNonQueryAsync(sql, cancellationToken);
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

    private async Task PersistRunsAsync(List<ParsedRunBundle> bundles, CancellationToken cancellationToken)
    {
        foreach (var bundle in bundles)
        {
            var moduleSql = $@"
INSERT OR IGNORE INTO modules(name, legacy_source_root, converted_source_root, created_at)
VALUES('{SqliteCli.Escape(bundle.ModuleName)}', '{SqliteCli.Escape(bundle.LegacySourceRoot)}', '{SqliteCli.Escape(bundle.ConvertedSourceRoot)}', '{DateTime.UtcNow:O}');";
            await _sqlite.ExecuteNonQueryAsync(moduleSql, cancellationToken);

            var moduleId = await GetSingleLongAsync($"SELECT id AS value FROM modules WHERE name='{SqliteCli.Escape(bundle.ModuleName)}' LIMIT 1;", cancellationToken);
            if (moduleId is null)
            {
                continue;
            }

            var orderedSkills = bundle.Skills.OrderBy(static s => s.StartedAt, StringComparer.OrdinalIgnoreCase).ToList();
            var startedAt = orderedSkills.FirstOrDefault()?.StartedAt ?? DateTime.UtcNow.ToString("O");
            var endedAt = orderedSkills.LastOrDefault()?.EndedAt ?? DateTime.UtcNow.ToString("O");
            var runStatus = orderedSkills.Any(static s => s.Status.Equals("failed", StringComparison.OrdinalIgnoreCase)) ? "failed" : "passed";
            var summary = $"{orderedSkills.Count(static s => s.Status.Equals("passed", StringComparison.OrdinalIgnoreCase))}/{orderedSkills.Count} skills passed.";

            var runSql = $@"
INSERT INTO runs(module_id, run_id, status, started_at, ended_at, summary, base_url, brs_path, artifact_root, created_at)
VALUES({moduleId.Value}, '{SqliteCli.Escape(bundle.RunId)}', '{SqliteCli.Escape(runStatus)}', '{SqliteCli.Escape(startedAt)}', '{SqliteCli.Escape(endedAt)}', '{SqliteCli.Escape(summary)}', '{SqliteCli.Escape(bundle.BaseUrl)}', '{SqliteCli.Escape(bundle.BrsPath)}', '{SqliteCli.Escape(bundle.ArtifactRoot)}', '{DateTime.UtcNow:O}');";
            await _sqlite.ExecuteNonQueryAsync(runSql, cancellationToken);

            var runFk = await GetSingleLongAsync($"SELECT id AS value FROM runs WHERE module_id={moduleId.Value} AND run_id='{SqliteCli.Escape(bundle.RunId)}' LIMIT 1;", cancellationToken);
            if (runFk is null)
            {
                continue;
            }

            foreach (var skill in orderedSkills)
            {
                var skillSql = $@"
INSERT INTO skill_executions
(run_fk, skill_name, stage, status, started_at, ended_at, summary, metrics_json, artifacts_json, findings_json, recommendations_json, result_contract_version, result_json)
VALUES
({runFk.Value}, '{SqliteCli.Escape(skill.SkillName)}', '{SqliteCli.Escape(skill.Stage)}', '{SqliteCli.Escape(skill.Status)}', '{SqliteCli.Escape(skill.StartedAt)}', '{SqliteCli.Escape(skill.EndedAt)}', '{SqliteCli.Escape(skill.Summary)}', '{SqliteCli.Escape(skill.MetricsJson)}', '{SqliteCli.Escape(skill.ArtifactsJson)}', '{SqliteCli.Escape(skill.FindingsJson)}', '{SqliteCli.Escape(skill.RecommendationsJson)}', '{SqliteCli.Escape(skill.ResultContractVersion)}', '{SqliteCli.Escape(skill.ResultJson)}');";
                await _sqlite.ExecuteNonQueryAsync(skillSql, cancellationToken);

                await PersistFindingsAsync(runFk.Value, skill, cancellationToken);
                await PersistRecommendationsAsync(runFk.Value, skill, cancellationToken);
                await PersistTestCategoryIfApplicableAsync(runFk.Value, skill, cancellationToken);
            }
        }
    }

    private async Task PersistFindingsAsync(long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (skill.RawResult["findings"] is not JsonArray findingArray)
        {
            return;
        }

        foreach (var findingNode in findingArray)
        {
            var finding = findingNode as JsonObject;
            var issueType = finding?["type"]?.GetValue<string>() ?? "General";
            var message = finding?["message"]?.GetValue<string>() ?? findingNode?.ToJsonString() ?? string.Empty;
            var scenario = finding?["scenario"]?.GetValue<string>() ?? string.Empty;
            var likelyCause = finding?["likelyCause"]?.GetValue<string>() ?? finding?["cause"]?.GetValue<string>() ?? string.Empty;
            var evidence = finding?["evidence"]?.GetValue<string>() ?? string.Empty;
            var severity = finding?["severity"]?.GetValue<string>() ?? "medium";
            var status = finding?["status"]?.GetValue<string>() ?? "open";
            var confidence = ParseDouble(finding?["confidence"], 0.65);
            var resolvedInRunId = finding?["resolvedInRunId"]?.GetValue<string>() ?? string.Empty;
            var resolutionNotes = finding?["resolutionNotes"]?.GetValue<string>() ?? string.Empty;
            var affectedFilesJson = finding?["affectedFiles"]?.ToJsonString() ?? "[]";

            var sql = $@"
INSERT INTO finding_records
(run_fk, stage, skill_name, scenario, issue_type, message, likely_cause, evidence, severity, status, confidence, affected_files_json, recommendation, resolved_in_run_id, resolution_notes)
VALUES
({runFk}, '{SqliteCli.Escape(skill.Stage)}', '{SqliteCli.Escape(skill.SkillName)}', '{SqliteCli.Escape(scenario)}', '{SqliteCli.Escape(issueType)}', '{SqliteCli.Escape(message)}', '{SqliteCli.Escape(likelyCause)}', '{SqliteCli.Escape(evidence)}', '{SqliteCli.Escape(severity)}', '{SqliteCli.Escape(status)}', {confidence.ToString(System.Globalization.CultureInfo.InvariantCulture)}, '{SqliteCli.Escape(affectedFilesJson)}', '', '{SqliteCli.Escape(resolvedInRunId)}', '{SqliteCli.Escape(resolutionNotes)}');";

            await _sqlite.ExecuteNonQueryAsync(sql, cancellationToken);
        }
    }

    private async Task PersistRecommendationsAsync(long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (skill.RawResult["recommendations"] is not JsonArray recommendationArray)
        {
            return;
        }

        foreach (var recommendationNode in recommendationArray)
        {
            var recommendationObject = recommendationNode as JsonObject;
            var message = recommendationObject?["message"]?.GetValue<string>() ?? recommendationNode?.GetValue<string>() ?? recommendationNode?.ToJsonString() ?? string.Empty;
            var priority = recommendationObject?["priority"]?.GetValue<string>() ?? "medium";
            var evidence = recommendationObject?["evidence"]?.GetValue<string>() ?? string.Empty;

            var sql = $@"
INSERT INTO recommendation_records
(run_fk, stage, skill_name, message, priority, evidence)
VALUES
({runFk}, '{SqliteCli.Escape(skill.Stage)}', '{SqliteCli.Escape(skill.SkillName)}', '{SqliteCli.Escape(message)}', '{SqliteCli.Escape(priority)}', '{SqliteCli.Escape(evidence)}');";

            await _sqlite.ExecuteNonQueryAsync(sql, cancellationToken);
        }
    }

    private async Task PersistTestCategoryIfApplicableAsync(long runFk, ParsedSkillExecution skill, CancellationToken cancellationToken)
    {
        if (!TestCategoryBySkill.TryGetValue(skill.SkillName, out var testInfo))
        {
            return;
        }

        var metrics = ParseMetrics(skill.MetricsJson);
        var total = metrics.GetValueOrDefault("total");
        var passed = metrics.GetValueOrDefault("passed");
        var failed = metrics.GetValueOrDefault("failed");
        var warningCount = metrics.GetValueOrDefault("warnings");
        var newTests = metrics.GetValueOrDefault("newTestsAdded");

        var scenariosJson = ExtractScenarioJson(skill.RawResult);
        var logsJson = BuildLogsJson(skill.ArtifactsJson);

        var sql = $@"
INSERT INTO test_category_results
(run_fk, category, purpose, scenarios_json, total, passed, failed, warnings, new_tests_added, logs_json, artifacts_json, source_skill, stage)
VALUES
({runFk}, '{SqliteCli.Escape(testInfo.Category)}', '{SqliteCli.Escape(testInfo.Purpose)}', '{SqliteCli.Escape(scenariosJson)}', {total}, {passed}, {failed}, {warningCount}, {newTests}, '{SqliteCli.Escape(logsJson)}', '{SqliteCli.Escape(skill.ArtifactsJson)}', '{SqliteCli.Escape(skill.SkillName)}', '{SqliteCli.Escape(skill.Stage)}');";

        await _sqlite.ExecuteNonQueryAsync(sql, cancellationToken);
    }

    private async Task PersistIterationDeltasAsync(CancellationToken cancellationToken)
    {
        var modules = await QueryRowsAsync("SELECT id, name FROM modules ORDER BY name;", cancellationToken);

        foreach (var module in modules)
        {
            var moduleId = module["id"]?.GetValue<long>() ?? 0;
            var runs = await QueryRowsAsync($"SELECT id, run_id FROM runs WHERE module_id={moduleId} ORDER BY run_id;", cancellationToken);

            JsonObject? previousRun = null;
            var previousFindingTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var previousTotalFailed = 0;

            foreach (var run in runs)
            {
                var runFk = run["id"]?.GetValue<long>() ?? 0;
                var runId = run["run_id"]?.GetValue<string>() ?? string.Empty;

                var testsAdded = (await GetSingleLongAsync($"SELECT COALESCE(SUM(new_tests_added),0) AS value FROM test_category_results WHERE run_fk={runFk};", cancellationToken)) ?? 0;
                var totalFailed = (int)((await GetSingleLongAsync($"SELECT COALESCE(SUM(failed),0) AS value FROM test_category_results WHERE run_fk={runFk};", cancellationToken)) ?? 0);
                var resolvedFindings = (await GetSingleLongAsync($"SELECT COUNT(1) AS value FROM finding_records WHERE run_fk={runFk} AND LOWER(status)='resolved';", cancellationToken)) ?? 0;

                var currentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                var currentTypeRows = await QueryRowsAsync($"SELECT DISTINCT issue_type FROM finding_records WHERE run_fk={runFk};", cancellationToken);
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

                var deltaJson = JsonSerializer.Serialize(new
                {
                    testsAdded,
                    testsFixed,
                    failuresReduced,
                    newFindingsIntroduced = newFindings,
                    resolvedFindings,
                    progressionTrend = trend
                });

                var previousRunId = previousRun?["run_id"]?.GetValue<string>() ?? string.Empty;

                var insertSql = $@"
INSERT INTO iteration_deltas
(module_id, run_id, previous_run_id, tests_added, tests_fixed, failures_reduced, new_findings_introduced, resolved_findings, progression_trend, delta_json)
VALUES
({moduleId}, '{SqliteCli.Escape(runId)}', '{SqliteCli.Escape(previousRunId)}', {testsAdded}, {testsFixed}, {failuresReduced}, {newFindings}, {resolvedFindings}, '{SqliteCli.Escape(trend)}', '{SqliteCli.Escape(deltaJson)}');";
                await _sqlite.ExecuteNonQueryAsync(insertSql, cancellationToken);

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

    private async Task<long?> GetSingleLongAsync(string sql, CancellationToken cancellationToken)
    {
        var rows = await QueryRowsAsync(sql, cancellationToken);
        var first = rows.FirstOrDefault();
        if (first is null || !first.TryGetPropertyValue("value", out var valueNode) || valueNode is null)
        {
            return null;
        }

        return long.TryParse(valueNode.ToString(), out var parsed) ? parsed : null;
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

        return double.TryParse(node.ToString(), out var value) ? value : fallback;
    }

    private static string ExtractScenarioJson(JsonObject rawResult)
    {
        if (rawResult["metrics"] is not JsonObject metrics)
        {
            return "[]";
        }

        if (metrics["scenarios"] is not JsonArray scenarios)
        {
            return "[]";
        }

        var names = new JsonArray();
        foreach (var scenario in scenarios)
        {
            if (scenario is JsonObject scenarioObject)
            {
                var name = scenarioObject["name"]?.GetValue<string>() ?? string.Empty;
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

                if (path.EndsWith(".log", StringComparison.OrdinalIgnoreCase) || path.EndsWith(".txt", StringComparison.OrdinalIgnoreCase) || path.EndsWith("console-logs.json", StringComparison.OrdinalIgnoreCase) || path.EndsWith("network-failures.json", StringComparison.OrdinalIgnoreCase))
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
