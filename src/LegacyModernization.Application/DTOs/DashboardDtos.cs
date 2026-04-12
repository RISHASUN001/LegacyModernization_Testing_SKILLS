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
    public string ModuleName { get; set; } = "Checklist";
    public string LegacySourceRoot { get; set; } = "C:/edcs2000/src";
    public string ConvertedSourceRoot { get; set; } = "C:/edcs2000/src_conversion4";
    public string BaseUrl { get; set; } = "http://localhost:5276";
    public string BrsPath { get; set; } = "C:/docs/checklist_brs.docx";
    public string RelatedFoldersText { get; set; } = "src/jsp/checklist\nsrc/com/seagate/edcs/checklist";
    public string KnownUrlsText { get; set; } = "/checklist/loadChecklist.do";
    public string KeywordsText { get; set; } = "checklist\nATC\nsensor\nwork order";
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
    public FindingsStageDto Findings { get; init; } = new();
    public IterationComparisonSummaryDto IterationComparison { get; init; } = new();
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
    public string SourceArtifactPath { get; init; } = string.Empty;
}

public sealed class LogicUnderstandingStageDto
{
    public string ModulePurpose { get; init; } = string.Empty;
    public List<string> ImportantFlows { get; init; } = [];
    public List<string> Rules { get; init; } = [];
    public List<string> Dependencies { get; init; } = [];
    public List<string> MustPreserve { get; init; } = [];
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
    public List<string> Logs { get; init; } = [];
    public List<string> Artifacts { get; init; } = [];
}

public sealed class PlaywrightEvidenceDto
{
    public string Status { get; init; } = "unknown";
    public string Summary { get; init; } = string.Empty;
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
