#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "clean-architecture-assessment",
  "stage": "architecture-review",
  "profiles": {
    "baseline": {
      "status": "failed",
      "summary": "Architecture review identified critical DI and coupling issues.",
      "metrics": {
        "violations": 6,
        "critical": 2,
        "warnings": 4
      },
      "findings": [
        {
          "type": "DirectInfrastructureDependency",
          "scenario": "Controller to repository coupling",
          "message": "ChecklistController depends directly on Oracle repository implementation.",
          "likelyCause": "Missing application-level repository abstraction.",
          "evidence": "ChecklistController constructor injects ChecklistOracleRepository.",
          "severity": "high",
          "status": "open",
          "confidence": 0.9,
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/ChecklistController.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Introduce application interfaces and move infrastructure binding to composition root.",
          "priority": "high",
          "evidence": "Direct implementation injection detected."
        }
      ],
      "extra": {
        "architecture-review.json": {
          "cleanArchitectureIssues": [
            {
              "title": "Web layer references infrastructure directly",
              "severity": "high",
              "evidence": "Controller -> Oracle repo dependency"
            },
            {
              "title": "Application layer contains SQL literals",
              "severity": "medium",
              "evidence": "Query strings in service class"
            }
          ],
          "namespaceFolderIssues": [
            {
              "title": "DTOs live under Web namespace",
              "severity": "medium",
              "evidence": "DTO path under Controllers folder"
            }
          ],
          "diIssues": [
            {
              "title": "Missing scoped registration for checklist validators",
              "severity": "high",
              "evidence": "Service collection lacks AddScoped<ChecklistValidator>"
            }
          ],
          "couplingIssues": [
            {
              "title": "Checklist service orchestrates persistence and HTTP concerns",
              "severity": "medium",
              "evidence": "Service receives HttpContext and repository"
            }
          ],
          "recommendedStructure": [
            "Modules/Checklist/Application for use cases and contracts",
            "Modules/Checklist/Infrastructure for Oracle/Dapper repositories",
            "Modules/Checklist/Web for controllers and view models only"
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Architecture review shows major critical issues resolved; one minor namespace warning remains.",
      "metrics": {
        "violations": 2,
        "critical": 0,
        "warnings": 2
      },
      "findings": [
        {
          "type": "DirectInfrastructureDependency",
          "scenario": "Controller to repository coupling",
          "message": "Controller now uses application abstraction and DI registration corrected.",
          "likelyCause": "Resolved through use-case abstraction.",
          "evidence": "Controller injects IChecklistQueryUseCase.",
          "severity": "high",
          "status": "resolved",
          "confidence": 0.89,
          "resolvedInRunId": "run-002",
          "resolutionNotes": "Dependency moved behind application layer interface.",
          "affectedFiles": [
            "src_conversion4/Modules/Checklist/ChecklistController.cs"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Finalize namespace cleanup for remaining DTO class placement.",
          "priority": "low",
          "evidence": "One DTO still under migration namespace."
        }
      ],
      "extra": {
        "architecture-review.json": {
          "cleanArchitectureIssues": [
            {
              "title": "No critical boundary breach detected",
              "severity": "low",
              "evidence": "Dependency direction validated"
            }
          ],
          "namespaceFolderIssues": [
            {
              "title": "One DTO namespace still uses migration prefix",
              "severity": "low",
              "evidence": "ChecklistResponseDto namespace mismatch"
            }
          ],
          "diIssues": [
            {
              "title": "Validator and use case services registered correctly",
              "severity": "low",
              "evidence": "Service collection updated"
            }
          ],
          "couplingIssues": [
            {
              "title": "Minor coupling around telemetry helper remains",
              "severity": "low",
              "evidence": "Shared logger utility still static"
            }
          ],
          "recommendedStructure": [
            "Finalize Contracts namespace under Application",
            "Keep Infrastructure registration centralized in composition root"
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
