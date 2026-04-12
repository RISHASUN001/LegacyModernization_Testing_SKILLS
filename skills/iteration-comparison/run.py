#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "iteration-comparison",
  "stage": "iteration-comparison",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Baseline run has no prior iteration for comparison.",
      "metrics": {
        "testsAdded": 0,
        "testsFixed": 0,
        "failuresReduced": 0,
        "newFindingsIntroduced": 0,
        "resolvedFindings": 0,
        "previousRunId": ""
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Use run-001 as baseline and compare against run-002 onward.",
          "priority": "low",
          "evidence": "No previous run available."
        }
      ],
      "extra": {
        "iteration-delta.json": {
          "previousRunId": "",
          "testsAdded": 0,
          "testsFixed": 0,
          "failuresReduced": 0,
          "newFindingsIntroduced": 0,
          "resolvedFindings": 0,
          "progressionTrend": "baseline"
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Iteration comparison shows clear improvement over previous run.",
      "metrics": {
        "testsAdded": 12,
        "testsFixed": 26,
        "failuresReduced": 29,
        "newFindingsIntroduced": 2,
        "resolvedFindings": 7,
        "previousRunId": "run-001"
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Address remaining new findings in conflict-race scenarios in next run.",
          "priority": "medium",
          "evidence": "Trend improving but 2 new low/medium findings introduced."
        }
      ],
      "extra": {
        "iteration-delta.json": {
          "previousRunId": "run-001",
          "testsAdded": 12,
          "testsFixed": 26,
          "failuresReduced": 29,
          "newFindingsIntroduced": 2,
          "resolvedFindings": 7,
          "progressionTrend": "improving"
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
