using MATE.Dashboard.Web.Models.Pipeline;

namespace MATE.Dashboard.Web.Services;

public interface IPipelineArtifactsService
{
    Task<PipelineHomeDto> GetHomeAsync(CancellationToken cancellationToken);
    Task<PipelineRunDto?> GetRunAsync(string moduleName, string runId, CancellationToken cancellationToken);
    Task<string> SaveRunInputAsync(MateRunInputModel model, CancellationToken cancellationToken);
    bool TryGetArtifactPath(string moduleName, string runId, string path, out string absolutePath);
}
