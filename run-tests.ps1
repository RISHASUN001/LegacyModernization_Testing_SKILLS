# Browser Testing Setup and Test Runner (Windows PowerShell)
# Automates the complete setup and testing workflow for Windows

param(
    [string]$Command,
    [string]$BaseUrl = "http://localhost:5276",
    [string]$Module = "Checklist",
    [string]$RunId = "run-001"
)

# Script paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = $ScriptDir
$DashboardDir = Join-Path $ProjectDir "src\LegacyModernization.Dashboard.Web"
$SkillsDir = Join-Path $ProjectDir "skills\browser-testing-with-devtools"
$DataDir = Join-Path $ProjectDir "data"

# Colors and output helpers
$Colors = @{
    Green = 'DarkGreen'
    Red = 'DarkRed'
    Yellow = 'DarkYellow'
    Blue = 'DarkCyan'
}

function Write-Header($Text) {
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor $Colors.Blue
    Write-Host "║ $Text" -ForegroundColor $Colors.Blue
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor $Colors.Blue
}

function Write-Success($Text) {
    Write-Host "✅ $Text" -ForegroundColor $Colors.Green
}

function Write-Error-Custom($Text) {
    Write-Host "❌ $Text" -ForegroundColor $Colors.Red
}

function Write-Warning-Custom($Text) {
    Write-Host "⚠️  $Text" -ForegroundColor $Colors.Yellow
}

function Write-Info($Text) {
    Write-Host "ℹ️  $Text" -ForegroundColor $Colors.Blue
}

# Check prerequisites
function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check .NET
    try {
        $dotnetVersion = dotnet --version
        Write-Success ".NET SDK found: $dotnetVersion"
    } catch {
        Write-Error-Custom ".NET SDK not found. Please install .NET 8 or later."
        exit 1
    }
    
    # Check Python
    try {
        $pythonVersion = python --version
        Write-Success "Python found: $pythonVersion"
    } catch {
        Write-Error-Custom "Python not found. Please install Python 3.7 or later."
        exit 1
    }
    
    # Check Git (optional)
    try {
        $gitVersion = git --version
        Write-Success "Git found: $gitVersion"
    } catch {
        Write-Warning-Custom "Git not found (optional)"
    }
}

# Build solution
function Build-Solution {
    Write-Header "Building Solution"
    
    Push-Location $ProjectDir
    Write-Info "Running: dotnet build"
    
    $buildOutput = dotnet build 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Build completed successfully"
        # Show last 10 lines
        $buildOutput | Select-Object -Last 10 | Write-Host
    } else {
        Write-Error-Custom "Build failed"
        $buildOutput | Write-Host
        Pop-Location
        exit 1
    }
    
    Pop-Location
}

# Setup data
function Setup-Data {
    Write-Header "Setting Up Data"
    
    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
        Write-Success "Data directory created"
    } else {
        Write-Success "Data directory exists"
    }
    
    $dbPath = Join-Path $DataDir "modernization.db"
    if (Test-Path $dbPath) {
        Write-Success "Database exists"
    } else {
        Write-Info "Database will be created on first run"
    }
}

# Start dashboard
function Start-Dashboard {
    Write-Header "Starting Dashboard Application"
    
    Push-Location $DashboardDir
    Write-Info "Starting: dotnet run"
    Write-Info "Dashboard will be available at http://localhost:5276"
    Write-Info "Press Ctrl+C to stop the dashboard"
    
    dotnet run
    Pop-Location
}

# Test dashboard
function Test-Dashboard {
    Write-Header "Testing Dashboard"
    
    Write-Info "Waiting for dashboard to start..."
    Start-Sleep -Seconds 3
    
    $attempts = 0
    while ($attempts -lt 10) {
        $attempts++
        try {
            $response = Invoke-WebRequest http://localhost:5276/api/test/health -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "Dashboard is responding"
                return $true
            }
        } catch {
            Write-Info "Attempt $attempts/10 - waiting..."
            Start-Sleep -Seconds 2
        }
    }
    
    Write-Error-Custom "Dashboard failed to respond"
    return $false
}

# Show login page
function Show-LoginPage {
    Write-Header "Test Login Page"
    
    $LoginFile = Join-Path $ProjectDir "test-login.html"
    
    if (-not (Test-Path $LoginFile)) {
        Write-Error-Custom "Login page not found: $LoginFile"
        return
    }
    
    Write-Success "Login page available at:"
    Write-Info "file://$LoginFile"
    Write-Host ""
    Write-Info "Or after dashboard starts:"
    Write-Info "http://localhost:5276/test-login.html"
    Write-Host ""
    Write-Info "Demo Credentials:"
    Write-Info "  Email: test@buildathon.dev"
    Write-Info "  Password: TestPassword123!"
    Write-Info "  Module: Checklist"
}

# List API endpoints
function List-APIEndpoints {
    Write-Header "Available Test API Endpoints"
    
    Write-Host ""
    Write-Host "Health Check:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/health"
    Write-Host ""
    Write-Host "Console Logs:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/console-logs | python -m json.tool"
    Write-Host ""
    Write-Host "Network Requests:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/network-requests | python -m json.tool"
    Write-Host ""
    Write-Host "Performance Metrics:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/performance-metrics | python -m json.tool"
    Write-Host ""
    Write-Host "Accessibility Report:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/accessibility-report | python -m json.tool"
    Write-Host ""
    Write-Host "DOM Structure:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/dom-structure | python -m json.tool"
    Write-Host ""
    Write-Host "Interaction Flows:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:5276/api/test/interaction-flows | python -m json.tool"
    Write-Host ""
}

# Run browser tests
function Run-BrowserTests {
    Write-Header "Running Browser Testing Tasks"
    
    Push-Location $ProjectDir
    
    Write-Info "Parameters:"
    Write-Info "  Base URL: $BaseUrl"
    Write-Info "  Module: $Module"
    Write-Info "  Run ID: $RunId"
    Write-Host ""
    
    & python "$SkillsDir\test_runner.py" `
        --base-url $BaseUrl `
        --module $Module `
        --run-id $RunId `
        --verbose
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Browser tests completed successfully"
    } else {
        Write-Error-Custom "Browser tests failed"
    }
    
    Pop-Location
}

# Show menu
function Show-Menu {
    Write-Header "Browser Testing - Main Menu"
    
    Write-Host ""
    Write-Host "1) Check prerequisites" -ForegroundColor Cyan
    Write-Host "2) Build solution" -ForegroundColor Cyan
    Write-Host "3) Setup data" -ForegroundColor Cyan
    Write-Host "4) Start dashboard" -ForegroundColor Cyan
    Write-Host "5) Test dashboard" -ForegroundColor Cyan
    Write-Host "6) Show login page" -ForegroundColor Cyan
    Write-Host "7) List API endpoints" -ForegroundColor Cyan
    Write-Host "8) Run browser tests (requires running dashboard)" -ForegroundColor Cyan
    Write-Host "9) Full setup (1-3) + start dashboard" -ForegroundColor Cyan
    Write-Host "0) Exit" -ForegroundColor Cyan
    Write-Host ""
}

# Main logic
if ([string]::IsNullOrEmpty($Command)) {
    # Interactive mode
    while ($true) {
        Show-Menu
        $choice = Read-Host "Select option"
        
        switch ($choice) {
            "1" { Check-Prerequisites }
            "2" { Build-Solution }
            "3" { Setup-Data }
            "4" { Start-Dashboard }
            "5" { Test-Dashboard }
            "6" { Show-LoginPage }
            "7" { List-APIEndpoints }
            "8" {
                $baseUrl = Read-Host "Base URL [http://localhost:5276]"
                if ([string]::IsNullOrEmpty($baseUrl)) { $baseUrl = "http://localhost:5276" }
                
                $module = Read-Host "Module [Checklist]"
                if ([string]::IsNullOrEmpty($module)) { $module = "Checklist" }
                
                $runId = Read-Host "Run ID [run-001]"
                if ([string]::IsNullOrEmpty($runId)) { $runId = "run-001" }
                
                Run-BrowserTests -BaseUrl $baseUrl -Module $module -RunId $runId
            }
            "9" {
                Check-Prerequisites
                Build-Solution
                Setup-Data
                Write-Info "Setup complete. Starting dashboard..."
                Start-Dashboard
            }
            "0" {
                Write-Info "Exiting"
                exit 0
            }
            default {
                Write-Error-Custom "Invalid option"
            }
        }
        
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
} else {
    switch ($Command.ToLower()) {
        "prerequisites" { Check-Prerequisites }
        "build" { Build-Solution }
        "setup" { Setup-Data }
        "start" { Start-Dashboard }
        "test" { Test-Dashboard }
        "login" { Show-LoginPage }
        "api" { List-APIEndpoints }
        "run-tests" { Run-BrowserTests -BaseUrl $BaseUrl -Module $Module -RunId $RunId }
        "full" {
            Check-Prerequisites
            Build-Solution
            Setup-Data
            Write-Info "Setup complete. Starting dashboard..."
            Start-Dashboard
        }
        "help" {
            Write-Host "Usage: .\run-tests.ps1 [command] [options]"
            Write-Host ""
            Write-Host "Commands:"
            Write-Host "  prerequisites   - Check prerequisites"
            Write-Host "  build           - Build solution"
            Write-Host "  setup           - Setup data"
            Write-Host "  start           - Start dashboard"
            Write-Host "  test            - Test dashboard"
            Write-Host "  login           - Show login page"
            Write-Host "  api             - List API endpoints"
            Write-Host "  run-tests       - Run browser tests"
            Write-Host "  full            - Full setup and test"
            Write-Host "  help            - Show this help"
            Write-Host ""
            Write-Host "No arguments: Interactive menu"
        }
        default {
            Write-Error-Custom "Unknown command: $Command"
            Write-Host "Run '.\run-tests.ps1 help' for usage"
            exit 1
        }
    }
}
