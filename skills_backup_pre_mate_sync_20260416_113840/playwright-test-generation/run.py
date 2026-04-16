#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result
from ai_provider import call_ai, AIProviderError

SKILL_NAME = "playwright-test-generation"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


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
            ctx, SKILL_NAME, "failed", "Input validation failed.",
            artifacts=[],
            findings=[{"type": "InputValidation", "message": "; ".join(errors)}]
        )
        print(result_path)
        return 1

    strict_ai = bool(payload.get("strictAIGeneration", True))

    csharp_logic = read_json(Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "csharp-logic-understanding" / "csharp-logic-summary.json")
    legacy_logic = read_json(Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "legacy-logic-understanding" / "legacy-logic-summary.json")
    parity = read_json(Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "parity-analysis" / "parity-diff.json")
    diagrams = read_json(Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "diagram-generation" / "diagram-index.json")

    prompt = {
        "task": (
            "Generate Python Playwright tests as JSON array. "
            "Each item must contain: name, workflow, purpose, requiresInput, inputsNeeded, code. "
            "Use pytest-compatible Python Playwright tests. "
            "Begin from startUrl and follow the workflow. "
            "Do not generate generic smoke-only tests."
        ),
        "module": ctx.module_name,
        "baseUrl": payload.get("baseUrl", ""),
        "startUrl": payload.get("startUrl", ""),
        "workflowNames": payload.get("workflowNames", []),
        "csharpLogic": csharp_logic,
        "legacyLogic": legacy_logic,
        "parity": parity,
        "diagrams": diagrams
    }

    try:
        ai_resp = call_ai(prompt, strict=strict_ai)
        tests = json.loads(str(ai_resp.get("text") or "").strip())
        if not isinstance(tests, list):
            raise ValueError("AI did not return a JSON array")
    except (AIProviderError, ValueError, json.JSONDecodeError) as ex:
        result_path = write_result(
            ctx, SKILL_NAME, "failed",
            f"Playwright generation failed: {ex}",
            artifacts=[],
            findings=[{"type": "PlaywrightGenerationError", "message": str(ex)}]
        )
        print(result_path)
        return 1

    input_requirements = []
    files = []

    for test in tests:
        if test.get("requiresInput"):
            input_requirements.append({
                "testName": test.get("name", ""),
                "workflow": test.get("workflow", ""),
                "purpose": test.get("purpose", ""),
                "inputsNeeded": test.get("inputsNeeded", [])
            })

        name = str(test.get("name", "")).strip()
        if not name:
            continue

        file_path = ctx.out_dir / f"{name}.py"
        file_path.write_text(str(test.get("code", "")), encoding="utf-8")
        files.append(str(file_path.as_posix()))

    index_path = write_json(ctx.out_dir / "playwright-tests.generated.json", {
        "moduleName": ctx.module_name,
        "category": "playwright",
        "tests": tests
    })

    inputs_path = write_json(ctx.out_dir / "playwright-input-requirements.json", {
        "moduleName": ctx.module_name,
        "items": input_requirements
    })

    result_path = write_result(
        ctx, SKILL_NAME, "passed",
        f"Generated {len(tests)} Python Playwright test(s).",
        artifacts=[index_path, inputs_path, *files],
        metrics={"generatedCount": len(tests), "requiresInputCount": len(input_requirements)}
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())