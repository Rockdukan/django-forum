#!/usr/bin/env python3
"""Remove blank lines immediately after a docstring (module/class/def/async def)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr):
        return False
    v = stmt.value
    return isinstance(v, ast.Constant) and isinstance(v.value, str)


def _blank_indices_after_docstring(body: list[ast.stmt], lines: list[str]) -> list[int]:
    if len(body) < 2:
        return []
    first, second = body[0], body[1]
    if not _is_docstring_stmt(first):
        return []
    start = first.end_lineno  # 0-based index of first physical line after docstring
    last_gap_index = second.lineno - 2  # inclusive
    if start > last_gap_index:
        return []
    out: list[int] = []
    i = start
    while i <= last_gap_index and lines[i].strip() == "":
        out.append(i)
        i += 1
    return out


def _collect_all(tree: ast.AST, lines: list[str]) -> list[int]:
    to_drop: list[int] = []
    if isinstance(tree, ast.Module):
        to_drop.extend(_blank_indices_after_docstring(tree.body, lines))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            to_drop.extend(_blank_indices_after_docstring(node.body, lines))
    return sorted(set(to_drop))


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        print(f"skip (syntax): {path}", file=sys.stderr)
        return False
    lines = text.splitlines(keepends=True)
    physical = text.splitlines()
    drop = _collect_all(tree, physical)
    if not drop:
        return False
    for i in sorted(drop, reverse=True):
        del lines[i]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in {".venv", "venv"}:
            continue
        if "__pycache__" in rel.parts:
            continue
        if process_file(path):
            changed += 1
            print(rel)
    print(f"updated {changed} files", file=sys.stderr)


if __name__ == "__main__":
    main()
