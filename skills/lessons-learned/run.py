#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "lessons-learned",
  "stage": "findings",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Lessons captured with action-oriented guidance for next run.",
      "metrics": {
        "lessons": 4,
        "actionItems": 4
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Track each resolved finding with explicit runId and evidence pointer.",
          "priority": "medium",
          "evidence": "Iteration explainability depends on traceability."
        }
      ],
      "extra": {
        "lessons.json": {
          "items": [
            "Alias mismatches can cascade across integration and API failures.",
            "Stable data-test selectors improve browser verification reliability.",
            "Timeout parity must be validated by e2e and playwright together."
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Lessons updated with stronger traceability and repeatable remediation patterns.",
      "metrics": {
        "lessons": 5,
        "actionItems": 3
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Adopt lessons template across all module modernization workstreams.",
          "priority": "low",
          "evidence": "Improved clarity in run-to-run diagnosis."
        }
      ],
      "extra": {
        "lessons.json": {
          "items": [
            "Resolved findings should include resolvedInRunId and evidence.",
            "Devtools evidence (console/network/runtime) accelerates browser bug triage.",
            "Ordering fixes by failure cluster impact reduces rerun churn."
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
