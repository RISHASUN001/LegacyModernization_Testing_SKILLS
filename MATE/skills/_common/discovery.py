from __future__ import annotations

import re
from pathlib import Path
from typing import Any


ROUTE_PATTERNS = [
    re.compile(r'\[Route\("([^"]+)"\)\]'),
    re.compile(r'\[Http(?:Get|Post|Put|Delete|Patch)\("?([^"\)]*)"?\)\]'),
    re.compile(r'@RequestMapping\("([^"]+)"\)'),
    re.compile(r'@(?:Get|Post|Put|Delete|Patch)Mapping\("([^"]+)"\)'),
    re.compile(r'action\s*=\s*"([^"]+)"', re.IGNORECASE),
]

SQL_PATTERN = re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE)\b', re.IGNORECASE)
TABLE_PATTERN = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_]*)\b', re.IGNORECASE)


def gather_files(roots: list[str], patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            continue
        for pattern in patterns:
            files.extend(root_path.rglob(pattern))
    dedup = sorted(set(f.resolve() for f in files if f.is_file()), key=lambda p: p.as_posix())
    return dedup


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def extract_routes(text: str) -> list[str]:
    routes: list[str] = []
    for pattern in ROUTE_PATTERNS:
        routes.extend([m.group(1).strip() for m in pattern.finditer(text) if m.group(1).strip()])
    return sorted(set(routes))


def extract_sql_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if SQL_PATTERN.search(line)]
    return [line[:300] for line in lines[:200]]


def extract_tables(sql_lines: list[str]) -> list[str]:
    tables: list[str] = []
    for line in sql_lines:
        tables.extend([m.group(1) for m in TABLE_PATTERN.finditer(line)])
    return sorted(set(tables))


def tokenize_anchor(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in re.split(r"[^a-zA-Z0-9]+", value.lower()):
            if len(token) >= 3:
                tokens.add(token)
    return tokens


def score_legacy_match(path: Path, text: str, anchor_tokens: set[str]) -> int:
    score = 0
    hay = (path.name.lower() + " " + text.lower())
    for token in anchor_tokens:
        if token in hay:
            score += 1
    return score


def file_basename_list(paths: list[Path]) -> list[str]:
    return sorted(set(p.name for p in paths))


def unique_strings(values: list[str]) -> list[str]:
    return sorted(set(v for v in values if v))


def build_provenance_summary(provider: str, strict: bool) -> dict[str, Any]:
    return {
        "provider": provider,
        "strictAIGeneration": strict,
    }
