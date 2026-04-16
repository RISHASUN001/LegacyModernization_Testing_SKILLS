namespace MATE.Dashboard.Web.Models.Pipeline;

public sealed class PipelineHomeViewModel
{
    public List<PipelineRunListItem> LatestRuns { get; init; } = [];
}

public sealed class PipelineRunListItem
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Status { get; init; } = "unknown";
    public string StartedAt { get; init; } = string.Empty;
    public string EndedAt { get; init; } = string.Empty;
}

public sealed class PipelineRunDetailsViewModel
{
    public string ModuleName { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string Status { get; init; } = "unknown";
    public string Summary { get; init; } = string.Empty;
    public string StartedAt { get; init; } = string.Empty;
    public string EndedAt { get; init; } = string.Empty;
    public List<PipelineStageStatus> Stages { get; init; } = [];
    public List<ArtifactProofItem> Proofs { get; init; } = [];
    public List<PipelineSkillResult> Skills { get; init; } = [];
}

public sealed class PipelineStageStatus
{
    public int Index { get; init; }
    public string Stage { get; init; } = string.Empty;
    public string Title { get; init; } = string.Empty;
    public string Objective { get; init; } = string.Empty;
    public string Status { get; init; } = "unknown";
    public int SkillCount { get; init; }
    public int SkillsFailed { get; init; }
    public int ReusedSkills { get; init; }
    public string InputType { get; init; } = string.Empty;
    public string OutputType { get; init; } = string.Empty;
    public string NextStage { get; init; } = string.Empty;
    public string NextInputType { get; init; } = string.Empty;
    public List<PipelineSkillResult> Skills { get; init; } = [];
}

public sealed class ArtifactProofItem
{
    public string Label { get; init; } = string.Empty;
    public string Path { get; init; } = string.Empty;
    public bool Exists { get; init; }
}

public sealed class PipelineSkillResult
{
    public string Stage { get; init; } = string.Empty;
    public string Skill { get; init; } = string.Empty;
    public string Status { get; init; } = "unknown";
    public string Summary { get; init; } = string.Empty;
    public int ReturnCode { get; init; }
    public bool Reused { get; init; }
    public string StdErr { get; init; } = string.Empty;
    public Dictionary<string, object> Metrics { get; init; } = [];
    public List<ArtifactPreviewItem> Artifacts { get; init; } = [];
    public List<PipelineFindingItem> Findings { get; init; } = [];
}

public sealed class ArtifactPreviewItem
{
    public string Name { get; init; } = string.Empty;
    public string RelativePath { get; init; } = string.Empty;
    public string Kind { get; init; } = "other";
    public bool Exists { get; init; }
    public string PreviewText { get; init; } = string.Empty;
}

public sealed class PipelineFindingItem
{
    public string Type { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;
    public string Severity { get; init; } = string.Empty;
}
