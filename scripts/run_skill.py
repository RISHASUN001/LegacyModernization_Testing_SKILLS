#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one skill using config.json script entry")
    parser.add_argument("skill", help="Skill folder name, e.g. module-discovery")
    parser.add_argument("--input", required=True, help="Path to module-run-input JSON")
    parser.add_argument("--artifacts-root", default="artifacts", help="Artifacts root directory")
    parser.add_argument("--workdir", default=".", help="Project root/workdir")
    args = parser.parse_args()

    root = Path(args.workdir).resolve()
    skill_dir = root / "skills" / args.skill
    config_path = skill_dir / "config.json"
    if not config_path.exists():
        raise SystemExit(f"Skill config not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    script_entry = str(config.get("scriptEntry") or "run.py")
    script_path = skill_dir / script_entry
    if not script_path.exists():
        raise SystemExit(f"Skill entry script not found: {script_path}")

    if script_path.suffix.lower() == ".py":
        command = ["python3", script_path.as_posix(), "--input", args.input, "--artifacts-root", args.artifacts_root]
    elif script_path.suffix.lower() == ".ps1":
        if shutil.which("pwsh"):
            command = ["pwsh", "-File", script_path.as_posix(), "-InputPath", args.input, "-ArtifactsRoot", args.artifacts_root]
        elif shutil.which("powershell"):
            command = ["powershell", "-File", script_path.as_posix(), "-InputPath", args.input, "-ArtifactsRoot", args.artifacts_root]
        else:
            raise SystemExit("PowerShell script requested but pwsh/powershell is not available")
    else:
        raise SystemExit(f"Unsupported script type: {script_path}")

    completed = subprocess.run(command, cwd=root.as_posix())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
