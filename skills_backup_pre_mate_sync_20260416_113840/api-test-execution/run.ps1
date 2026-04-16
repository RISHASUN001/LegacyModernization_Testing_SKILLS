param(
    [string]$InputPath = "module-run-input.json",
    [string]$ArtifactsRoot = "artifacts"
)

$ErrorActionPreference = "Stop"

$specJson = @'
{
  "name": "api-test-execution",
  "stage": "execution",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "API tests show route and response contract mismatch.",
      "metrics": {
        "total": 18,
        "passed": 13,
        "failed": 5,
        "warnings": 0,
        "newTestsAdded": 4,
        "scenarios": [
          {
            "name": "Legacy save route compatibility",
            "status": "failed",
            "notes": "404 on /saveChecklist.do"
          },
          {
            "name": "Validation response schema",
            "status": "failed",
            "notes": "Error contract mismatch"
          }
        ]
      },
      "findings": [
        {
          "type": "RouteParityMismatch",
          "scenario": "Legacy save route compatibility",
          "message": "Legacy .do route not mapped in converted API.",
          "likelyCause": "Compatibility route not configured.",
          "evidence": "POST /checklist/saveChecklist.do returns 404.",
          "severity": "high",
          "status": "open",
          "confidence": 0.91,
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/Web/ChecklistController.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Add compatibility route aliases and align validation error schema.",
          "priority": "high",
          "evidence": "5 API failures on compatibility and validation paths."
        }
      ],
      "extra": {
        "log.txt": "newman run checklist-api.json -> Passed:13 Failed:5"
      }
    },
    "improved": {
      "status": "passed",
      "summary": "API tests largely pass after route compatibility updates.",
      "metrics": {
        "total": 21,
        "passed": 20,
        "failed": 1,
        "warnings": 0,
        "newTestsAdded": 2,
        "scenarios": [
          {
            "name": "Legacy save route compatibility",
            "status": "passed",
            "notes": "Route alias added."
          },
          {
            "name": "Validation response schema",
            "status": "passed",
            "notes": "Schema aligned."
          }
        ]
      },
      "findings": [
        {
          "type": "RouteParityMismatch",
          "scenario": "Legacy save route compatibility",
          "message": "Route compatibility issue resolved.",
          "likelyCause": "Added alias routes for legacy .do endpoints.",
          "evidence": "Legacy route tests now pass.",
          "severity": "high",
          "status": "resolved",
          "confidence": 0.87,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Configured compatibility route mapping."
        }
      ],
      "recommendations": [
        {
          "message": "Fix remaining optional query default behavior in one API edge path.",
          "priority": "medium",
          "evidence": "1 API failure left."
        }
      ],
      "extra": {
        "log.txt": "newman run checklist-api.json -> Passed:20 Failed:1"
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
