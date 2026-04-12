namespace LegacyModernization.Infrastructure.Options;

public sealed class PlatformPathsOptions
{
    public string WorkspaceRoot { get; set; } = string.Empty;
    public string SkillsRoot { get; set; } = string.Empty;
    public string ArtifactsRoot { get; set; } = string.Empty;
    public string RunInputsRoot { get; set; } = string.Empty;
    public string DataRoot { get; set; } = string.Empty;
    public string DatabasePath { get; set; } = string.Empty;
}
