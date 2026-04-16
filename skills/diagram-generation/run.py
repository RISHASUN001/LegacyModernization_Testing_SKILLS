#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
import sys

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from ai_provider import AIProvider, StrictAIUnavailableError
from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result


SKILL_NAME = "diagram-generation"

PALETTE = {
    "start": {"fill": "#fed7aa", "stroke": "#c2410c"},
    "process": {"fill": "#3b82f6", "stroke": "#1e3a5f"},
    "decision": {"fill": "#fef3c7", "stroke": "#b45309"},
    "success": {"fill": "#a7f3d0", "stroke": "#047857"},
    "error": {"fill": "#fecaca", "stroke": "#b91c1c"},
    "note": {"fill": "#dbeafe", "stroke": "#1e40af"},
}
TEXT_DARK = "#374151"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_logic_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_json(path)
    payload = data.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def find_renderer(skill_dir: Path) -> Path:
    candidate = skill_dir / "references" / "render_excalidraw.py"
    if not candidate.exists():
        raise FileNotFoundError(
            f"Expected Excalidraw renderer at: {candidate.as_posix()}"
        )
    return candidate.resolve()


def ai_diagram_bundle(provider: AIProvider, module_name: str, source_name: str, logic_payload: dict[str, Any]) -> dict[str, Any]:
    schema_hint = {
        "title": "string",
        "mermaid": "string",
        "graph": {
            "nodes": [
                {
                    "id": "string",
                    "text": "string",
                    "type": "start|process|decision|success|error|note"
                }
            ],
            "edges": [
                {
                    "from": "string",
                    "to": "string",
                    "label": "string"
                }
            ]
        }
    }

    prompt = (
        f"Generate one unified business-flow diagram bundle for the {source_name} workflow logic. "
        "Return Mermaid flowchart TD text plus a simple graph model. "
        "Include major branches, validations, db-related steps, success paths, and error/failure paths in the same flow. "
        "Do not output file lists. Diagram actual business behavior only."
    )

    ai = provider.generate_json(prompt, context={"moduleName": module_name, "source": source_name, "logic": logic_payload}, schema_hint=schema_hint)
    content = ai.content if isinstance(ai.content, dict) else {}
    content["provider"] = ai.provider
    return content


def compute_levels(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    children = defaultdict(list)
    indegree = defaultdict(int)
    ids = [n["id"] for n in nodes]

    for node_id in ids:
        indegree[node_id] = 0

    for edge in edges:
        src = edge["from"]
        dst = edge["to"]
        children[src].append(dst)
        indegree[dst] += 1

    roots = [node_id for node_id in ids if indegree[node_id] == 0] or ids[:1]
    level: dict[str, int] = {r: 0 for r in roots}
    queue = deque(roots)

    while queue:
        current = queue.popleft()
        for nxt in children[current]:
            candidate = level[current] + 1
            if nxt not in level or candidate > level[nxt]:
                level[nxt] = candidate
                queue.append(nxt)

    for node_id in ids:
        level.setdefault(node_id, 0)

    return level


def node_size(node_type: str) -> tuple[int, int]:
    if node_type == "decision":
        return (170, 110)
    if node_type in ("start", "success", "error"):
        return (180, 90)
    if node_type == "note":
        return (220, 90)
    return (220, 90)


def build_excalidraw(title: str, graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    levels = compute_levels(nodes, edges)
    level_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        level_groups[levels[node["id"]]].append(node)

    positions: dict[str, tuple[int, int, int, int]] = {}
    x_gap = 320
    y_gap = 170
    base_x = 120
    base_y = 140

    for level in sorted(level_groups.keys()):
        row = level_groups[level]
        for idx, node in enumerate(row):
            width, height = node_size(node.get("type", "process"))
            x = base_x + idx * x_gap
            y = base_y + level * y_gap
            positions[node["id"]] = (x, y, width, height)

    elements: list[dict[str, Any]] = []

    elements.append({
        "id": "title-text",
        "type": "text",
        "x": 60,
        "y": 40,
        "width": 1200,
        "height": 30,
        "text": title,
        "originalText": title,
        "fontSize": 24,
        "fontFamily": 3,
        "textAlign": "left",
        "verticalAlign": "top",
        "strokeColor": "#1e40af",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "groupIds": [],
        "seed": 1000,
        "version": 1,
        "versionNonce": 1001,
        "isDeleted": False,
        "boundElements": None,
        "updated": 0,
        "link": None,
        "locked": False,
        "containerId": None,
        "lineHeight": 1.25
    })

    for i, node in enumerate(nodes, start=1):
        node_id = node["id"]
        node_type = node.get("type", "process")
        x, y, width, height = positions[node_id]
        colors = PALETTE.get(node_type, PALETTE["process"])
        shape_id = f"node-{node_id}"
        text_id = f"text-{node_id}"

        shape_type = "rectangle"
        if node_type in ("start", "success", "error"):
            shape_type = "ellipse"
        elif node_type == "decision":
            shape_type = "diamond"

        elements.append({
            "id": shape_id,
            "type": shape_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "strokeColor": colors["stroke"],
            "backgroundColor": colors["fill"],
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "groupIds": [],
            "seed": 2000 + i,
            "version": 1,
            "versionNonce": 3000 + i,
            "isDeleted": False,
            "boundElements": None,
            "updated": 0,
            "link": None,
            "locked": False,
            **({"roundness": {"type": 3}} if shape_type == "rectangle" else {})
        })

        elements.append({
            "id": text_id,
            "type": "text",
            "x": x + 20,
            "y": y + (height / 2) - 18,
            "width": width - 40,
            "height": 36,
            "text": node.get("text", node_id),
            "originalText": node.get("text", node_id),
            "fontSize": 16,
            "fontFamily": 3,
            "textAlign": "center",
            "verticalAlign": "middle",
            "strokeColor": TEXT_DARK,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "groupIds": [],
            "seed": 4000 + i,
            "version": 1,
            "versionNonce": 5000 + i,
            "isDeleted": False,
            "boundElements": None,
            "updated": 0,
            "link": None,
            "locked": False,
            "containerId": shape_id,
            "lineHeight": 1.25
        })

    for i, edge in enumerate(edges, start=1):
        src = edge["from"]
        dst = edge["to"]
        if src not in positions or dst not in positions:
            continue

        sx, sy, sw, sh = positions[src]
        dx, dy, dw, dh = positions[dst]

        start_x = sx + sw / 2
        start_y = sy + sh
        end_x = dx + dw / 2
        end_y = dy

        points = [
            [0, 0],
            [0, max(40, (end_y - start_y) / 2)],
            [end_x - start_x, end_y - start_y]
        ]

        elements.append({
            "id": f"arrow-{i}",
            "type": "arrow",
            "x": start_x,
            "y": start_y,
            "width": end_x - start_x,
            "height": end_y - start_y,
            "strokeColor": "#1e3a5f",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "groupIds": [],
            "seed": 6000 + i,
            "version": 1,
            "versionNonce": 7000 + i,
            "isDeleted": False,
            "boundElements": None,
            "updated": 0,
            "link": None,
            "locked": False,
            "points": points,
            "startArrowhead": None,
            "endArrowhead": "arrow"
        })

        label = (edge.get("label") or "").strip()
        if label:
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2 - 20
            elements.append({
                "id": f"arrow-label-{i}",
                "type": "text",
                "x": mid_x - 60,
                "y": mid_y,
                "width": 120,
                "height": 20,
                "text": label,
                "originalText": label,
                "fontSize": 14,
                "fontFamily": 3,
                "textAlign": "center",
                "verticalAlign": "top",
                "strokeColor": "#64748b",
                "backgroundColor": "transparent",
                "fillStyle": "solid",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 0,
                "opacity": 100,
                "angle": 0,
                "groupIds": [],
                "seed": 8000 + i,
                "version": 1,
                "versionNonce": 9000 + i,
                "isDeleted": False,
                "boundElements": None,
                "updated": 0,
                "link": None,
                "locked": False,
                "containerId": None,
                "lineHeight": 1.25
            })

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "mate-diagram-generation",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {}
    }


def render_png(renderer: Path, excalidraw_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["python3", str(renderer), str(excalidraw_path), "--output", str(output_path)],
        check=True,
        capture_output=True,
        text=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=SKILL_NAME)
    parser.add_argument("--input", required=True)
    parser.add_argument("--artifacts-root", required=True)
    args = parser.parse_args()

    payload = normalize_payload(load_payload(args.input))
    errors = validate_payload(payload)
    ctx = make_context(payload, args.artifacts_root, SKILL_NAME)

    if errors:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Input validation failed for diagram generation.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}],
        )
        print(result_path)
        return 1

    strict = bool(payload.get("strictAIGeneration", True))
    provider = AIProvider(strict_mode=strict)

    artifacts_root = Path(args.artifacts_root)
    csharp_logic = load_logic_payload(artifacts_root / ctx.module_name / ctx.run_id / "csharp-logic-understanding" / "csharp-logic-summary.json")
    legacy_logic = load_logic_payload(artifacts_root / ctx.module_name / ctx.run_id / "legacy-logic-understanding" / "legacy-logic-summary.json")

    try:
        csharp_bundle = ai_diagram_bundle(provider, ctx.module_name, "csharp", csharp_logic)
        legacy_bundle = ai_diagram_bundle(provider, ctx.module_name, "legacy", legacy_logic)
    except StrictAIUnavailableError as ex:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            str(ex),
            artifacts=[],
            findings=[{"type": "StrictAIUnavailable", "message": str(ex)}],
        )
        print(result_path)
        return 1

    csharp_mmd_path = ctx.out_dir / "csharp-workflow.mmd"
    legacy_mmd_path = ctx.out_dir / "legacy-workflow.mmd"
    csharp_mmd_path.write_text(csharp_bundle.get("mermaid", ""), encoding="utf-8")
    legacy_mmd_path.write_text(legacy_bundle.get("mermaid", ""), encoding="utf-8")

    csharp_exc_data = build_excalidraw(f"{ctx.module_name} - C# Workflow", csharp_bundle.get("graph", {}))
    legacy_exc_data = build_excalidraw(f"{ctx.module_name} - Legacy Workflow", legacy_bundle.get("graph", {}))

    csharp_exc_path = Path(write_json(ctx.out_dir / "csharp-workflow.excalidraw.json", csharp_exc_data))
    legacy_exc_path = Path(write_json(ctx.out_dir / "legacy-workflow.excalidraw.json", legacy_exc_data))

    preview_dir = ctx.out_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    csharp_png = preview_dir / "csharp-workflow.png"
    legacy_png = preview_dir / "legacy-workflow.png"

    renderer = find_renderer(Path(__file__).resolve().parent)
    if not renderer:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Excalidraw renderer not found. Add the renderer assets or mount the excalidraw skill references.",
            artifacts=[csharp_mmd_path.as_posix(), legacy_mmd_path.as_posix(), csharp_exc_path.as_posix(), legacy_exc_path.as_posix()],
            findings=[{"type": "MissingRenderer", "message": "render_excalidraw.py not found"}],
        )
        print(result_path)
        return 1

    try:
        render_png(renderer, csharp_exc_path, csharp_png)
        render_png(renderer, legacy_exc_path, legacy_png)
    except subprocess.CalledProcessError as ex:
        result_path = write_result(
            ctx,
            SKILL_NAME,
            "failed",
            "Diagram render failed.",
            artifacts=[csharp_mmd_path.as_posix(), legacy_mmd_path.as_posix(), csharp_exc_path.as_posix(), legacy_exc_path.as_posix()],
            findings=[{
                "type": "RenderFailure",
                "message": ex.stderr or ex.stdout or str(ex)
            }],
        )
        print(result_path)
        return 1

    index_path = write_json(
        ctx.out_dir / "diagram-index.json",
        {
            "moduleName": ctx.module_name,
            "items": [
                {
                    "workflow": "C# Unified",
                    "group": "csharp",
                    "mermaid": "csharp-workflow.mmd",
                    "excalidraw": "csharp-workflow.excalidraw.json",
                    "preview": "previews/csharp-workflow.png",
                    "provider": csharp_bundle.get("provider", "")
                },
                {
                    "workflow": "Legacy Unified",
                    "group": "legacy",
                    "mermaid": "legacy-workflow.mmd",
                    "excalidraw": "legacy-workflow.excalidraw.json",
                    "preview": "previews/legacy-workflow.png",
                    "provider": legacy_bundle.get("provider", "")
                }
            ]
        }
    )

    artifacts = [
        csharp_mmd_path.as_posix(),
        legacy_mmd_path.as_posix(),
        csharp_exc_path.as_posix(),
        legacy_exc_path.as_posix(),
        csharp_png.as_posix(),
        legacy_png.as_posix(),
        index_path,
    ]

    result_path = write_result(
        ctx,
        SKILL_NAME,
        "passed",
        "Generated Mermaid + Excalidraw + PNG workflow diagrams for C# and legacy business flows.",
        artifacts=artifacts,
        metrics={"diagramBundles": 2},
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())