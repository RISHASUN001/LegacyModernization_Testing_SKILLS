param(
    [string]$InputPath = "module-run-input.json",
    [string]$ArtifactsRoot = "artifacts"
)

$ErrorActionPreference = "Stop"

$specJson = @'
{
  "name": "integration-test-execution",
  "stage": "execution",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Integration tests found data mapping defects.",
      "metrics": {
        "total": 22,
        "passed": 17,
        "failed": 5,
        "warnings": 0,
        "newTestsAdded": 3,
        "scenarios": [
          {
            "name": "Oracle alias to DTO mapping",
            "status": "failed",
            "notes": "RESOURCE_ID mismatch"
          },
          {
            "name": "Checklist save audit write",
            "status": "passed",
            "notes": "Write flow works"
          }
        ]
      },
      "findings": [
        {
          "type": "DapperMappingMismatch",
          "scenario": "Oracle alias to DTO mapping",
          "message": "RESOURCE_ID alias mismatch causes null DTO fields.",
          "likelyCause": "Alias differs from DTO property names.",
          "evidence": "ChecklistRepository_Load_MapsOracleAliases failed.",
          "severity": "high",
          "status": "open",
          "confidence": 0.88,
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/Infrastructure/ChecklistRepository.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Use explicit aliases matching DTO members and null-safe conversion.",
          "priority": "high",
          "evidence": "5 integration failures related to mapping."
        }
      ],
      "extra": {
        "log.txt": "dotnet test Checklist.IntegrationTests -> Passed:17 Failed:5"
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Integration failures reduced after mapping fixes.",
      "metrics": {
        "total": 28,
        "passed": 25,
        "failed": 3,
        "warnings": 1,
        "newTestsAdded": 4,
        "scenarios": [
          {
            "name": "Oracle alias to DTO mapping",
            "status": "passed",
            "notes": "Alias map fixed"
          },
          {
            "name": "Nullable date mapping",
            "status": "failed",
            "notes": "Two residual nullable cases"
          }
        ]
      },
      "findings": [
        {
          "type": "DapperMappingMismatch",
          "scenario": "Oracle alias to DTO mapping",
          "message": "Primary alias mismatch resolved; residual nullable date case remains.",
          "likelyCause": "Null date handling incomplete for two fields.",
          "evidence": "Most mapping tests passed; two nullable cases still failing.",
          "severity": "medium",
          "status": "resolved",
          "confidence": 0.8,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Alias map corrected and null guards added."
        }
      ],
      "recommendations": [
        {
          "message": "Close nullable date conversion edge failures in repository mapper.",
          "priority": "medium",
          "evidence": "3 integration failures remain."
        }
      ],
      "extra": {
        "log.txt": "dotnet test Checklist.IntegrationTests -> Passed:25 Failed:3 Warning:1"
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
