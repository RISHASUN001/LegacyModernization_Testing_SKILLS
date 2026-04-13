using Dapper;
using LegacyModernization.Infrastructure.Abstractions;
using LegacyModernization.Infrastructure.Options;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Options;

namespace LegacyModernization.Infrastructure.Factories;

public sealed class SqliteConnectionFactory : ISqliteConnectionFactory
{
    private readonly PlatformPathsOptions _paths;

    public SqliteConnectionFactory(IOptions<PlatformPathsOptions> options)
    {
        _paths = options.Value;
    }

    public async Task<SqliteConnection> CreateOpenConnectionAsync(CancellationToken cancellationToken = default)
    {
        var rawConnectionString = string.IsNullOrWhiteSpace(_paths.ConnectionString)
            ? $"Data Source={_paths.DatabasePath}"
            : _paths.ConnectionString;

        var builder = new SqliteConnectionStringBuilder(rawConnectionString);
        if (string.IsNullOrWhiteSpace(builder.DataSource))
        {
            builder.DataSource = _paths.DatabasePath;
        }
        else if (!Path.IsPathRooted(builder.DataSource))
        {
            builder.DataSource = Path.GetFullPath(Path.Combine(_paths.WorkspaceRoot, builder.DataSource));
        }

        var directory = Path.GetDirectoryName(builder.DataSource);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        var connection = new SqliteConnection(builder.ConnectionString);
        await connection.OpenAsync(cancellationToken);
        await connection.ExecuteAsync(new CommandDefinition("PRAGMA foreign_keys = ON;", cancellationToken: cancellationToken));
        return connection;
    }
}
