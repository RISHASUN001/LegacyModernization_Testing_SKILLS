#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full modernization pipeline via orchestrator")
    parser.add_argument("--input", required=True, help="Path to module-run-input JSON")
    parser.add_argument("--workdir", default=".", help="Project root/workdir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.workdir).resolve()
    orchestrator = root / "skills" / "legacy-modernization-orchestrator" / "run.py"
    if not orchestrator.exists():
        raise SystemExit(f"Orchestrator script not found: {orchestrator}")

    command = ["python3", orchestrator.as_posix(), "--input", args.input]
    if args.verbose:
        command.append("--verbose")

    completed = subprocess.run(command, cwd=root.as_posix())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
