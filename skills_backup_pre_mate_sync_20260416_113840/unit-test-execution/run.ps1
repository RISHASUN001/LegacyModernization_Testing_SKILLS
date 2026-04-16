param(
    [string]$InputPath = "module-run-input.json",
    [string]$ArtifactsRoot = "artifacts"
)

$ErrorActionPreference = "Stop"

$specJson = @'
{
  "name": "unit-test-execution",
  "stage": "execution",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Unit tests executed with validation-related failures.",
      "metrics": {
        "total": 78,
        "passed": 62,
        "failed": 16,
        "warnings": 1,
        "newTestsAdded": 12,
        "scenarios": [
          {
            "name": "ATC verifier required rule",
            "status": "failed",
            "notes": "Missing validator check."
          },
          {
            "name": "Closed work order read-only guard",
            "status": "passed",
            "notes": "Guard enforced."
          }
        ]
      },
      "findings": [
        {
          "type": "ValidationRuleRegression",
          "scenario": "ATC verifier required rule",
          "message": "Validator does not enforce ATC verifier requirement.",
          "likelyCause": "Rule omitted during migration.",
          "evidence": "ChecklistValidator_RejectsMissingATCVerifier failed.",
          "severity": "high",
          "status": "open",
          "confidence": 0.93,
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/Application/ChecklistValidator.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Re-apply ATC required rule in validator and add explicit unit regression test.",
          "priority": "high",
          "evidence": "16 unit failures centered around validator path."
        }
      ],
      "extra": {
        "log.txt": "dotnet test Checklist.UnitTests -> Passed:62 Failed:16 Warning:1"
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Unit tests significantly improved after validation fixes.",
      "metrics": {
        "total": 96,
        "passed": 93,
        "failed": 3,
        "warnings": 0,
        "newTestsAdded": 8,
        "scenarios": [
          {
            "name": "ATC verifier required rule",
            "status": "passed",
            "notes": "Regression fixed."
          },
          {
            "name": "Closed work order read-only guard",
            "status": "passed",
            "notes": "Stable."
          }
        ]
      },
      "findings": [
        {
          "type": "ValidationRuleRegression",
          "scenario": "ATC verifier required rule",
          "message": "Validator regression resolved.",
          "likelyCause": "Rule restored and test expanded.",
          "evidence": "ChecklistValidator_RejectsMissingATCVerifier now passes.",
          "severity": "high",
          "status": "resolved",
          "confidence": 0.9,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Validator updated with ATC branch."
        }
      ],
      "recommendations": [
        {
          "message": "Address remaining 3 unit failures tied to async timing in validator pipeline.",
          "priority": "medium",
          "evidence": "Residual flaky async assertions."
        }
      ],
      "extra": {
        "log.txt": "dotnet test Checklist.UnitTests -> Passed:93 Failed:3 Warning:0"
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
