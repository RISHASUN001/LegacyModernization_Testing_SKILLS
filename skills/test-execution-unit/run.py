#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Any

COMMON = Path(__file__).resolve().parents[1] / "_common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from runtime import load_payload, make_context, normalize_payload, validate_payload, write_json, write_result

SKILL_NAME = "test-execution-unit"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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

    generated_index = Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "unit-test-generation" / "unit-tests.generated.json"
    generated = read_json(generated_index)
    tests = generated.get("tests", []) if isinstance(generated, dict) else []

    tests_root = Path("Tests") / "Unit" / ctx.module_name
    ensure_dir(tests_root)

    generated_skill_dir = Path(args.artifacts_root) / ctx.module_name / ctx.run_id / "unit-test-generation"
    copied_files = []

    for test in tests:
        test_name = str(test.get("name", "")).strip()
        if not test_name:
            continue
        src = generated_skill_dir / f"{test_name}.cs"
        dst = tests_root / f"{test_name}.cs"
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            copied_files.append(dst)

    dotnet_test_target = str(payload.get("dotnetTestTarget", "")).strip()
    if not dotnet_test_target:
        log_path = ctx.out_dir / "unit-test.log"
        log_path.write_text("Unit test execution could not start because 'dotnetTestTarget' was not provided.\n", encoding="utf-8")

        manifest_path = write_json(ctx.out_dir / "unit-test-execution-manifest.json", {
            "moduleName": ctx.module_name,
            "category": "unit",
            "status": "failed",
            "reason": "Missing dotnetTestTarget input.",
            "testsDiscovered": len(tests),
            "testsCopied": len(copied_files),
            "items": []
        })

        results_path = write_json(ctx.out_dir / "unit-test-results.json", {
            "moduleName": ctx.module_name,
            "category": "unit",
            "status": "failed",
            "total": len(tests),
            "passed": 0,
            "failed": len(tests),
            "logPath": str(log_path.as_posix())
        })

        result_path = write_result(
            ctx, SKILL_NAME, "failed",
            "Unit test execution could not run because dotnetTestTarget was missing.",
            artifacts=[str(log_path.as_posix()), results_path, manifest_path],
            findings=[{"type": "MissingExecutionInput", "message": "dotnetTestTarget is required"}]
        )
        print(result_path)
        return 1

    cmd = ["dotnet", "test", dotnet_test_target, "--logger", "trx"]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    log_path = ctx.out_dir / "unit-test.log"
    log_path.write_text((proc.stdout or "") + "\n\nSTDERR:\n" + (proc.stderr or ""), encoding="utf-8")

    overall_status = "passed" if proc.returncode == 0 else "failed"
    manifest_items = [{
        "testName": test.get("name", ""),
        "workflow": test.get("workflow", ""),
        "purpose": test.get("purpose", ""),
        "codeFile": str((tests_root / f"{test.get('name', '')}.cs").as_posix()),
        "status": "unknown",
        "logPath": str(log_path.as_posix())
    } for test in tests]

    manifest_path = write_json(ctx.out_dir / "unit-test-execution-manifest.json", {
        "moduleName": ctx.module_name,
        "category": "unit",
        "status": overall_status,
        "testsDiscovered": len(tests),
        "testsCopied": len(copied_files),
        "command": cmd,
        "items": manifest_items
    })

    results_path = write_json(ctx.out_dir / "unit-test-results.json", {
        "moduleName": ctx.module_name,
        "category": "unit",
        "status": overall_status,
        "total": len(tests),
        "passed": len(tests) if proc.returncode == 0 else 0,
        "failed": 0 if proc.returncode == 0 else len(tests),
        "exitCode": proc.returncode,
        "logPath": str(log_path.as_posix())
    })

    result_path = write_result(
        ctx, SKILL_NAME,
        "passed" if proc.returncode == 0 else "failed",
        f"Unit test execution completed with exit code {proc.returncode}.",
        artifacts=[str(log_path.as_posix()), results_path, manifest_path],
        metrics={"total": len(tests), "testsCopied": len(copied_files), "exitCode": proc.returncode},
        findings=[] if proc.returncode == 0 else [
            {"type": "UnitExecutionFailure", "message": "dotnet test returned non-zero exit code.", "evidence": str(log_path.as_posix())}
        ]
    )
    print(result_path)
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())