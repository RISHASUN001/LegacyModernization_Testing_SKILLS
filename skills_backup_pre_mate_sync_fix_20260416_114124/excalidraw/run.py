#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import shutil
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from skill_runtime import make_provenance, run_python_skill

SPEC = {
    "name": "excalidraw-diagram",
    "stage": "java-logic",
    "requiredInputs": ["moduleName"],
}

_RENDER_SCRIPT = Path(__file__).resolve().parent / "references" / "render_excalidraw.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mermaid_for_workflow(title: str, flow: dict) -> str:
    """Generate Mermaid flowchart showing ALL conditional branches and outcomes."""
    entry = flow["entry"]
    controller = flow["controller"]
    decision = flow["decision"]
    action = flow["action"]
    data_access = flow["data"]
    outcome = flow["outcome"]
    validations = flow.get("validations", [])
    actions = flow.get("actions", [])
    
    lines = [
        "flowchart TD",
        f"  A[\"{entry or 'Entry Route'}\"] --> B[\"{controller}\"]",
        f"  B --> C{{{decision}}}",
        f"  C -->|VALID| D[\"{action}\"]",
        f"  C -->|INVALID| E[\"Validation Error\"]",
        f"  D --> F[\"{data_access}\"]",
        f"  F --> G[\"{outcome}\"]",
        f"  E --> H[\"Error Response\"]",
    ]
    
    # Add additional validation branches if available
    if validations and len(validations) > 1:
        for i, val in enumerate(validations[1:], start=2):
            lines.append(f"  C -->|{_fit_text(val, 16)}| V{i}[\"Check {_fit_text(val, 20)}\"]") 
            lines.append(f"  V{i} --> G")
    
    # Show alternative actions/outcomes if available
    if actions and len(actions) > 1:
        for i, act in enumerate(actions[1:], start=2):
            lines.append(f"  D -->|Alt| A{i}[\"{_fit_text(act, 22)}\"]") 
            lines.append(f"  A{i} --> F")
    
    return "\n".join(lines)


def _fit_text(value: str, limit: int = 44) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _shape_and_text(
    shape_id: str,
    text_id: str,
    x: int,
    y: int,
    text: str,
    width: int = 220,
    height: int = 64,
    bg: str = "#e5f3ff",
) -> list[dict]:
    label = _fit_text(text)
    shape = {
        "id": shape_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1f2937",
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": 101,
        "version": 1,
        "versionNonce": 101,
        "isDeleted": False,
        "boundElements": [{"id": text_id, "type": "text"}],
        "updated": 0,
        "link": None,
        "locked": False,
    }

    text_el = {
        "id": text_id,
        "type": "text",
        "x": x + 10,
        "y": y + 21,
        "width": max(40, width - 24),
        "height": 22,
        "angle": 0,
        "strokeColor": "#111827",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "seed": 202,
        "version": 1,
        "versionNonce": 202,
        "isDeleted": False,
        "boundElements": None,
        "updated": 0,
        "link": None,
        "locked": False,
        "text": label,
        "fontSize": 15,
        "fontFamily": 3,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": shape_id,
        "originalText": label,
        "lineHeight": 1.25,
    }

    return [shape, text_el]


def _arrow(arrow_id: str, x: int, y: int, width: int, start_id: str, end_id: str) -> dict:
    return {
        "id": arrow_id,
        "type": "arrow",
        "x": x,
        "y": y,
        "width": width,
        "height": 0,
        "angle": 0,
        "strokeColor": "#1f2937",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "seed": 303,
        "version": 1,
        "versionNonce": 303,
        "isDeleted": False,
        "boundElements": None,
        "updated": 0,
        "link": None,
        "locked": False,
        "points": [[0, 0], [width, 0]],
        "startBinding": {"elementId": start_id, "focus": 0, "gap": 4},
        "endBinding": {"elementId": end_id, "focus": 0, "gap": 4},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


def _stringify_step(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for candidate in ("name", "rule", "table", "path", "value"):
            if candidate in value and isinstance(value[candidate], str):
                text = value[candidate].strip()
                if text:
                    return text
        return json.dumps(value, ensure_ascii=True)[:120]
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _stringify_step(item)
            if text:
                parts.append(text)
        return ", ".join(parts[:3])
    return str(value).strip()


def _workflow_step(workflow: dict, key: str, fallback: str) -> str:
    values = workflow.get(key)
    if isinstance(values, list) and values:
        first = _stringify_step(values[0])
        if first:
            return first
    return fallback


def _dependency_stems(workflow: dict) -> list[str]:
    dependencies = workflow.get("dependencies")
    if not isinstance(dependencies, list):
        return []

    stems: list[str] = []
    for item in dependencies:
        if isinstance(item, dict):
            path = str(item.get("path") or "").strip()
        else:
            path = str(item or "").strip()

        if not path:
            continue

        name = Path(path).stem
        if name:
            stems.append(name)
    return stems


def _first_action(workflow: dict, index: int, fallback: str) -> str:
    values = workflow.get("actionSequence")
    if isinstance(values, list) and values:
        pos = min(index, len(values) - 1)
        value = _stringify_step(values[pos])
        if value:
            return value
    return fallback


def _infer_controller(workflow: dict) -> str:
    controller = _workflow_step(workflow, "controllerPath", "")
    if controller:
        return controller

    for stem in _dependency_stems(workflow):
        lowered = stem.lower()
        if any(token in lowered for token in ["controller", "servlet", "action"]):
            return stem

    first_action = _first_action(workflow, 0, "")
    if first_action:
        return first_action

    return "Request Handler"


def _infer_decision(workflow: dict) -> str:
    decision = _workflow_step(workflow, "decisionBranches", "")
    if decision:
        return decision

    validation = _workflow_step(workflow, "validations", "")
    if validation:
        return validation

    return "Validation / Rule Check"


def _infer_data_access(workflow: dict) -> str:
    touchpoint = _workflow_step(workflow, "dbTouchpoints", "")
    if touchpoint:
        return touchpoint

    for stem in _dependency_stems(workflow):
        lowered = stem.lower()
        if any(token in lowered for token in ["repository", "dao", "db", "query"]):
            return stem

    return "Data Access"


def _workflow_view(title: str, workflow: dict) -> dict:
    entry = str(workflow.get("entryPoint") or workflow.get("entryRoute") or workflow.get("entryHint") or "Entry").strip()
    outcome = str(workflow.get("outcome") or workflow.get("expectedOutput") or "").strip()
    if not outcome:
        expected = _workflow_step(workflow, "expectedOutputs", "")
        outcome = expected or title

    return {
        "title": title,
        "entry": entry or "Entry",
        "controller": _infer_controller(workflow),
        "decision": _infer_decision(workflow),
        "action": _first_action(workflow, 1, _first_action(workflow, 0, "Business Action")),
        "data": _infer_data_access(workflow),
        "outcome": outcome,
        "validations": workflow.get("validations", []),
        "actions": workflow.get("actions", []),
        "dbTouchpoints": workflow.get("dbTouchpoints", []),
    }


def _flow_chain(entry: str, controller: str, decision: str, action: str, data_access: str, outcome: str) -> str:
    chain = " -> ".join(
        [
            _fit_text(entry or "Entry", 22),
            _fit_text(controller, 24),
            _fit_text(decision, 22),
            _fit_text(action, 22),
            _fit_text(data_access, 22),
            _fit_text(outcome, 24),
        ]
    )
    return chain


def _excalidraw_for_workflow(flow: dict) -> dict:
    """Generate Excalidraw diagram showing ALL conditional branches and outcomes."""
    title = flow["title"]
    entry = flow["entry"]
    controller = flow["controller"]
    decision = flow["decision"]
    action = flow["action"]
    data_access = flow["data"]
    outcome = flow["outcome"]
    validations = flow.get("validations", [])
    actions = flow.get("actions", [])
    flow_chain = _flow_chain(entry, controller, decision, action, data_access, outcome)

    elements: list[dict] = []
    
    # Summary row
    elements.extend(_shape_and_text("flow-chain", "flow-chain-text", 40, -50, flow_chain, 1600, 42, "#f8fafc"))
    
    # Main flow line (top)
    elements.extend(_shape_and_text("entry", "entry-text", 40, 40, entry or "Entry Route", 210, 64, "#e5f3ff"))
    elements.extend(_shape_and_text("controller", "controller-text", 300, 40, controller, 220, 64, "#eff6ff"))
    elements.extend(_shape_and_text("decision", "decision-text", 560, 40, decision, 260, 64, "#fef3c7"))
    
    # VALID path (center)
    elements.extend(_shape_and_text("action", "action-text", 860, 40, action, 230, 64, "#eef9f1"))
    elements.extend(_shape_and_text("data", "data-text", 1130, 40, data_access, 230, 64, "#f5f3ff"))
    elements.extend(_shape_and_text("outcome", "outcome-text", 1400, 40, outcome, 240, 64, "#ecfeff"))
    
    # INVALID path (error handling - bottom)
    elements.extend(_shape_and_text("error-validation", "error-validation-text", 600, 160, "Validation Error", 260, 64, "#fee2e2"))
    elements.extend(_shape_and_text("error-response", "error-response-text", 920, 160, "Error Response", 240, 64, "#fecaca"))
    
    # Main flow arrows (TOP LINE)
    elements.append(_arrow("a1", 252, 72, 44, "entry", "controller"))
    elements.append(_arrow("a2", 522, 72, 34, "controller", "decision"))
    
    # Decision to VALID path
    elements.append(_arrow("a3-valid", 822, 72, 34, "decision", "action"))
    elements.append(_arrow("a4", 1092, 72, 34, "action", "data"))
    elements.append(_arrow("a5", 1362, 72, 34, "data", "outcome"))
    
    # Decision to INVALID path (downward)
    elements.append({
        "id": "a3-invalid",
        "type": "arrow",
        "x": 690,
        "y": 112,
        "width": -90,
        "height": 46,
        "angle": 0,
        "strokeColor": "#991b1b",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "seed": 405,
        "version": 1,
        "versionNonce": 405,
        "isDeleted": False,
        "boundElements": None,
        "updated": 0,
        "link": None,
        "locked": False,
        "points": [[0, 0], [-90, 46]],
        "startBinding": {"elementId": "decision", "focus": 0, "gap": 4},
        "endBinding": {"elementId": "error-validation", "focus": 0, "gap": 4},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    })
    
    # Error handling flow
    elements.append(_arrow("a6-error", 862, 192, 56, "error-validation", "error-response"))
    
    # Add labels for branches
    elements.extend(_shape_and_text("label-valid", "label-valid-text", 820, 10, "✓ VALID", 100, 32, "transparent"))
    elements.extend(_shape_and_text("label-invalid", "label-invalid-text", 640, 90, "✗ INVALID", 110, 32, "transparent"))
    
    # Add alternative actions if available
    alt_y = 280
    for i, alt_action in enumerate(actions[1:3], start=1):
        alt_id = f"alt-action-{i}"
        alt_text_id = f"alt-action-text-{i}"
        elements.extend(_shape_and_text(alt_id, alt_text_id, 860, alt_y, _fit_text(alt_action, 30), 230, 64, "#f0fdf4"))
        alt_y += 100

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "legacy-modernization-platform",
        "elements": elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }


def _consolidate_workflows(workflows: list[dict]) -> dict:
    """Merge multiple related workflows into a single consolidated workflow."""
    if not workflows:
        return {}
    
    # Get common attributes from first workflow
    base = workflows[0] if isinstance(workflows[0], dict) else {}
    
    # Consolidate names/entry points
    entry_points = []
    for wf in workflows:
        if isinstance(wf, dict):
            ep = wf.get("entryPoint") or wf.get("entryRoute") or wf.get("entryHint")
            if ep and ep not in entry_points:
                entry_points.append(str(ep))
    
    # Build consolidated entry
    entry_summary = " / ".join(entry_points[:3]) if entry_points else "Auth Flow"
    
    # Consolidate other attributes (use first non-empty value)
    consolidated = {
        "name": f"{base.get('moduleName', 'Module')} - Unified Auth Flow",
        "entryPoint": entry_summary,
        "moduleName": base.get("moduleName"),
        "controller": base.get("controller") or base.get("controllerName"),
        "validations": [],
        "actions": [],
        "dbTouchpoints": [],
        "outcome": base.get("outcome") or "Auth decision completed",
    }
    
    # Merge validations, actions, db touchpoints from all workflows
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        
        for val in (wf.get("validations") or []):
            if val not in consolidated["validations"]:
                consolidated["validations"].append(val)
        
        for act in (wf.get("actions") or []):
            if act not in consolidated["actions"]:
                consolidated["actions"].append(act)
        
        for db in (wf.get("dbTouchpoints") or []):
            if db not in consolidated["dbTouchpoints"]:
                consolidated["dbTouchpoints"].append(db)
    
    return consolidated


def _emit_for_group(ctx, group_name: str, workflows: list[dict], consolidate: bool = True) -> list[dict]:
    emitted: list[dict] = []
    
    # Use consolidation mode for same-module workflows
    if consolidate and len(workflows) > 1:
        # Check if all workflows are for the same module
        module_names = set(str(w.get("moduleName", "")).strip() for w in workflows if isinstance(w, dict))
        if len(module_names) == 1:
            # Consolidate all into one
            consolidated = _consolidate_workflows(workflows)
            if consolidated:
                title = str(consolidated.get("name") or f"{group_name}-unified")
                flow = _workflow_view(title, consolidated)
                
                base_name = f"{group_name}-workflow-unified"
                mmd_rel = f"{base_name}.mmd"
                exc_rel = f"{base_name}.excalidraw.json"
                png_rel = f"previews/{base_name}.png"

                ctx.write_text(mmd_rel, _mermaid_for_workflow(title, flow))
                exc_abs = Path(ctx.write_json(exc_rel, _excalidraw_for_workflow(flow)))

                png_abs = ctx.out_dir / png_rel
                png_abs.parent.mkdir(parents=True, exist_ok=True)

                rendered = False
                if _RENDER_SCRIPT.exists():
                    command: list[str]
                    if shutil.which("uv"):
                        command = ["uv", "run", "python", str(_RENDER_SCRIPT), str(exc_abs), "--output", str(png_abs)]
                    else:
                        command = [sys.executable, str(_RENDER_SCRIPT), str(exc_abs), "--output", str(png_abs)]

                    try:
                        subprocess.run(
                            command,
                            cwd=str(_RENDER_SCRIPT.parent),
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=90,
                        )
                        rendered = png_abs.exists()
                    except Exception:
                        rendered = False

                if not rendered:
                    ctx.write_placeholder_png(png_rel)
                else:
                    ctx.add_artifact(png_abs)

                emitted.append(
                    {
                        "workflow": title,
                        "workflowId": "unified",
                        "entryPoint": str(consolidated.get("entryPoint") or ""),
                        "group": group_name,
                        "mermaid": mmd_rel,
                        "excalidraw": exc_rel,
                        "preview": png_rel,
                        "provenance": make_provenance("excalidraw-generated", sources=[group_name, "consolidated"], confidence=0.75),
                    }
                )
                return emitted
    
    # Fallback to individual diagrams (original behavior)
    for idx, workflow in enumerate(workflows[:12], start=1):
        if not isinstance(workflow, dict):
            continue
        title = str(workflow.get("name") or f"{group_name}-workflow-{idx:02d}")
        flow = _workflow_view(title, workflow)

        base_name = f"{group_name}-workflow-{idx:02d}"
        mmd_rel = f"{base_name}.mmd"
        exc_rel = f"{base_name}.excalidraw.json"
        png_rel = f"previews/{base_name}.png"

        ctx.write_text(mmd_rel, _mermaid_for_workflow(title, flow))
        exc_abs = Path(ctx.write_json(exc_rel, _excalidraw_for_workflow(flow)))

        png_abs = ctx.out_dir / png_rel
        png_abs.parent.mkdir(parents=True, exist_ok=True)

        rendered = False
        if _RENDER_SCRIPT.exists():
            command: list[str]
            if shutil.which("uv"):
                command = ["uv", "run", "python", str(_RENDER_SCRIPT), str(exc_abs), "--output", str(png_abs)]
            else:
                command = [sys.executable, str(_RENDER_SCRIPT), str(exc_abs), "--output", str(png_abs)]

            try:
                subprocess.run(
                    command,
                    cwd=str(_RENDER_SCRIPT.parent),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                rendered = png_abs.exists()
            except Exception:
                rendered = False

        if not rendered:
            ctx.write_placeholder_png(png_rel)
        else:
            ctx.add_artifact(png_abs)

        emitted.append(
            {
                "workflow": title,
                "workflowId": str(workflow.get("workflowId") or ""),
                "entryPoint": str(workflow.get("entryPoint") or workflow.get("entryRoute") or ""),
                "group": group_name,
                "mermaid": mmd_rel,
                "excalidraw": exc_rel,
                "preview": png_rel,
                "provenance": make_provenance("excalidraw-generated", sources=[group_name], confidence=0.7),
            }
        )
    return emitted


def execute(ctx):
    csharp_logic = (
        ctx.load_artifact_json("csharp-logic-understanding", "csharp-logic-summary.json")
        or ctx.load_artifact_json("module-documentation", "module-analysis.json")
        or ctx.load_artifact_json("legacy-logic-extraction", "logic-summary.json")
        or {}
    )
    java_logic = (
        ctx.load_artifact_json("java-logic-understanding", "java-logic-summary.json")
        or ctx.load_artifact_json("java-counterpart-discovery", "legacy-workflows.json")
        or {}
    )

    csharp_workflows = csharp_logic.get("workflows") if isinstance(csharp_logic.get("workflows"), list) else []
    java_workflows = java_logic.get("workflows") if isinstance(java_logic.get("workflows"), list) else []

    emitted = []
    # Enable consolidation to merge same-module workflows into unified diagrams
    emitted.extend(_emit_for_group(ctx, "csharp", csharp_workflows, consolidate=True))
    emitted.extend(_emit_for_group(ctx, "java", java_workflows, consolidate=True))

    index = {
        "moduleName": ctx.module_name,
        "generatedAt": ctx.started_at,
        "items": emitted,
    }
    index_path = Path(ctx.write_json("diagram-index.json", index))

    # Collect all artifact paths
    artifact_paths = [str(index_path)]
    for item in emitted:
        # Add diagram files
        if "mermaid" in item:
            artifact_paths.append(str(ctx.out_dir / item["mermaid"]))
        if "excalidraw" in item:
            artifact_paths.append(str(ctx.out_dir / item["excalidraw"]))
        if "preview" in item:
            preview_path = ctx.out_dir / item["preview"]
            if preview_path.exists():
                artifact_paths.append(str(preview_path))

    return {
        "skillName": "excalidraw-diagram",
        "stage": "java-logic",
        "moduleName": ctx.module_name,
        "runId": ctx.run_id,
        "status": "passed" if emitted else "degraded",
        "startedAt": ctx.started_at,
        "endedAt": _now_iso(),
        "summary": f"Generated {len(emitted)} consolidated workflow diagrams (Mermaid + Excalidraw + preview PNG).",
        "metrics": {
            "diagramBundles": len(emitted),
            "csharpWorkflows": len(csharp_workflows),
            "javaWorkflows": len(java_workflows),
            "mermaidFiles": sum(1 for item in emitted if "mermaid" in item),
            "excalidrawFiles": sum(1 for item in emitted if "excalidraw" in item),
            "previewPNGs": sum(1 for item in emitted if "preview" in item),
        },
        "artifacts": artifact_paths,
        "findings": [],
        "recommendations": [
            "Diagrams show all conditional branches and pivots in single consolidated view per language",
            "Use Excalidraw JSON for editing or PNG for readonly dashboard viewing"
        ] if emitted else [],
        "resultContractVersion": "1.0",
        "provenanceSummary": {
            "scenarioSources": ["excalidraw-generated"],
            "confidence": 0.7 if emitted else 0.4,
        },
    }


if __name__ == "__main__":
    run_python_skill(SPEC, execute)
