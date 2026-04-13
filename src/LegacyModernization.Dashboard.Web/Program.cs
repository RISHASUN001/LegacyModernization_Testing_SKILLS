using LegacyModernization.Application.Contracts;
using LegacyModernization.Infrastructure;
using LegacyModernization.Infrastructure.Options;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();

var workspaceRoot = Path.GetFullPath(Path.Combine(builder.Environment.ContentRootPath, "..", ".."));
var skillsRoot = Path.Combine(workspaceRoot, "skills");
var artifactsRoot = Path.Combine(workspaceRoot, "artifacts");
var runInputsRoot = Path.Combine(workspaceRoot, "run-inputs");
var dataRoot = Path.Combine(workspaceRoot, "data");
var databasePath = Path.Combine(dataRoot, "modernization.db");

var connectionString = builder.Configuration.GetConnectionString("ModernizationDb");
if (string.IsNullOrWhiteSpace(connectionString))
{
    connectionString = "Data Source=data/modernization.db";
}

builder.Services.Configure<PlatformPathsOptions>(options =>
{
    options.WorkspaceRoot = workspaceRoot;
    options.SkillsRoot = skillsRoot;
    options.ArtifactsRoot = artifactsRoot;
    options.RunInputsRoot = runInputsRoot;
    options.DataRoot = dataRoot;
    options.DatabasePath = databasePath;
    options.ConnectionString = connectionString;
});

builder.Services.AddLegacyModernizationInfrastructure();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var syncService = scope.ServiceProvider.GetRequiredService<IMetadataSyncService>();
    await syncService.SyncAsync();
}

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
    app.UseHttpsRedirection();
}
app.UseStaticFiles();
app.UseRouting();
app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Dashboard}/{action=Index}/{id?}");

app.Run();
