using LegacyModernization.Application.Contracts;
using LegacyModernization.Infrastructure.Abstractions;
using LegacyModernization.Infrastructure.Factories;
using LegacyModernization.Infrastructure.Services;
using Microsoft.Extensions.DependencyInjection;

namespace LegacyModernization.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddLegacyModernizationInfrastructure(this IServiceCollection services)
    {
        services.AddSingleton<ISqliteConnectionFactory, SqliteConnectionFactory>();
        services.AddSingleton<IMetadataSyncService, MetadataSyncService>();
        services.AddSingleton<IDashboardQueryService, DashboardQueryService>();

        return services;
    }
}
