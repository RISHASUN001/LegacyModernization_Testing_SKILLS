namespace MATE.Dashboard.Web.Models.Pipeline;

public class PipelineRunDto
{
    public string ModuleName { get; set; } = string.Empty;
    public string RunId { get; set; } = string.Empty;
    public string StartedAt { get; set; } = string.Empty;
    public string EndedAt { get; set; } = string.Empty;
    public string Status { get; set; } = "unknown";
    public string Summary { get; set; } = string.Empty;
    public List<StageStatusDto> StageStatuses { get; set; } = new();
    public Dictionary<string, object> StagArtifacts { get; set; } = new();
}

public class StageStatusDto
{
    public int StageIndex { get; set; }
    public string StageId { get; set; } = string.Empty;
    public string StageTitle { get; set; } = string.Empty;
    public string StageObjective { get; set; } = string.Empty;
    public string Status { get; set; } = "unknown";
    public List<SkillResultDto> Skills { get; set; } = new();
}

public class SkillResultDto
{
    public string SkillName { get; set; } = string.Empty;
    public string Status { get; set; } = "unknown";
    public string Summary { get; set; } = string.Empty;
    public int ReturnCode { get; set; }
    public bool Reused { get; set; }
    public string StdErr { get; set; } = string.Empty;
    public Dictionary<string, object> Metrics { get; set; } = new();
    public List<string> ArtifactPaths { get; set; } = new();
    public List<ArtifactDto> Artifacts { get; set; } = new();
    public List<string> FindingIds { get; set; } = new();
}

public class ArtifactDto
{
    public string Name { get; set; } = string.Empty;
    public string RelativePath { get; set; } = string.Empty;
    public string Kind { get; set; } = "other";
    public bool Exists { get; set; }
}

public class PipelineHomeDto
{
    public List<ModuleRunSummaryDto> Modules { get; set; } = new();
    public int TotalRuns { get; set; }
}

public class ModuleRunSummaryDto
{
    public string ModuleName { get; set; } = string.Empty;
    public int RunCount { get; set; }
    public string LatestRunId { get; set; } = string.Empty;
    public string LatestStatus { get; set; } = "unknown";
    public string LatestEndedAt { get; set; } = string.Empty;
}
