#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "module-documentation",
  "stage": "logic-understanding",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Module documentation published for checklist legacy parity baseline.",
      "metrics": {
        "sections": 6,
        "flowsDocumented": 5
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Review documentation with QA and SME before finalizing test plan.",
          "priority": "medium",
          "evidence": "Rule list drives test categories."
        }
      ],
      "extra": {
        "module-analysis.json": {
          "modulePurpose": "Checklist module ensures completion readiness before order closure.",
          "importantFlows": [
            "Open checklist",
            "Edit items",
            "Save draft",
            "Submit",
            "Review history"
          ],
          "rules": [
            "ATC verifier required",
            "Sensor fail blocks submit",
            "Read-only on closed work order"
          ],
          "dependencies": [
            "Checklist JS validation",
            "Oracle package",
            "WorkOrder service"
          ],
          "mustPreserve": [
            "Validation message order",
            "Timeout redirect",
            "Legacy URL compatibility"
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Module documentation updated with conflict handling and API parity notes.",
      "metrics": {
        "sections": 7,
        "flowsDocumented": 7
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Freeze module-analysis for this sprint and use for regression reviews.",
          "priority": "low",
          "evidence": "Documentation stable across flows."
        }
      ],
      "extra": {
        "module-analysis.json": {
          "modulePurpose": "Checklist module orchestrates draft, validation, and approval workflows for operational safety.",
          "importantFlows": [
            "Open checklist",
            "Auto-load latest draft",
            "Edit items",
            "Save draft",
            "Submit",
            "Review history",
            "Resolve concurrent edit conflict"
          ],
          "rules": [
            "ATC verifier required",
            "Sensor fail blocks submit",
            "Read-only on closed work order",
            "Duplicate submit idempotency"
          ],
          "dependencies": [
            "Checklist JS validation",
            "Oracle package",
            "WorkOrder service",
            "Conflict lock API"
          ],
          "mustPreserve": [
            "Validation message order",
            "Timeout redirect",
            "Legacy URL compatibility",
            "Conflict response contract"
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
