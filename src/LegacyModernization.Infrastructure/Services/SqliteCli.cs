using System.Diagnostics;
using System.Text;
using LegacyModernization.Infrastructure.Options;
using Microsoft.Extensions.Options;

namespace LegacyModernization.Infrastructure.Services;

public sealed class SqliteCli
{
    private readonly PlatformPathsOptions _paths;

    public SqliteCli(IOptions<PlatformPathsOptions> options)
    {
        _paths = options.Value;
    }

    public async Task ExecuteNonQueryAsync(string sql, CancellationToken cancellationToken = default)
    {
        await RunSqliteAsync(arguments: [_paths.DatabasePath, sql], cancellationToken);
    }

    public async Task<string> ExecuteJsonQueryAsync(string sql, CancellationToken cancellationToken = default)
    {
        return await RunSqliteAsync(arguments: ["-json", _paths.DatabasePath, sql], cancellationToken);
    }

    public static string Escape(string raw)
    {
        return raw.Replace("'", "''");
    }

    private static async Task<string> RunSqliteAsync(string[] arguments, CancellationToken cancellationToken)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "sqlite3",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        foreach (var argument in arguments)
        {
            psi.ArgumentList.Add(argument);
        }

        using var process = new Process { StartInfo = psi };
        process.Start();

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken);

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"sqlite3 failed with exit code {process.ExitCode}: {stderr}");
        }

        return stdout;
    }
}
