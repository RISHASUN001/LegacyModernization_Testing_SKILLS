#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "parity-verification",
  "stage": "findings",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Parity score indicates notable gaps in timeout and submit behavior.",
      "metrics": {
        "total": 24,
        "passed": 16,
        "failed": 8,
        "warnings": 1,
        "newTestsAdded": 2,
        "parityScore": 68
      },
      "findings": [
        {
          "type": "ParityGap",
          "scenario": "Timeout + submit parity",
          "message": "Converted module diverges from legacy timeout and submit response behavior.",
          "likelyCause": "Middleware and response contract differences.",
          "evidence": "Parity-diff highlights timeout redirect and submit payload mismatch.",
          "severity": "high",
          "status": "open",
          "confidence": 0.9
        }
      ],
      "recommendations": [
        {
          "message": "Close timeout redirect and submit contract gaps before release-readiness signoff.",
          "priority": "high",
          "evidence": "Parity score below target threshold."
        }
      ],
      "extra": {
        "parity-diff.json": {
          "parityScore": 68,
          "gaps": [
            "Timeout redirect behavior mismatch",
            "Submit response schema mismatch",
            "ATC warning ordering mismatch"
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Parity verification improved significantly with only minor behavioral differences remaining.",
      "metrics": {
        "total": 28,
        "passed": 25,
        "failed": 3,
        "warnings": 1,
        "newTestsAdded": 3,
        "parityScore": 91
      },
      "findings": [
        {
          "type": "ParityGap",
          "scenario": "Timeout + submit parity",
          "message": "Major parity gaps resolved; minor warning ordering issue remains.",
          "likelyCause": "Residual warning order difference in one branch.",
          "evidence": "Parity score improved to 91 with two minor deltas.",
          "severity": "medium",
          "status": "resolved",
          "confidence": 0.84,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Timeout and submit contracts now aligned with legacy baseline."
        }
      ],
      "recommendations": [
        {
          "message": "Resolve final warning-order and conflict-message text parity deltas.",
          "priority": "medium",
          "evidence": "3 parity checks still failing."
        }
      ],
      "extra": {
        "parity-diff.json": {
          "parityScore": 91,
          "gaps": [
            "ATC warning ordering differs in one edge branch",
            "Conflict message text differs slightly"
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
