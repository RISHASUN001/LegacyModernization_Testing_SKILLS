using System;
using System.Collections.Generic;

namespace LegacyModernization.Converted.Services;

/// <summary>
/// Modern C# conversion of LoginServlet.java
/// Same hardcoded credentials for parity testing
/// </summary>
public class LoginService
{
    private const string ValidUsername = "admin";
    private const string ValidPassword = "password123";
    
    private static readonly Dictionary<string, Dictionary<string, string>> Sessions = 
        new Dictionary<string, Dictionary<string, string>>();

    public LoginResult Login(string email, string password, string module)
    {
        Console.WriteLine($"Login attempt for user: {email}");

        if (IsValidCredentials(email, password))
        {
            var sessionId = Guid.NewGuid().ToString();
            var sessionData = new Dictionary<string, string>
            {
                { "user", email },
                { "module", module },
                { "createdAt", DateTime.UtcNow.ToString() }
            };
            Sessions[sessionId] = sessionData;

            Console.WriteLine($"Login successful for user: {email}");
            return new LoginResult
            {
                Success = true,
                Message = "Login successful",
                SessionId = sessionId,
                Module = module
            };
        }

        Console.WriteLine($"Login failed for user: {email}");
        return new LoginResult
        {
            Success = false,
            Message = "Invalid credentials"
        };
    }

    private bool IsValidCredentials(string email, string password)
    {
        // Same hardcoded check as legacy LoginServlet
        return email != null && email == ValidUsername &&
               password != null && password == ValidPassword;
    }
}

public class LoginResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = "";
    public string? SessionId { get; set; }
    public string Module { get; set; } = "";
}
