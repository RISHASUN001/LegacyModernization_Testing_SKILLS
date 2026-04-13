var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services.AddControllersWithViews();
builder.Services.AddSession(options =>
{
    options.IdleTimeout = TimeSpan.FromMinutes(30);
});

var app = builder.Build();

// Configure middleware
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
}

app.UseStaticFiles();
app.UseRouting();
app.UseSession();

app.MapControllers();

var port = 5001;
Console.WriteLine($"🚀 Legacy (Converted) Application running on http://localhost:{port}");
Console.WriteLine($"Login with: admin / password123");
Console.WriteLine();

app.Run($"http://0.0.0.0:{port}");
