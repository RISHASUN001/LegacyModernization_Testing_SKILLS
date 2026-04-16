#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json:
        return json.loads(args.json)

    if args.json_file:
        return json.loads(Path(args.json_file).read_text(encoding="utf-8"))

    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("No JSON payload provided. Use --json, --json-file, or stdin.")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Save raw run-input JSON to MATE/run-inputs and invoke orchestrator with MATE-only roots."
    )
    parser.add_argument("--json", help="Raw JSON payload string.")
    parser.add_argument("--json-file", help="Path to file containing JSON payload.")
    parser.add_argument("--rerun-mode", default="changed", choices=["changed", "full"])
    args = parser.parse_args()

    mate_root = Path(__file__).resolve().parents[2]
    run_inputs_root = mate_root / "run-inputs"
    skills_root = mate_root / "skills"
    artifacts_root = mate_root / "artifacts"
    orchestrator_script = Path(__file__).resolve().parent / "run.py"

    payload = read_payload(args)
    module_name = str(payload.get("moduleName") or "module").strip() or "module"
    if not payload.get("runId"):
        payload["runId"] = f"run-{now_stamp()}"

    run_inputs_root.mkdir(parents=True, exist_ok=True)
    safe_module = "".join(ch for ch in module_name if ch.isalnum() or ch in ("-", "_")) or "module"
    input_path = run_inputs_root / f"run-input.{safe_module}.{now_stamp()}.json"
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        str(orchestrator_script),
        "--input",
        str(input_path),
        "--skills-root",
        str(skills_root),
        "--artifacts-root",
        str(artifacts_root),
        "--rerun-mode",
        args.rerun_mode,
    ]

    proc = subprocess.run(cmd, cwd=str(mate_root), capture_output=True, text=True)

    out = {
        "savedInput": str(input_path),
        "invocation": {
            "skillsRoot": str(skills_root),
            "artifactsRoot": str(artifacts_root),
            "rerunMode": args.rerun_mode,
            "exitCode": proc.returncode,
        },
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    print(json.dumps(out, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
