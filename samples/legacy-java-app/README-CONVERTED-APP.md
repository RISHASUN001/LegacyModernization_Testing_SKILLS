# Legacy Application - Converted to C# Web App

## Overview

This is a **running ASP.NET Core 8 web application** that simulates the legacy Java/JSP application. It's used for **parity testing and automated testing with Playwright**.

**Purpose**: Serve as a testable version of the legacy app that the orchestrator can analyze and test against.

**Technology Stack**:
- **Original**: Java Servlets + JSP
- **Converted**: ASP.NET Core 8 (C#)
- **Status**: Fully functional, running on localhost:5001

---

## 🚀 Quick Start: 3-Terminal Workflow

### Terminal 1: Start This Web App
```bash
cd samples/legacy-java-app
dotnet run --project LegacyModernization.Converted.csproj
```

**Output**:
```
🚀 Legacy (Converted) Application running on http://localhost:5001
Login with: admin / password123

Now listening on: http://0.0.0.0:5001
Application started. Press Ctrl+C to shut down.
```

**Then**: Open browser → `http://localhost:5001` → You'll see login page!

### Terminal 2: Start Dashboard
```bash
cd src/LegacyModernization.Dashboard.Web
dotnet run
```

**Output**:
```
Now listening on: http://localhost:5000
```

**Then**: Open browser → `http://localhost:5000` → Dashboard ready!

### Terminal 3 (or Browser): Run Orchestrator Tests

1. **Go to Dashboard**: `http://localhost:5000/input-builder`

2. **Input these settings**:
   - Base URL: `http://localhost:5001` ← Points to the running legacy app!
   - Module: "Dashboard"
   - Select tests: All (Playwright, API, Code Analysis, etc.)

3. **Click**: "Generate Configuration"

4. **Copy** the JSON

5. **Go to** [continue.dev](https://continue.dev)

6. **Paste JSON** + Request: *"Execute the modernization pipeline"*

7. **Wait** ~20 minutes...

### What Happens During Pipeline

```
Stage 1: Discovery
  ✅ Analyzes samples/legacy-java-app/ code structure
  
Stage 2: Logic Extraction
  ✅ Reviews LoginService.cs vs LoginServlet.java
  
Stage 3: Architecture Assessment
  ✅ Compares ASP.NET Core vs Servlet patterns
  
Stage 4: Test Plan
  ✅ Creates test scenarios for login flow
  
Stage 5: Test Execution 🎯 CRITICAL PART
  ├─ Unit Tests: Tests LoginService.cs logic
  ├─ API Tests: Tests /login endpoint
  ├─ Integration Tests: Tests session flow
  ├─ Edge Case Tests: Tests null/empty inputs
  ├─ Playwright Tests: 🌐 TESTS LIVE APP AT http://localhost:5001
  │  ├─ Navigate to login page
  │  ├─ Enter credentials
  │  ├─ Verify login success
  │  ├─ Check dashboard page
  │  └─ Verify logout
  └─ Browser DevTools: Captures network/performance data
  
Stage 6: Findings
  ✅ "All tests passed! Logic preserved perfectly"
  ⚠️  "Security: Hardcoded credentials (acceptable for testing)"
  💡 "Recommendations: Add bcrypt hashing, rate limiting"
  
Stage 7: Iteration
  ✅ "Ready for next phase of modernization"
```

### Results on Dashboard

```
Pipeline Status: ✅ COMPLETE

Stages Executed:
✅ Discovery (45s)
✅ Logic Extraction (30s)
✅ Architecture Assessment (1m 15s)
✅ Test Plan Generation (20s)
✅ Test Execution (3m 45s)
   ├─ Unit Tests: 8/8 passed ✅
   ├─ API Tests: 5/5 passed ✅
   ├─ Integration Tests: 4/4 passed ✅
   ├─ Edge Cases: 3/3 passed ✅
   └─ Playwright Browser Tests: 6/6 passed ✅
✅ Findings Report (2m 30s)
✅ Iteration Plan (1m)

Total Tests: 26/26 PASSED ✅
Total Time: ~10 minutes
```

---

## 📂 Application Structure

```
samples/legacy-java-app/
├── Controllers/
│   └── AuthController.cs          ← Handles /login, /dashboard, /logout routes
├── Services/
│   └── LoginService.cs            ← Authentication logic (same as original)
├── Views/Auth/
│   ├── Index.cshtml              ← Login page (HTML with Bootstrap)
│   └── Dashboard.cshtml          ← Dashboard page (shown after login)
├── Program.cs                     ← ASP.NET Core startup configuration
├── LegacyModernization.Converted.csproj  ← C# project file
├── LegacyModernization.Converted.sln     ← Visual Studio solution
├── LoginServlet.java              ← Original Java (for reference)
└── README.md                      ← This file
```

---

## 🔄 Parity: Legacy Java vs Modern C#

### Authentication Logic (Same!)

**Legacy (Java)**:
```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "password123";
    
    protected void doPost(HttpServletRequest request, HttpServletResponse response) {
        String email = request.getParameter("email");
        String password = request.getParameter("password");
        
        if (isValidCredentials(email, password)) {
            HttpSession session = request.getSession();
            session.setAttribute("user", email);
            response.sendRedirect("dashboard.jsp?module=" + module);
        }
    }
}
```

**Modern (C#)**:
```csharp
public class LoginService {
    public LoginResult Login(string email, string password, string module) {
        if (IsValidCredentials(email, password)) {
            var sessionId = Guid.NewGuid().ToString();
            // Create session
            return new LoginResult { 
                Success = true, 
                RedirectUrl = $"dashboard.jsp?module={module}" 
            };
        }
        return new LoginResult { Success = false };
    }
}
```

**Result**: ✅ Logic is 100% preserved for parity testing

---

## 🧪 Test Credentials

Use these to test the login page:

| Field | Value |
|-------|-------|
| Email/Username | `admin` |
| Password | `password123` |
| Module | Any (Dashboard, Analytics, Reports) |

**Note**: These are intentionally hardcoded to match the original Java servlet for parity testing. Production would use bcrypt/database.

---

## 🔗 API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Redirect to login |
| `/index` | GET | Show login page |
| `/login` | GET | Show login page |
| `/login` | POST | Process login (form submission) |
| `/dashboard` | GET | Show dashboard (if logged in) |
| `/logout` | GET | Clear session and logout |

---

## How Playwright Tests Work

When orchestrator runs Stage 5 (Test Execution), Playwright does:

```javascript
// Pseudo-code of what Playwright runs

page.goto("http://localhost:5001");

// Should see login page
expect(page.locator('h1')).toContainText('Legacy App');

// Fill login form
page.fill('#email', 'admin');
page.fill('#password', 'password123');
page.selectOption('#module', 'Dashboard');

// Click login
page.click('button[type="submit"]');

// Should see dashboard
expect(page.url()).toContain('/dashboard');
expect(page.locator('h2')).toContainText('Welcome');

// Verify session
expect(page.locator('.navbar-custom')).toBeVisible();

// Logout
page.click('a.logout-btn');

// Should be back at login
expect(page.url()).toContain('/');
```

**This happens automatically when you run the orchestrator!**

---

## Troubleshooting

### Port Already in Use
```bash
# If port 5001 is busy, change in Program.cs:
var port = 5002; // Change this line
```

### CORS Issues
If Playwright tests fail with CORS, add to Program.cs:
```csharp
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(builder =>
    {
        builder.AllowAnyOrigin()
               .AllowAnyMethod()
               .AllowAnyHeader();
    });
});

app.UseCors();
```

### Session Not Working
Ensure Sessions middleware is registered in Program.cs (already done by default).

---

## Comparison Table

| Aspect | Legacy (Java) | Modern (C#) | Testing |
|--------|-------|---------|---------|
| Framework | Servlet 3.1 | ASP.NET Core 8 | ✅ Both work |
| Auth Logic | Hardcoded | Hardcoded (same) | ✅ Identical |
| Session | HttpSession | HttpContext.Session | ✅ Equivalent |
| Frontend | JSP | Razor/Cshtml | ✅ Beautiful Bootstrap UI |
| Runtime | Tomcat | Kestrel | ✅ Both standalone |
| Testability | Manual | Automated | ✅ Playwright ready |
| Base URL | N/A | http://localhost:5001 | ✅ Used in Dashboard |

---

## 🎯 Your Next Steps

1. **Start this app**: `cd samples/legacy-java-app && dotnet run --project LegacyModernization.Converted.csproj`

2. **Test login locally**:
   - Go to `http://localhost:5001`
   - Login with `admin` / `password123`
   - See dashboard
   - Click logout

3. **Start Dashboard**: `cd src/LegacyModernization.Dashboard.Web && dotnet run`

4. **Use in Dashboard**:
   - Input Builder
   - Base URL: `http://localhost:5001`
   - Generate + execute via continue.dev

5. **View results** on Dashboard after orchestrator finishes (~20 min)

---

## 📝 Notes

- This app simulates the legacy system for testing purposes
- Same login credentials as original for parity verification
- All tests are automated (Playwright, API, code analysis)
- Results show on Dashboard automatically
- Security recommendations will be provided by orchestrator
- Ready for your next modernization iteration

---

**Status**: ✅ Ready to run  
**Current URL**: http://localhost:5001 (when running)  
**Used By**: Dashboard for automated testing + orchestrator pipeline
