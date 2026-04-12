#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "edge-case-testing",
  "stage": "execution",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Edge-case testing found race and stale-session defects.",
      "metrics": {
        "total": 12,
        "passed": 7,
        "failed": 5,
        "warnings": 1,
        "newTestsAdded": 4,
        "scenarios": [
          {
            "name": "Duplicate submit race",
            "status": "failed",
            "notes": "Duplicate audit rows"
          },
          {
            "name": "Stale session edit",
            "status": "failed",
            "notes": "Unexpected 500 response"
          }
        ]
      },
      "findings": [
        {
          "type": "DuplicateSubmitRace",
          "scenario": "Duplicate submit race",
          "message": "Concurrent submit creates duplicate audit records.",
          "likelyCause": "No idempotency token check in save flow.",
          "evidence": "Edge-case matrix duplicate submit scenario failed twice.",
          "severity": "high",
          "status": "open",
          "confidence": 0.86,
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/Application/ChecklistCommandHandler.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Implement idempotency key logic for submit command path.",
          "priority": "high",
          "evidence": "Duplicate rows observed in edge-case run."
        }
      ],
      "extra": {
        "edge-case-matrix.json": {
          "scenarios": [
            {
              "name": "Duplicate submit race",
              "status": "failed"
            },
            {
              "name": "Stale session edit",
              "status": "failed"
            },
            {
              "name": "Empty payload submit",
              "status": "passed"
            }
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Edge-case scenarios improved after idempotency and session handling changes.",
      "metrics": {
        "total": 15,
        "passed": 13,
        "failed": 2,
        "warnings": 1,
        "newTestsAdded": 3,
        "scenarios": [
          {
            "name": "Duplicate submit race",
            "status": "passed",
            "notes": "Idempotency fix verified."
          },
          {
            "name": "Stale session edit",
            "status": "failed",
            "notes": "One branch still unstable"
          }
        ]
      },
      "findings": [
        {
          "type": "DuplicateSubmitRace",
          "scenario": "Duplicate submit race",
          "message": "Duplicate submit race resolved after idempotency implementation.",
          "likelyCause": "Request hash dedupe applied.",
          "evidence": "Edge-case duplicate scenario now passes.",
          "severity": "high",
          "status": "resolved",
          "confidence": 0.84,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Added request hash + time-window dedupe."
        }
      ],
      "recommendations": [
        {
          "message": "Address remaining stale-session branch instability.",
          "priority": "medium",
          "evidence": "2 edge-case failures remain."
        }
      ],
      "extra": {
        "edge-case-matrix.json": {
          "scenarios": [
            {
              "name": "Duplicate submit race",
              "status": "passed"
            },
            {
              "name": "Stale session edit",
              "status": "failed"
            },
            {
              "name": "Empty payload submit",
              "status": "passed"
            },
            {
              "name": "Slow sensor retry",
              "status": "passed"
            }
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
