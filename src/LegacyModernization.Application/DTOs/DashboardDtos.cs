namespace LegacyModernization.Application.DTOs;

public sealed class HomePageDto
{
    public List<ModuleSummaryDto> Modules { get; init; } = [];
    public List<RunSummaryDto> LatestRuns { get; init; } = [];
    public int TotalRuns { get; init; }
    public int PassedRuns { get; init; }
    public int FailedRuns { get; init; }
}

public sealed class ModuleSummaryDto
{
    public string Name { get; init; } = string.Empty;
    public int TotalRuns { get; init; }
    public string LastRunId { get; init; } = string.Empty;
    public string LastStatus { get; init; } = string.Empty;
    public string LastUpdatedAt { get; init; } = string.Empty;
}

public sealed class RunSummaryDto
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string StartedAt { get; init; } = string.Empty;
    public string EndedAt { get; init; } = string.Empty;
    public string Summary { get; init; } = string.Empty;
}

public sealed class SkillLibraryPageDto
{
    public List<SkillLibraryItemDto> Skills { get; init; } = [];
}

public sealed class SkillLibraryItemDto
{
    public string Name { get; init; } = string.Empty;
    public string Stage { get; init; } = string.Empty;
    public string Category { get; init; } = string.Empty;
    public string Purpose { get; init; } = string.Empty;
    public string ScriptEntry { get; init; } = string.Empty;
    public string SummaryOutputType { get; init; } = string.Empty;
    public string ResultContractVersion { get; init; } = string.Empty;
    public List<string> RequiredInputs { get; init; } = [];
    public List<string> OptionalInputs { get; init; } = [];
    public List<string> OutputFiles { get; init; } = [];
    public List<string> ArtifactFolders { get; init; } = [];
    public List<string> Dependencies { get; init; } = [];
    public string SkillMarkdown { get; init; } = string.Empty;
}

public sealed class RunInputBuilderPageDto
{
    public RunInputDraftDto Draft { get; init; } = new();
    public List<string> AvailableSkills { get; init; } = [];
    public string GeneratedJson { get; init; } = string.Empty;
    public string? SavedPath { get; init; }
}

public sealed class RunInputDraftDto
{
    public string RunId { get; set; } = "run-001";
    public string ModuleName { get; set; } = string.Empty;
    public string LegacySourceRoot { get; set; } = string.Empty;
    public string ConvertedSourceRoot { get; set; } = string.Empty;
    public string BaseUrl { get; set; } = "http://localhost:5276";
    public string TestApiEndpoint { get; set; } = "http://localhost:5276/api/test";
    public string BrsPath { get; set; } = string.Empty;
    public string RelatedFoldersText { get; set; } = string.Empty;
    public string KnownUrlsText { get; set; } = string.Empty;
    public string KeywordsText { get; set; } = string.Empty;
    public string UnitCommand { get; set; } = "dotnet test --nologo --verbosity minimal";
    public string IntegrationCommand { get; set; } = "dotnet test --nologo --verbosity minimal";
    public string ApiCommand { get; set; } = "python3 -m pytest -m api";
    public string E2eCommand { get; set; } = "python3 -m pytest -m e2e";
    public string EdgeCaseCommand { get; set; } = "dotnet test --nologo --verbosity minimal";
    public string PlaywrightCommand { get; set; } = "python3 -m pytest -m playwright";
    public List<string> SelectedSkills { get; set; } = [];
}

public sealed class ModuleRunsPageDto
{
    public string? ModuleFilter { get; init; }
    public List<RunSummaryDto> Runs { get; init; } = [];
}

public sealed class RunPipelinePageDto
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string StartedAt { get; init; } = string.Empty;
    public string EndedAt { get; init; } = string.Empty;
    public string Summary { get; init; } = string.Empty;
    public List<StageStatusDto> StageStatuses { get; init; } = [];
    public DiscoveryStageDto Discovery { get; init; } = new();
    public LogicUnderstandingStageDto LogicUnderstanding { get; init; } = new();
    public ArchitectureReviewStageDto ArchitectureReview { get; init; } = new();
    public TestPlanStageDto TestPlan { get; init; } = new();
    public ExecutionStageDto Execution { get; init; } = new();
    public ParityStageDto Parity { get; init; } = new();
    public FindingsStageDto Findings { get; init; } = new();
    public KeyLearningsDto KeyLearnings { get; init; } = new();
    public IterationComparisonSummaryDto IterationComparison { get; init; } = new();
}

public sealed class ParityStageDto
{
    public int ParityScore { get; init; }
    public int TotalChecks { get; init; }
    public int PassedChecks { get; init; }
    public int FailedChecks { get; init; }
    public double Confidence { get; init; }
    public List<ParityCheckDto> Checks { get; init; } = [];
    public SqlParityDto SqlParity { get; init; } = new();
    public List<string> Gaps { get; init; } = [];
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class ParityCheckDto
{
    public string Name { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public List<string> EvidenceLines { get; init; } = [];
    public string ProvenanceType { get; init; } = string.Empty;
    public double Confidence { get; init; }
}

public sealed class SqlParityDto
{
    public int LegacyQueryCount { get; init; }
    public int ConvertedQueryCount { get; init; }
    public int MatchedCount { get; init; }
    public List<TableParityDto> Tables { get; init; } = [];
    public List<SqlBeforeAfterDto> BeforeAfter { get; init; } = [];
}

public sealed class TableParityDto
{
    public string Table { get; init; } = string.Empty;
    public int LegacyOccurrences { get; init; }
    public int ConvertedOccurrences { get; init; }
    public string Status { get; init; } = string.Empty;
}

public sealed class SqlBeforeAfterDto
{
    public string Status { get; init; } = string.Empty;
    public string LegacyFile { get; init; } = string.Empty;
    public string LegacyQuery { get; init; } = string.Empty;
    public List<string> LegacyTables { get; init; } = [];
    public string ConvertedFile { get; init; } = string.Empty;
    public string ConvertedQuery { get; init; } = string.Empty;
    public List<string> ConvertedTables { get; init; } = [];
    public double Confidence { get; init; }
}

public sealed class KeyLearningsDto
{
    public List<string> RecurringSignatures { get; init; } = [];
    public List<string> KnownPitfalls { get; init; } = [];
    public List<string> NewIssues { get; init; } = [];
    public List<string> RecurringIssues { get; init; } = [];
    public List<string> ResolvedIssues { get; init; } = [];
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class StageStatusDto
{
    public string StageId { get; init; } = string.Empty;
    public string StageTitle { get; init; } = string.Empty;
    public string Status { get; init; } = "unknown";
    public int SkillCount { get; init; }
    public int FailedSkills { get; init; }
}

public sealed class DiscoveryStageDto
{
    public List<string> JavaFiles { get; init; } = [];
    public List<string> JspFiles { get; init; } = [];
    public List<string> JsFiles { get; init; } = [];
    public List<string> ConfigFiles { get; init; } = [];
    public List<string> Urls { get; init; } = [];
    public List<string> DbTouchpoints { get; init; } = [];
    public List<ProvenancedValueDto> UrlDetails { get; init; } = [];
    public List<ProvenancedValueDto> DbTouchpointDetails { get; init; } = [];
    public List<ProvenancedValueDto> EntrypointHints { get; init; } = [];
    public double Confidence { get; init; }
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class LogicUnderstandingStageDto
{
    public string ModulePurpose { get; init; } = string.Empty;
    public List<string> ImportantFlows { get; init; } = [];
    public List<string> Rules { get; init; } = [];
    public List<string> Dependencies { get; init; } = [];
    public List<string> MustPreserve { get; init; } = [];
    public List<ProvenancedValueDto> FlowDetails { get; init; } = [];
    public List<ProvenancedValueDto> RuleDetails { get; init; } = [];
    public List<string> Unknowns { get; init; } = [];
    public double Confidence { get; init; }
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class ArchitectureReviewStageDto
{
    public List<ArchitectureIssueDto> CleanArchitectureIssues { get; init; } = [];
    public List<ArchitectureIssueDto> NamespaceFolderIssues { get; init; } = [];
    public List<ArchitectureIssueDto> DiIssues { get; init; } = [];
    public List<ArchitectureIssueDto> CouplingIssues { get; init; } = [];
    public List<string> RecommendedStructure { get; init; } = [];
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class ArchitectureIssueDto
{
    public string Title { get; init; } = string.Empty;
    public string Severity { get; init; } = string.Empty;
    public string Evidence { get; init; } = string.Empty;
}

public sealed class TestPlanStageDto
{
    public List<string> ExistingTestsFound { get; init; } = [];
    public List<string> NewTestsSuggested { get; init; } = [];
    public List<TestCategoryPlanDto> TestCategories { get; init; } = [];
    public string CoverageSummary { get; init; } = string.Empty;
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class TestCategoryPlanDto
{
    public string Category { get; init; } = string.Empty;
    public string Purpose { get; init; } = string.Empty;
    public List<TestScenarioPlanDto> Scenarios { get; init; } = [];
}

public sealed class ExecutionStageDto
{
    public List<TestCategoryExecutionDto> TestCategories { get; init; } = [];
    public PlaywrightEvidenceDto Playwright { get; init; } = new();
}

public sealed class TestCategoryExecutionDto
{
    public string Category { get; init; } = string.Empty;
    public string Purpose { get; init; } = string.Empty;
    public List<string> ScenariosCovered { get; init; } = [];
    public int TotalCount { get; init; }
    public int Passed { get; init; }
    public int Failed { get; init; }
    public int Warnings { get; init; }
    public int NewTestsAdded { get; init; }
    public string SourceSkill { get; init; } = string.Empty;
    public string PreflightStatus { get; init; } = string.Empty;
    public string PreflightReason { get; init; } = string.Empty;
    public double ScenarioConfidence { get; init; }
    public List<string> Logs { get; init; } = [];
    public List<string> Artifacts { get; init; } = [];
    public List<TestScenarioExecutionDto> ScenarioDetails { get; init; } = [];
}

public sealed class PlaywrightEvidenceDto
{
    public string Status { get; init; } = "unknown";
    public string Summary { get; init; } = string.Empty;
    public string TestApiEndpoint { get; init; } = string.Empty;
    public string TestApiStatus { get; init; } = "unknown";
    public string TestApiReason { get; init; } = string.Empty;
    public List<PlaywrightScenarioDto> Scenarios { get; init; } = [];
    public List<string> ConsoleErrors { get; init; } = [];
    public List<string> ConsoleWarnings { get; init; } = [];
    public List<string> NetworkFailures { get; init; } = [];
    public List<string> DomStateChecks { get; init; } = [];
    public List<string> RuntimeIssues { get; init; } = [];
    public List<string> PerformanceObservations { get; init; } = [];
    public List<string> Screenshots { get; init; } = [];
    public List<string> ArtifactLinks { get; init; } = [];
}

public sealed class PlaywrightScenarioDto
{
    public string Name { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string Notes { get; init; } = string.Empty;
}

public sealed class FindingsStageDto
{
    public List<FindingDto> Findings { get; init; } = [];
    public List<RecommendationDto> Recommendations { get; init; } = [];
}

public sealed class FindingsPageDto
{
    public string? ModuleName { get; init; }
    public string? RunId { get; init; }
    public List<FindingDto> Findings { get; init; } = [];
    public List<RecommendationDto> Recommendations { get; init; } = [];
}

public sealed class FindingDto
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Stage { get; init; } = string.Empty;
    public string SkillName { get; init; } = string.Empty;
    public string Scenario { get; init; } = string.Empty;
    public string FindingType { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;
    public string LikelyCause { get; init; } = string.Empty;
    public string Evidence { get; init; } = string.Empty;
    public string Severity { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public double Confidence { get; init; }
    public string ProvenanceType { get; init; } = string.Empty;
    public string ResolvedInRunId { get; init; } = string.Empty;
    public string ResolutionNotes { get; init; } = string.Empty;
    public List<string> AffectedFiles { get; init; } = [];
}

public sealed class RecommendationDto
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Stage { get; init; } = string.Empty;
    public string SkillName { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;
    public string Priority { get; init; } = string.Empty;
    public string Evidence { get; init; } = string.Empty;
    public string ProvenanceType { get; init; } = string.Empty;
}

public sealed class IterationComparisonPageDto
{
    public string ModuleName { get; init; } = string.Empty;
    public List<IterationPointDto> Iterations { get; init; } = [];
}

public sealed class IterationPointDto
{
    public string RunId { get; init; } = string.Empty;
    public string PreviousRunId { get; init; } = string.Empty;
    public int TestsAdded { get; init; }
    public int TestsFixed { get; init; }
    public int FailuresReduced { get; init; }
    public int NewFindingsIntroduced { get; init; }
    public int ResolvedFindings { get; init; }
    public string ProgressionTrend { get; init; } = string.Empty;
}

public sealed class IterationComparisonSummaryDto
{
    public string PreviousRunId { get; init; } = string.Empty;
    public int TestsAdded { get; init; }
    public int TestsFixed { get; init; }
    public int FailuresReduced { get; init; }
    public int NewFindingsIntroduced { get; init; }
    public int ResolvedFindings { get; init; }
    public string ProgressionTrend { get; init; } = string.Empty;
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class ProvenancedValueDto
{
    public string Value { get; init; } = string.Empty;
    public string ProvenanceType { get; init; } = string.Empty;
    public double Confidence { get; init; }
    public List<string> Sources { get; init; } = [];
}

public sealed class TestScenarioPlanDto
{
    public string Name { get; init; } = string.Empty;
    public List<string> Coverage { get; init; } = [];
    public string ProvenanceType { get; init; } = string.Empty;
    public double Confidence { get; init; }
}

public sealed class TestScenarioExecutionDto
{
    public string Name { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string Notes { get; init; } = string.Empty;
    public List<string> Coverage { get; init; } = [];
    public bool Generated { get; init; }
    public List<string> GeneratedFrom { get; init; } = [];
    public string ProvenanceType { get; init; } = string.Empty;
    public double Confidence { get; init; }
}

#region Browser Testing DTOs

public sealed class BrowserTestingResultsDto
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty; // completed, not_executed, failed
    public List<BrowserSessionDto> Sessions { get; init; } = [];
    public List<BrowserConsoleLogDto> ConsoleLogs { get; init; } = [];
    public List<BrowserNetworkRequestDto> NetworkRequests { get; init; } = [];
    public List<BrowserPerformanceMetricDto> PerformanceMetrics { get; init; } = [];
    public List<BrowserAccessibilityIssueDto> AccessibilityIssues { get; init; } = [];
    public List<BrowserScreenshotDto> Screenshots { get; init; } = [];
    public List<BrowserDomSnapshotDto> DomSnapshots { get; init; } = [];
}

public sealed class BrowserSessionDto
{
    public long Id { get; init; }
    public string BaseUrl { get; init; } = string.Empty;
    public string StartTimestamp { get; init; } = string.Empty;
    public string EndTimestamp { get; init; } = string.Empty;
    public int TotalScenarios { get; init; }
    public int PassedScenarios { get; init; }
    public int FailedScenarios { get; init; }
    public string ViewportSizes { get; init; } = string.Empty; // JSON array
}

public sealed class BrowserConsoleLogDto
{
    public string Level { get; init; } = string.Empty; // error, warn, info, debug
    public string Message { get; init; } = string.Empty;
    public string SourceFile { get; init; } = string.Empty;
    public int SourceLine { get; init; }
    public string Timestamp { get; init; } = string.Empty;
    public string StackTrace { get; init; } = string.Empty;
}

public sealed class BrowserNetworkRequestDto
{
    public string Method { get; init; } = string.Empty; // GET, POST, etc.
    public string Url { get; init; } = string.Empty;
    public int StatusCode { get; init; }
    public string RequestPayload { get; init; } = string.Empty;
    public string ResponsePayload { get; init; } = string.Empty;
    public int ResponseTimeMs { get; init; }
    public string ContentType { get; init; } = string.Empty;
    public string Timestamp { get; init; } = string.Empty;
}

public sealed class BrowserPerformanceMetricDto
{
    public string MetricName { get; init; } = string.Empty; // LCP, CLS, INP, TTFB, FCP
    public double MetricValue { get; init; }
    public double TargetThreshold { get; init; }
    public bool MeetsThreshold { get; init; }
    public string Timestamp { get; init; } = string.Empty;
}

public sealed class BrowserAccessibilityIssueDto
{
    public string IssueType { get; init; } = string.Empty; // color-contrast, aria-labels, keyboard-nav, etc.
    public string Severity { get; init; } = string.Empty; // critical, high, medium, low
    public string ElementSelector { get; init; } = string.Empty;
    public string IssueDescription { get; init; } = string.Empty;
    public string Recommendation { get; init; } = string.Empty;
    public string Timestamp { get; init; } = string.Empty;
}

public sealed class BrowserScreenshotDto
{
    public string Filename { get; init; } = string.Empty;
    public string ArtifactPath { get; init; } = string.Empty;
    public int ViewportWidth { get; init; }
    public int ViewportHeight { get; init; }
    public string ScenarioContext { get; init; } = string.Empty;
    public string CapturedAt { get; init; } = string.Empty;
}

public sealed class BrowserDomSnapshotDto
{
    public string Filename { get; init; } = string.Empty;
    public string ArtifactPath { get; init; } = string.Empty;
    public string ScenarioContext { get; init; } = string.Empty;
    public int ElementCount { get; init; }
    public string CapturedAt { get; init; } = string.Empty;
}

#endregion
