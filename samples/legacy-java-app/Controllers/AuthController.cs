using Microsoft.AspNetCore.Mvc;
using LegacyModernization.Converted.Services;

namespace LegacyModernization.Converted.Controllers;

/// <summary>
/// Legacy LoginServlet converted to ASP.NET Core
/// Serves login page and processes authentication
/// </summary>
[Route("")]
public class AuthController : Controller
{
    private readonly LoginService _loginService = new();

    [HttpGet("")]
    [HttpGet("index")]
    [HttpGet("login")]
    public IActionResult Index()
    {
        return View("~/Views/Auth/Index.cshtml");
    }

    [HttpPost("login")]
    public IActionResult LoginPost(string email, string password, string module = "Dashboard")
    {
        var result = _loginService.Login(email, password, module);

        if (!result.Success)
        {
            TempData["Error"] = result.Message;
            return RedirectToAction("Index");
        }

        HttpContext.Session.SetString("user", result.SessionId ?? "");
        HttpContext.Session.SetString("module", result.Module);

        return RedirectToAction("Dashboard");
    }

    [HttpGet("dashboard")]
    public IActionResult Dashboard()
    {
        var sessionId = HttpContext.Session.GetString("user");
        if (string.IsNullOrEmpty(sessionId))
        {
            return RedirectToAction("Index");
        }

        var module = HttpContext.Session.GetString("module") ?? "Dashboard";
        ViewData["User"] = sessionId;
        ViewData["Module"] = module;

        return View("~/Views/Auth/Dashboard.cshtml");
    }

    [HttpGet("logout")]
    public IActionResult Logout()
    {
        HttpContext.Session.Clear();
        return RedirectToAction("Index");
    }
}
