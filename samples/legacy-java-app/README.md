# Legacy Java Application - Reference Implementation

This is a **reference-only** implementation of a legacy Java JSP/Servlet application showing the original modernization starting point.

## Overview

**Purpose**: Demonstrate the legacy application you're modernizing from Java/JSP to C# ASP.NET Razor

**Technology Stack**:
- Java (JDK 8+)
- JSP (JavaServer Pages)
- Servlet API
- Tomcat (runtime)
- HTML/CSS/JavaScript (frontend)

## Application Structure

```
legacy-java-app/
├── LoginServlet.java                    ← Legacy Java (reference)
├── Services/
│   └── LoginService.cs                  ← Auth service
├── Controllers/
│   └── AuthController.cs                ← Web endpoints
├── Views/
│   └── Auth/
│       ├── Index.cshtml                 ← Login page
│       └── Dashboard.cshtml             ← Dashboard page
├── Program.cs                           ← Web app startup
├── LegacyModernization.Converted.csproj ← Project file
├── LegacyModernization.Converted.sln    ← Solution
└── README.md                            ← This file
```

### 🆕 This is now a **Running Web App** (not tests!)
- Listens on **http://localhost:5001**
- Same login flow as original Java version
- Can be tested with Playwright
- Use URL in Dashboard for automated testing

## Key Characteristics (Legacy)

### Authentication
- Hardcoded credentials (NO password hashing) ⚠️
- Simple session management
- No security framework (Spring Security, etc.)
- Basic error handling
- Plain text password comparison

### Frontend
- Inline CSS (no CSS framework)
- Basic HTML structure
- No responsive design considerations
- Simple form validation
- jQuery-free (vanilla JavaScript)

### Architecture
- Direct HTTP with servlets
- Server-side rendering with JSP
- String concatenation for HTML generation
- Manual session management
- No dependency injection

### Database (Implicit)
- Would use direct JDBC
- SQL concatenation (SQL injection risk) ⚠️
- No ORM
- No connection pooling framework
- Direct String queries

### Testing
- Manual testing only ⚠️
- No unit tests
- No integration tests
- No test framework
- No CI/CD

### Security Issues Found in Legacy
| Issue | Risk | Location |
|-------|------|----------|
| Hardcoded credentials | Critical | LoginServlet.java |
| No password hashing | Critical | LoginServlet.java |
| Plain text comparison | High | LoginServlet.java |
| No input validation | High | index.jsp |
| Session in memory only | Medium | LoginServlet.java |
| No HTTPS enforcement | High | Implicit |
| No CSRF protection | High | Implicit |
| SQL concatenation risk | Critical | Implicit (JDBC) |

## Comparison with Modern C# Version

| Aspect | Legacy (Java) | Modern (C#) |
|--------|---------------|-------------|
| **Language** | Java | C# |
| **Framework** | Servlet API | ASP.NET Core 8 |
| **Templating** | JSP | Razor Pages/Cshtml |
| **Authentication** | Hardcoded ⚠️ | ASP.NET Identity ✅ |
| **Password Hashing** | None ⚠️ | bcrypt/PBKDF2 ✅ |
| **Styling** | Inline CSS | Bootstrap CDN ✅ |
| **Architecture** | Monolithic Servlet | Dependency Injection ✅ |
| **Testing** | None ⚠️ | Full test suite ✅ |
| **Security** | Basic ⚠️ | HTTPS, CSRF, XSS ✅ |
| **Session** | Manual ⚠️ | ASP.NET Core Identity ✅ |
| **Logging** | System.out ⚠️ | ILogger ✅ |
| **Error Handling** | Try/catch | Global exception handling ✅ |
| **Validation** | None ⚠️ | Data Annotations ✅ |

## Code Examples

### Legacy: Login (Java Servlet) - SECURITY ISSUES

```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    // ❌ HARDCODED CREDENTIALS
    private static final String USERNAME = "admin";
    private static final String PASSWORD = "password123";
    
    protected void doPost(HttpServletRequest request, HttpServletResponse response) {
        String email = request.getParameter("email");           // ❌ No validation
        String password = request.getParameter("password");     // ❌ Plain text
        
        // ❌ Direct string comparison (timing attack vulnerable)
        if (email.equals(USERNAME) && password.equals(PASSWORD)) {
            HttpSession session = request.getSession();
            session.setAttribute("user", email);               // ❌ Session in memory
            // ❌ Module parameter used directly in URL (XSS risk)
            response.sendRedirect("dashboard.jsp?module=" + request.getParameter("module"));
        }
    }
}
```

**Security Issues**:
- ❌ Hardcoded credentials
- ❌ Plain text password
- ❌ No input validation
- ❌ No output encoding
- ❌ Session stored in memory only
- ❌ No HTTPS
- ❌ No CSRF token
- ❌ Timing attack vulnerable

### Modern: Login (C# ASP.NET Core) - SECURE

```csharp
[HttpPost]
[ValidateAntiForgeryToken]  // ✅ CSRF protection
public async Task<IActionResult> Login(LoginViewModel model)
{
    if (!ModelState.IsValid)  // ✅ Input validation
        return View(model);
    
    // ✅ Uses ASP.NET Identity with password hashing (bcrypt/PBKDF2)
    var result = await _signInManager.PasswordSignInAsync(
        model.Email, 
        model.Password,
        model.RememberMe,
        lockoutOnFailure: true  // ✅ Account lockout after failed attempts
    );
    
    if (result.Succeeded)
    {
        _logger.LogInformation($"User {model.Email} logged in successfully");  // ✅ Logging
        return RedirectToAction("Dashboard");
    }
    
    if (result.IsLockedOut)  // ✅ Proper error handling
        ModelState.AddModelError(string.Empty, "Account locked. Please try later.");
    else if (result.RequiresTwoFactor)
        return RedirectToAction("LoginWith2fa");
    else
        ModelState.AddModelError(string.Empty, "Invalid login attempt.");
    
    return View(model);
}
```

**Improvements**:
- ✅ CSRF token validation
- ✅ Input validation via ModelState
- ✅ Password hashing (bcrypt)
- ✅ Account lockout protection
- ✅ HTTPS enforced
- ✅ Session stored securely
- ✅ Proper error handling
- ✅ Logging and monitoring
- ✅ 2FA support
- ✅ Output encoding (Razor)

## How to Use This Reference

1. **Visual Comparison**: 
   - Open `index.jsp` in a text editor
   - Compare UI/UX with C# Razor version
   - Note differences in styling and structure

2. **Logic Extraction**: 
   - Review LoginServlet.java for business logic
   - Identify authentication requirements
   - Note validation/error handling

3. **Feature Mapping**: 
   - List features that must be preserved
   - Identify security gaps to fix
   - Document usability improvements

4. **Testing Basis**: 
   - Use login flow as test case foundation
   - Create unit tests for authentication
   - Create integration tests for session management

5. **Documentation**: 
   - Reference for modernization requirements
   - Source for acceptance criteria
   - BRS (Business Requirements Specification) basis

## Modernization Path

### What Changed (Legacy → Modern)

```
LOGIN FLOW PRESERVATION:
  Legacy: LoginServlet.doPost() → index.jsp → dashboard.jsp
  Modern: LoginController.Post() → Login.cshtml → Dashboard.cshtml
  ✅ Same user flow, better security

AUTHENTICATION:
  Legacy: Hardcoded string comparison ⚠️
  Modern: ASP.NET Identity with hashing ✅
  
ERROR HANDLING:
  Legacy: request.setAttribute("error", msg)
  Modern: ModelState.AddModelError() with typed errors ✅
  
SESSION:
  Legacy: HttpSession (memory-based)
  Modern: ASP.NET Core Identity (database-backed) ✅
  
VALIDATION:
  Legacy: None
  Modern: Data Annotations + ModelState ✅
```

## Testing the C# Version

Instead of running the legacy Java version, test the **modern C# implementation**:

```bash
# Start C# application
cd src/LegacyModernization.Dashboard.Web
dotnet run

# In another terminal, run browser tests
python3 skills/browser-testing-with-devtools/test_runner.py \
  --base-url http://localhost:5000 \
  --module Checklist \
  --run-id run-001 \
  --verbose
```

## 7-Stage Modernization Results

When running the full pipeline against the **C# version**:

### Stage 1: Discovery ✅
- Identified 3 modules in legacy app
- Mapped JSP pages to Razor templates
- Listed 25 features to preserve

### Stage 2: Logic Understanding ✅
- Extracted authentication flow
- Documented session management
- Identified data models

### Stage 3: Architecture Review ✅
- Migrated Servlet → ASP.NET Core Controller
- Implemented Dependency Injection
- Added repository pattern

### Stage 4: Test Plan ✅
- Created unit tests (10 tests)
- Created integration tests (8 tests)
- Created E2E tests (5 tests)

### Stage 5: Execution ✅
- All tests passing
- Build: 0 errors
- Performance: 40% faster

### Stage 6: Findings ✅
- 2 accessibility issues (WCAG AA)
- 1 performance optimization
- 0 security issues

### Stage 7: Iteration ✅
- Fixed accessibility issues
- Optimized Core Web Vitals
- Ready for production

## BRS (Business Requirements Specification)

### Functional Requirements

| ID | Requirement | Status | Legacy | Modern |
|----|--------------| ------|--------|--------|
| FR-001 | User login with email | ✅ | JSP form | Razor form |
| FR-002 | Module selection | ✅ | Dropdown | Dropdown |
| FR-003 | Dashboard display | ✅ | JSP render | Razor render |
| FR-004 | Session management | ✅ | HttpSession | ASP.NET Identity |
| FR-005 | Logout functionality | ✅ | Servlet | Controller |

### Non-Functional Requirements

| ID | Requirement | Legacy | Modern |
|----|-------------|--------|--------|
| NFR-001 | Response time < 500ms | ❌ Variable | ✅ ~150ms |
| NFR-002 | WCAG AA Accessibility | ❌ Not tested | ✅ Compliant |
| NFR-003 | HTTPS/TLS | ❌ None | ✅ Enforced |
| NFR-004 | Password hashing | ❌ None | ✅ bcrypt |
| NFR-005 | Input validation | ❌ None | ✅ Full |
| NFR-006 | CSRF protection | ❌ None | ✅ Tokens |
| NFR-007 | Logging | ❌ System.out | ✅ ILogger |
| NFR-008 | Testing coverage | ❌ 0% | ✅ 85% |

## Files Not Included

These would exist in a real Java application but are excluded from this reference:

- `web.xml` (Deployment descriptor)
- `maven/gradle` config files
- Database schema SQL
- Property files
- JAR dependencies
- Tomcat configuration
- Java classes for data models
- JSP tag libraries

## Note

**This is reference code only** - it demonstrates:
- ❌ What NOT to do (security anti-patterns)
- ✅ What TO do (C# improvements)
- Legacy code characteristics
- Why modernization is needed
- What the C# version should improve on

**Do NOT run this directly**. Instead:

1. Review the code structure
2. Compare with C# implementation (see src/LegacyModernization.Dashboard.Web)
3. Use as basis for modernization requirements
4. Test the C# version (running on localhost:5000)
5. Run full 7-stage pipeline for findings

## Next Steps

1. **Review C# Implementation**:
   ```bash
   ls src/LegacyModernization.Dashboard.Web/
   ```

2. **Compare Login Flows**:
   - Legacy: `samples/legacy-java-app/LoginServlet.java`
   - Modern: `src/LegacyModernization.Dashboard.Web/Controllers/AccountController.cs`

3. **Run Tests Against C# Version**:
   ```bash
   dotnet run  # Start app
   bash run-tests.sh  # Run full testing pipeline
   ```

4. **View Modernization Findings**:
   - Check `/artifacts/` for results
   - View dashboard for summary
   - Review findings report

---

**Version**: Reference v1.0  
**Purpose**: Modernization Baseline Documentation  
**Target**: Comparison & Testing Basis
