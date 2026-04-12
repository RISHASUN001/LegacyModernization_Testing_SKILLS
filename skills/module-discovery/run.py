#!/usr/bin/env python3
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill

SPEC = {
  "name": "module-discovery",
  "stage": "discovery",
  "profiles": {
    "baseline": {
      "status": "passed",
      "summary": "Discovery completed with moderate confidence and 62 related assets.",
      "metrics": {
        "totalAssets": 62,
        "javaFiles": 28,
        "jspFiles": 11,
        "jsFiles": 8,
        "configFiles": 6,
        "urls": 5,
        "dbTouchpoints": 4,
        "confidence": 78
      },
      "findings": [
        {
          "type": "MissingLegacyEndpointMapping",
          "scenario": "Discovery URL mapping",
          "message": "One legacy save endpoint was not linked during initial scan.",
          "likelyCause": "Route alias not included in hints.",
          "evidence": "Missing /checklist/saveChecklist.do in first URL index.",
          "severity": "medium",
          "status": "open",
          "confidence": 0.74,
          "affectedFiles": [
            "src/struts-config.xml"
          ]
        }
      ],
      "recommendations": [
        {
          "message": "Add route aliases from Struts action mapping into module hints.",
          "priority": "medium",
          "evidence": "Route alias gap in discovery map."
        }
      ],
      "extra": {
        "discovery-map.json": {
          "javaFiles": [
            "src/com/seagate/edcs/checklist/action/ChecklistAction.java",
            "src/com/seagate/edcs/checklist/dao/ChecklistDao.java",
            "src/com/seagate/edcs/checklist/service/ChecklistService.java"
          ],
          "jspFiles": [
            "src/jsp/checklist/checklistMain.jsp",
            "src/jsp/checklist/checklistEdit.jsp"
          ],
          "jsFiles": [
            "src/jsp/checklist/js/checklist.js",
            "src/jsp/checklist/js/checklistValidation.js"
          ],
          "configFiles": [
            "src/struts-config.xml",
            "src/config/checklist.properties"
          ],
          "urls": [
            "/checklist/loadChecklist.do",
            "/checklist/viewChecklist.do"
          ],
          "dbTouchpoints": [
            "PKG_CHECKLIST.GET_HEADER",
            "PKG_CHECKLIST.GET_ITEMS",
            "PKG_CHECKLIST.SAVE_ITEMS"
          ]
        }
      }
    },
    "improved": {
      "status": "passed",
      "summary": "Discovery completed with high confidence and expanded URL/DB mapping.",
      "metrics": {
        "totalAssets": 79,
        "javaFiles": 34,
        "jspFiles": 13,
        "jsFiles": 11,
        "configFiles": 8,
        "urls": 8,
        "dbTouchpoints": 5,
        "confidence": 92
      },
      "findings": [],
      "recommendations": [
        {
          "message": "Persist discovery map as baseline for future iteration diffs.",
          "priority": "low",
          "evidence": "Stable asset map achieved."
        }
      ],
      "extra": {
        "discovery-map.json": {
          "javaFiles": [
            "src/com/seagate/edcs/checklist/action/ChecklistAction.java",
            "src/com/seagate/edcs/checklist/dao/ChecklistDao.java",
            "src/com/seagate/edcs/checklist/service/ChecklistService.java",
            "src/com/seagate/edcs/checklist/validator/ChecklistValidator.java"
          ],
          "jspFiles": [
            "src/jsp/checklist/checklistMain.jsp",
            "src/jsp/checklist/checklistEdit.jsp",
            "src/jsp/checklist/checklistHistory.jsp"
          ],
          "jsFiles": [
            "src/jsp/checklist/js/checklist.js",
            "src/jsp/checklist/js/checklistValidation.js",
            "src/jsp/checklist/js/checklistHistory.js"
          ],
          "configFiles": [
            "src/struts-config.xml",
            "src/config/checklist.properties",
            "src/config/workflow-rules.xml"
          ],
          "urls": [
            "/checklist/loadChecklist.do",
            "/checklist/viewChecklist.do",
            "/checklist/saveChecklist.do",
            "/checklist/validateChecklist.do"
          ],
          "dbTouchpoints": [
            "PKG_CHECKLIST.GET_HEADER",
            "PKG_CHECKLIST.GET_ITEMS",
            "PKG_CHECKLIST.SAVE_ITEMS",
            "PKG_CHECKLIST.SAVE_AUDIT"
          ]
        }
      }
    }
  }
}

if __name__ == "__main__":
    run_python_skill(SPEC)
