using LegacyModernization.Application.DTOs;

namespace LegacyModernization.Dashboard.Web.Models;

public sealed class RunInputBuilderFormModel
{
    public RunInputBuilderPageDto Page { get; init; } = new();
    public string? Message { get; init; }
}
