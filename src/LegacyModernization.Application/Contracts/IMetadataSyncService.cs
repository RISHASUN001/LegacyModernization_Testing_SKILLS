namespace LegacyModernization.Application.Contracts;

public interface IMetadataSyncService
{
    Task SyncAsync(CancellationToken cancellationToken = default);
}
