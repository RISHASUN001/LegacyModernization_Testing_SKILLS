#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "legacy-logic-extraction",
  "stage": "logic-understanding",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Logic extraction identified 9 critical flows and preservation requirements.",
      "metrics": {
        "flows": 9,
        "rules": 8,
        "dependencies": 4,
        "preserveItems": 3
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Validate extracted preserve-list with SME before architecture refactor.",
          "priority": "medium",
          "evidence": "Session and redirect behavior depends on preserve-list."
        }
      ],
      "extra": {
        "logic-summary.json": {
          "modulePurpose": "Checklist validates work-order completion readiness with ATC and sensor checkpoints.",
          "importantFlows": [
            "Load checklist by work order",
            "Edit checklist rows by role",
            "Save draft checklist",
            "Submit checklist for verification"
          ],
          "rules": [
            "Closed work orders are read-only",
            "ATC fields require verifier id",
            "Sensor failures block final submit"
          ],
          "dependencies": [
            "WorkOrder module",
            "Sensor service",
            "Oracle package PKG_CHECKLIST"
          ],
          "mustPreserve": [
            "Legacy timeout redirect behavior",
            "ATC rule ordering",
            "Supervisor override branch"
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Logic extraction refined with additional validation and conflict flows.",
      "metrics": {
        "flows": 12,
        "rules": 10,
        "dependencies": 5,
        "preserveItems": 5
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Use mustPreserve list as parity acceptance checklist.",
          "priority": "high",
          "evidence": "Parity gaps map directly to preserve items."
        }
      ],
      "extra": {
        "logic-summary.json": {
          "modulePurpose": "Checklist governs draft, validation, and signoff lifecycle for operational readiness.",
          "importantFlows": [
            "Load checklist by work order",
            "Auto-load latest draft",
            "Edit checklist rows by role",
            "Save draft checklist",
            "Submit checklist for verification",
            "Handle concurrent edit conflict"
          ],
          "rules": [
            "Closed work orders are read-only",
            "ATC fields require verifier id",
            "Sensor failures block final submit",
            "Duplicate submit is idempotent"
          ],
          "dependencies": [
            "WorkOrder module",
            "Sensor service",
            "Approval service",
            "Oracle package PKG_CHECKLIST"
          ],
          "mustPreserve": [
            "Legacy timeout redirect behavior",
            "ATC rule ordering",
            "Supervisor override branch",
            "Conflict warning message contract"
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
