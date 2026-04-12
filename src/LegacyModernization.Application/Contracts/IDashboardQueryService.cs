using LegacyModernization.Application.DTOs;

namespace LegacyModernization.Application.Contracts;

public interface IDashboardQueryService
{
    Task<HomePageDto> GetHomePageAsync(CancellationToken cancellationToken = default);
    Task<SkillLibraryPageDto> GetSkillLibraryAsync(CancellationToken cancellationToken = default);
    Task<RunInputBuilderPageDto> GetRunInputBuilderAsync(CancellationToken cancellationToken = default);
    Task<string> SaveRunInputAsync(RunInputDraftDto draft, CancellationToken cancellationToken = default);
    Task<ModuleRunsPageDto> GetModuleRunsAsync(string? moduleName, CancellationToken cancellationToken = default);
    Task<RunPipelinePageDto?> GetRunPipelineAsync(string moduleName, string runId, CancellationToken cancellationToken = default);
    Task<FindingsPageDto> GetFindingsAsync(string? moduleName, string? runId, CancellationToken cancellationToken = default);
    Task<IterationComparisonPageDto?> GetIterationComparisonAsync(string moduleName, CancellationToken cancellationToken = default);
}
