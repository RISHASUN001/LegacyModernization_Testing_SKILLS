using Microsoft.Data.Sqlite;

namespace LegacyModernization.Infrastructure.Abstractions;

public interface ISqliteConnectionFactory
{
    Task<SqliteConnection> CreateOpenConnectionAsync(CancellationToken cancellationToken = default);
}
