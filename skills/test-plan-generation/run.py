#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "test-plan-generation",
  "stage": "test-plan",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Test plan generated with explicit category purpose and initial coverage gaps.",
      "metrics": {
        "existingTests": 61,
        "suggestedTests": 24,
        "coveragePercent": 64
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Prioritize API and edge-case scenarios before parity gate.",
          "priority": "high",
          "evidence": "Coverage low on compatibility and resilience flows."
        }
      ],
      "extra": {
        "test-plan.json": {
          "existingTestsFound": [
            "61 tests across unit/integration/API in converted solution",
            "No dedicated e2e regression suite yet"
          ],
          "newTestsSuggested": [
            "Add e2e submit/timeout journey",
            "Add stale-session and duplicate-submit edge cases",
            "Add Playwright DOM-state assertions for validation banners"
          ],
          "testCategories": [
            {
              "category": "Unit",
              "purpose": "Validate domain rules and validators quickly."
            },
            {
              "category": "Integration",
              "purpose": "Validate repository mapping and service orchestration."
            },
            {
              "category": "E2E",
              "purpose": "Validate full journey across API, UI, and data updates."
            },
            {
              "category": "API",
              "purpose": "Validate endpoint contract and status code behavior."
            },
            {
              "category": "Edge Case",
              "purpose": "Validate resilience paths and rare failure conditions."
            },
            {
              "category": "Playwright / Browser Verification",
              "purpose": "Validate browser behavior with runtime/network evidence."
            }
          ],
          "coverageSummary": "Overall functional coverage estimated at 64%; weakest areas are e2e parity and browser-state assertions."
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Test plan refined with stronger category mapping and increased projected coverage.",
      "metrics": {
        "existingTests": 84,
        "suggestedTests": 17,
        "coveragePercent": 82
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Lock current test plan and carry remaining suggestions into next sprint backlog.",
          "priority": "medium",
          "evidence": "High-value categories now covered."
        }
      ],
      "extra": {
        "test-plan.json": {
          "existingTestsFound": [
            "84 tests across all categories including new e2e flows",
            "Playwright suite includes runtime/console/network checks"
          ],
          "newTestsSuggested": [
            "Add one more conflict-resolution e2e scenario",
            "Add performance threshold check for checklist load under 2.5s"
          ],
          "testCategories": [
            {
              "category": "Unit",
              "purpose": "Validate domain rules and validators quickly."
            },
            {
              "category": "Integration",
              "purpose": "Validate repository mapping and service orchestration."
            },
            {
              "category": "E2E",
              "purpose": "Validate full journey across API, UI, and data updates."
            },
            {
              "category": "API",
              "purpose": "Validate endpoint contract and status code behavior."
            },
            {
              "category": "Edge Case",
              "purpose": "Validate resilience paths and rare failure conditions."
            },
            {
              "category": "Playwright / Browser Verification",
              "purpose": "Validate browser behavior with runtime/network evidence."
            }
          ],
          "coverageSummary": "Overall functional coverage estimated at 82%; remaining risk is concurrent conflict handling under load."
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
