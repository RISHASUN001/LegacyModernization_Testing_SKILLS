#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import run_python_skill
from skill_logic import previous_run_id

SPEC = {
    "name": "lessons-learned",
    "stage": "findings",
    "requiredInputs": ["moduleName", "runId"],
}


SEED_SIGNATURE_HINTS = {
    "dapper": "DapperCaseSensitivity",
    "namespace": "NamespaceFolderMismatch",
    "di": "DIRegistrationMissing",
    "relative url": "RelativeUrlFailure",
    "oracle": "OracleMappingIssue",
    "session": "SessionHandlingPitfall",
    "route": "RouteAssumptionMismatch",
    "viewmodel": "ViewModelBindingMismatch",
    "model binding": "ViewModelBindingMismatch",
    "case sensitive": "DapperCaseSensitivity",
    "column name": "DapperCaseSensitivity",
    "property mapping": "ViewModelBindingMismatch",
    "null reference": "NullReferenceException",
    "session expired": "SessionHandlingPitfall",
}


def _read_result(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _collect_findings(run_root: Path) -> dict[str, dict]:
    findings: dict[str, dict] = {}
    for result_path in run_root.glob("*/result.json"):
        data = _read_result(result_path)
        skill = str(data.get("skillName") or result_path.parent.name)
        stage = str(data.get("stage") or "")
        for item in data.get("findings", []) or []:
            if not isinstance(item, dict):
                continue
            signature = f"{item.get('type','General')}::{item.get('scenario','')}::{item.get('message','')}"
            findings[signature] = {
                "signature": signature,
                "type": str(item.get("type", "General")),
                "scenario": str(item.get("scenario", "")),
                "message": str(item.get("message", "")),
                "likelyCause": str(item.get("likelyCause", "")),
                "evidence": str(item.get("evidence", "")),
                "stage": stage,
                "skill": skill,
                "confidence": float(item.get("confidence") or 0.65),
            }
    return findings


def _derive_recurring_signatures(current: dict[str, dict], previous: dict[str, dict]) -> list[str]:
    recurring = sorted(set(previous.keys()) & set(current.keys()))
    out: list[str] = []
    for signature in recurring:
        out.append(signature)

    # Seed stable signatures from known modernization pitfalls when they appear in findings text.
    corpus = " ".join([f"{v.get('message','')} {v.get('likelyCause','')} {v.get('evidence','')}".lower() for v in current.values()])
    for keyword, signature in SEED_SIGNATURE_HINTS.items():
        if keyword in corpus and signature not in out:
            out.append(signature)

    return out[:80]


def execute(ctx):
    module_root = ctx.artifacts_root / ctx.module_name
    run_root = module_root / ctx.run_id
    prev_id = previous_run_id(ctx.artifacts_root, ctx.module_name, ctx.run_id)
    prev_root = module_root / prev_id if prev_id else None

    current_findings = _collect_findings(run_root)
    previous_findings = _collect_findings(prev_root) if prev_root and prev_root.exists() else {}

    resolved = sorted(set(previous_findings.keys()) - set(current_findings.keys()))
    recurring = sorted(set(previous_findings.keys()) & set(current_findings.keys()))
    new_items = sorted(set(current_findings.keys()) - set(previous_findings.keys()))

    lessons = {
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "previousRunId": prev_id,
        "resolvedIssues": resolved,
        "recurringIssues": recurring,
        "newIssues": new_items,
        "knowledgeUpdates": [
            {
                "signature": sig,
                "stage": current_findings.get(sig, {}).get("stage", "findings"),
                "skill": current_findings.get(sig, {}).get("skill", "unknown-skill"),
                "message": current_findings.get(sig, {}).get("message", ""),
                "recommendedGuard": "Add targeted regression scenario in next test plan.",
            }
            for sig in new_items[:30]
        ],
    }

    knowledge_root = ctx.artifacts_root / ctx.module_name / "_knowledge-base"
    knowledge_root.mkdir(parents=True, exist_ok=True)
    kb_path = knowledge_root / "lessons-kb.json"

    existing_kb = _read_result(kb_path)
    recurring_signatures = _derive_recurring_signatures(current_findings, previous_findings)

    kb = {
        "moduleName": ctx.module_name,
        "updatedAt": ctx.started_at,
        "latestRunId": ctx.run_id,
        "recurringSignatures": recurring_signatures,
        "knownPitfalls": sorted(
            set((existing_kb.get("knownPitfalls", []) if isinstance(existing_kb.get("knownPitfalls"), list) else []) + [
                "DapperCaseSensitivity",
                "NamespaceFolderMismatch",
                "DIRegistrationMissing",
                "RelativeUrlFailure",
                "OracleMappingIssue",
                "SessionHandlingPitfall",
                "RouteAssumptionMismatch",
            ])
        ),
        "history": (existing_kb.get("history", []) if isinstance(existing_kb.get("history"), list) else [])[-8:] + [
            {
                "runId": ctx.run_id,
                "resolvedCount": len(resolved),
                "recurringCount": len(recurring),
                "newCount": len(new_items),
            }
        ],
    }

    kb_path.write_text(json.dumps(kb, indent=2), encoding="utf-8")
    ctx.add_artifact(kb_path)

    ctx.write_json("lessons-learned.json", lessons)
    ctx.write_json("lessons.json", lessons)

    recommendations = [
        {
            "message": "Use recurring lesson signatures to generate mandatory regression scenarios in next run.",
            "priority": "high" if recurring else "medium",
            "evidence": f"recurring={len(recurring)}, resolved={len(resolved)}, new={len(new_items)}",
        }
    ]

    return {
        "status": "passed",
        "summary": (
            f"Lessons synthesized for {ctx.module_name}: resolved={len(resolved)}, "
            f"recurring={len(recurring)}, new={len(new_items)}."
        ),
        "metrics": {
            "resolved": len(resolved),
            "recurring": len(recurring),
            "new": len(new_items),
            "kbRecurringSignatures": len(recurring_signatures),
        },
        "findings": [],
        "recommendations": recommendations,
        "provenanceSummary": {
            "scenarioSources": ["code-evidence", "lessons-learned"],
            "confidence": 0.84,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
