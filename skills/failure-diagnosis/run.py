#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "failure-diagnosis",
  "stage": "findings",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Failure diagnosis grouped key defects into 6 actionable clusters.",
      "metrics": {
        "clusters": 6,
        "highImpact": 4,
        "quickWins": 2
      },
      "findings": [
        {
          "type": "ClusteredFailurePattern",
          "scenario": "Data mapping and timeout cluster",
          "message": "Integration, e2e, and API failures share alias and timeout root causes.",
          "likelyCause": "Mapping and middleware gaps from migration.",
          "evidence": "Cross-skill correlation in diagnosis-report cluster #1/#2.",
          "severity": "high",
          "status": "open",
          "confidence": 0.79
        }
      ],
      "recommendations": [
        {
          "message": "Fix high-impact mapping and timeout clusters before rerunning full pipeline.",
          "priority": "high",
          "evidence": "These clusters drive most fail counts."
        }
      ],
      "extra": {
        "diagnosis-report.json": {
          "clusters": [
            {
              "name": "Data mapping cluster",
              "likelyCause": "Dapper alias mismatch",
              "affectedSkills": [
                "integration-test-execution",
                "api-test-execution"
              ]
            },
            {
              "name": "Timeout flow cluster",
              "likelyCause": "Session timeout middleware mismatch",
              "affectedSkills": [
                "e2e-test-execution",
                "playwright-browser-verification"
              ]
            }
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Failure diagnosis reduced to 2 low/medium clusters after major fixes.",
      "metrics": {
        "clusters": 2,
        "highImpact": 0,
        "quickWins": 2
      },
      "findings": [
        {
          "type": "ClusteredFailurePattern",
          "scenario": "Remaining flaky conflict paths",
          "message": "Remaining failures now centered on concurrent conflict warning race.",
          "likelyCause": "Timing-dependent lock state checks.",
          "evidence": "Failure cluster narrowed to e2e/playwright conflict scenarios.",
          "severity": "medium",
          "status": "open",
          "confidence": 0.71
        }
      ],
      "recommendations": [
        {
          "message": "Focus next iteration on deterministic lock-state synchronization in conflict flow.",
          "priority": "medium",
          "evidence": "Only 1-2 flaky scenarios remain."
        }
      ],
      "extra": {
        "diagnosis-report.json": {
          "clusters": [
            {
              "name": "Conflict lock timing",
              "likelyCause": "Non-deterministic lock propagation",
              "affectedSkills": [
                "e2e-test-execution",
                "playwright-browser-verification"
              ]
            }
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
