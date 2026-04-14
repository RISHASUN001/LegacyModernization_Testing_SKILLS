#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PROJECT_ROOT / "skills"
COMMON_ROOT = SKILLS_ROOT / "_common"

BANNED_PATTERNS = [
    re.compile(r"\\bChecklist\\b", re.IGNORECASE),
    re.compile(r"\\bLogin\\b", re.IGNORECASE),
    re.compile(r"saveChecklist", re.IGNORECASE),
    re.compile(r"http://localhost:5000/api/test", re.IGNORECASE),
    re.compile(r"http://127\\.0\\.0\\.1:5000/api/test", re.IGNORECASE),
]

ALLOWLIST_FILES = {
    (SKILLS_ROOT / "legacy-logic-extraction" / "module-profiles.json").resolve(),
    (COMMON_ROOT / "runtime-defaults.json").resolve(),
}


def _load_skill_entrypoints() -> list[Path]:
    files: list[Path] = []
    for config_path in sorted(SKILLS_ROOT.glob("*/config.json")):
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        skill_name = str(config.get("name") or "").strip()
        if not skill_name or skill_name == "legacy-modernization-orchestrator":
            continue

        script_entry = str(config.get("scriptEntry") or "").strip()
        if not script_entry:
            candidate_py = config_path.parent / "run.py"
            candidate_ps1 = config_path.parent / "run.ps1"
            if candidate_py.exists():
                script_entry = "run.py"
            elif candidate_ps1.exists():
                script_entry = "run.ps1"

        candidate = (config_path.parent / script_entry).resolve()
        if candidate.exists() and candidate.suffix.lower() == ".py":
            files.append(candidate)
    return files


def _scan_file(path: Path) -> list[str]:
    if path.resolve() in ALLOWLIST_FILES:
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    hits: list[str] = []
    for idx, line in enumerate(lines, start=1):
        for pattern in BANNED_PATTERNS:
            if pattern.search(line):
                hits.append(f"{path.relative_to(PROJECT_ROOT)}:{idx}: {line.strip()}")
                break
    return hits


def main() -> int:
    targets = _load_skill_entrypoints()
    targets.extend([p.resolve() for p in COMMON_ROOT.glob("*.py")])

    all_hits: list[str] = []
    for target in sorted(set(targets)):
        all_hits.extend(_scan_file(target))

    if all_hits:
        print("Hardcoding audit failed. Found banned literals in runtime skill code:")
        for hit in all_hits:
            print(f"- {hit}")
        print("\nAllowed data/config locations:")
        for item in sorted(ALLOWLIST_FILES):
            print(f"- {item.relative_to(PROJECT_ROOT)}")
        return 1

    print("Hardcoding audit passed: no banned literals found in runtime skill entrypoints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
