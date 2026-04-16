param(
    [string]$InputPath = "module-run-input.json",
    [string]$ArtifactsRoot = "artifacts"
)

$ErrorActionPreference = "Stop"

$specJson = @'
{
  "name": "playwright-browser-verification",
  "stage": "execution",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Playwright browser verification found selector and runtime issues.",
      "metrics": {
        "total": 8,
        "passed": 5,
        "failed": 3,
        "warnings": 2,
        "newTestsAdded": 2,
        "scenarios": [
          {
            "name": "Checklist load",
            "status": "passed",
            "notes": "Initial render good."
          },
          {
            "name": "Save draft action",
            "status": "failed",
            "notes": "Selector mismatch."
          },
          {
            "name": "Submit validation banner",
            "status": "failed",
            "notes": "Banner missing on invalid ATC."
          }
        ]
      },
      "findings": [
        {
          "type": "PlaywrightSelectorDrift",
          "scenario": "Save draft action",
          "message": "Playwright selector no longer matches save button.",
          "likelyCause": "UI changed from #btnSave to data-test selector.",
          "evidence": "click selector timeout in playwright log.",
          "severity": "medium",
          "status": "open",
          "confidence": 0.8,
          "affectedFiles": [
            "src_conversion4/wwwroot/js/checklist.js",
            "tests/playwright/checklist.spec.ts"
          ]
        },
        {
          "type": "JsRuntimeError",
          "scenario": "Submit validation banner",
          "message": "JavaScript runtime error prevents validation rendering.",
          "likelyCause": "Null reference in checklist form binding.",
          "evidence": "TypeError in browser console at checklist.js:214",
          "severity": "high",
          "status": "open",
          "confidence": 0.85,
          "affectedFiles": [
            "src_conversion4/wwwroot/js/checklist.js"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Switch selectors to stable data-test attributes and fix runtime null guard.",
          "priority": "high",
          "evidence": "3 playwright failures and runtime console errors."
        }
      ],
      "extra": {
        "log.txt": "npx playwright test checklist.spec.ts -> Passed:5 Failed:3 Warnings:2",
        "console-logs.json": [
          "ERROR TypeError: Cannot read properties of undefined (reading trim) at checklist.js:214",
          "WARN Validation banner container not found in DOM",
          "ERROR Failed to execute save button click action"
        ],
        "network-failures.json": [
          "POST /api/checklist/save -> 500 Internal Server Error",
          "GET /api/checklist/lookup/atc -> 503 Service Unavailable"
        ],
        "dom-state.json": [
          "Validation banner missing after invalid submit",
          "Save button rendered with data-test=save-checklist (not #btnSave)"
        ],
        "runtime-issues.json": [
          "Unhandled promise rejection in saveDraft()",
          "Null binding path for checklist header form"
        ],
        "performance-observations.json": [
          "Checklist page load TTI 3.2s (target < 2.5s)",
          "First submit latency 1.8s"
        ],
        "screenshots/failure-save-selector.png": "__PNG__",
        "screenshots/failure-validation-banner.png": "__PNG__"
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Playwright verification improved with richer runtime evidence and fewer failures.",
      "metrics": {
        "total": 10,
        "passed": 9,
        "failed": 1,
        "warnings": 1,
        "newTestsAdded": 2,
        "scenarios": [
          {
            "name": "Checklist load",
            "status": "passed",
            "notes": "Stable render."
          },
          {
            "name": "Save draft action",
            "status": "passed",
            "notes": "Selector updated."
          },
          {
            "name": "Submit validation banner",
            "status": "passed",
            "notes": "Banner now visible."
          },
          {
            "name": "Concurrent tab conflict warning",
            "status": "failed",
            "notes": "Flaky conflict warning sequence."
          }
        ]
      },
      "findings": [
        {
          "type": "PlaywrightSelectorDrift",
          "scenario": "Save draft action",
          "message": "Selector drift issue resolved using data-test selectors.",
          "likelyCause": "Test selectors aligned with rendered DOM.",
          "evidence": "Save scenario passes in run-002.",
          "severity": "medium",
          "status": "resolved",
          "confidence": 0.83,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Updated selectors in playwright spec."
        },
        {
          "type": "JsRuntimeError",
          "scenario": "Submit validation banner",
          "message": "Runtime null-binding issue resolved with form guard.",
          "likelyCause": "Null-check added before trim()",
          "evidence": "No TypeError in console for submit path.",
          "severity": "high",
          "status": "resolved",
          "confidence": 0.8,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Added null guards in checklist binding script."
        }
      ],
      "recommendations": [
        {
          "message": "Stabilize concurrent tab conflict warning scenario by deterministic wait and lock handling.",
          "priority": "medium",
          "evidence": "1 remaining playwright failure in conflict branch."
        }
      ],
      "extra": {
        "log.txt": "npx playwright test checklist.spec.ts -> Passed:9 Failed:1 Warnings:1",
        "console-logs.json": [
          "WARN Retry invoked for concurrent conflict warning assertion",
          "INFO Validation banner rendered successfully for ATC failure case"
        ],
        "network-failures.json": [
          "PUT /api/checklist/lock -> 409 Conflict (expected in race scenario)"
        ],
        "dom-state.json": [
          "Validation banner present for invalid ATC submit",
          "Save button data-test selector validated"
        ],
        "runtime-issues.json": [
          "No blocking runtime exceptions in checklist flow"
        ],
        "performance-observations.json": [
          "Checklist page load TTI 2.3s",
          "Submit latency reduced to 1.2s"
        ],
        "screenshots/success-validation-banner.png": "__PNG__",
        "screenshots/flaky-concurrent-conflict.png": "__PNG__"
      }
    }
  }
}
'@
$spec = $specJson | ConvertFrom-Json -Depth 50

if (!(Test-Path $InputPath)) {
    throw "Input file not found: $InputPath"
}

$payload = Get-Content -Raw -Path $InputPath | ConvertFrom-Json -Depth 50
$moduleName = [string]$payload.moduleName
$runId = [string]$payload.runId
$profileKey = "baseline"
if ($runId -match '(\d+)$') {
    if ([int]$Matches[1] -ge 2) { $profileKey = "improved" }
}

$profile = $spec.profiles.$profileKey
if ($null -eq $profile) { $profile = $spec.profiles.baseline }

$outDir = Join-Path $ArtifactsRoot "$moduleName/$runId/$($spec.name)"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$startedAt = [DateTime]::UtcNow.ToString("o")
$artifacts = @()

if ($profile.extra -ne $null) {
    foreach ($prop in $profile.extra.PSObject.Properties) {
        $relative = $prop.Name
        $target = Join-Path $outDir $relative
        $parent = Split-Path -Parent $target
        if ($parent -and !(Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

        $value = $prop.Value
        if ($value -is [string]) {
            if ($value -eq "__PNG__") {
                $png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AApMBgU8R4X0AAAAASUVORK5CYII="
                [IO.File]::WriteAllBytes($target, [Convert]::FromBase64String($png))
            } else {
                Set-Content -Path $target -Value $value -Encoding UTF8
            }
        } else {
            $value | ConvertTo-Json -Depth 50 | Set-Content -Path $target -Encoding UTF8
        }

        $artifacts += ($target -replace "\\", "/")
    }
}

$endedAt = [DateTime]::UtcNow.ToString("o")
$resultPath = Join-Path $outDir "result.json"

$result = [ordered]@{
    skillName = [string]$spec.name
    stage = [string]$spec.stage
    moduleName = $moduleName
    runId = $runId
    status = [string]$profile.status
    startedAt = $startedAt
    endedAt = $endedAt
    summary = [string]$profile.summary
    metrics = $profile.metrics
    artifacts = @(($resultPath -replace "\\", "/")) + $artifacts
    findings = $profile.findings
    recommendations = $profile.recommendations
    resultContractVersion = "2.0"
}

$result | ConvertTo-Json -Depth 50 | Set-Content -Path $resultPath -Encoding UTF8
Write-Output ($resultPath -replace "\\", "/")
