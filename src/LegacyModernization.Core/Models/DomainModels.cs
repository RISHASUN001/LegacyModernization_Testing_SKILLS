namespace LegacyModernization.Core.Models;

public sealed record ModuleRecord(
    long Id,
    string Name,
    string LegacySourceRoot,
    string ConvertedSourceRoot,
    string CreatedAt);

public sealed record RunRecord(
    long Id,
    long ModuleId,
    string RunId,
    string Status,
    string StartedAt,
    string EndedAt,
    string Summary,
    string BaseUrl,
    string BrsPath,
    string ArtifactRoot,
    string CreatedAt);

public sealed record SkillDefinitionRecord(
    long Id,
    string Name,
    string Category,
    string ScriptEntry,
    string RequiredInputsJson,
    string OptionalInputsJson,
    string ExpectedOutputsJson,
    string DependenciesJson,
    string ArtifactPathsJson,
    string Purpose,
    string SkillMarkdown);

public sealed record SkillExecutionRecord(
    long Id,
    long RunFk,
    string SkillName,
    string Status,
    string StartedAt,
    string EndedAt,
    string Summary,
    string MetricsJson,
    string FindingsJson,
    string RecommendationsJson,
    string ArtifactsJson);

public sealed record TestCategoryResultRecord(
    long Id,
    long RunFk,
    string Category,
    int Total,
    int Passed,
    int Failed,
    int NewTestsAdded,
    string KeyFailuresJson,
    string LogPath);

public sealed record FindingRecord(
    long Id,
    long RunFk,
    string SkillName,
    string FindingType,
    string Message,
    string Severity,
    string Status,
    string ResolvedInRunId,
    string ResolutionNotes);

public sealed record RecommendationRecord(
    long Id,
    long RunFk,
    string SkillName,
    string Recommendation,
    string Priority);

public sealed record LessonLearnedRecord(
    long Id,
    long RunFk,
    string Lesson,
    string Theme,
    string ActionTaken,
    string Impact);

public sealed record IterationSummaryRecord(
    long Id,
    long ModuleId,
    string RunId,
    int TestsAdded,
    int TotalFailed,
    int ResolvedFindings,
    int RecurringIssues,
    string ParityStatus);

public sealed record RunInputModel(
    string RunId,
    string ModuleName,
    string LegacySourceRoot,
    string ConvertedSourceRoot,
    string BaseUrl,
    string BrsPath,
    ModuleHintsModel ModuleHints,
    IReadOnlyList<string> SelectedSkills);

public sealed record ModuleHintsModel(
    IReadOnlyList<string> RelatedFolders,
    IReadOnlyList<string> KnownUrls,
    IReadOnlyList<string> Keywords);
