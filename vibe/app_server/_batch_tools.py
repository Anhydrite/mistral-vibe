"""Batch tools for the PicoVibe agent.

These run in the app server as provided tools, so they need no harness change.
They cut round-trips and tokens: read several files at once, look at a file
skeleton before reading it, list matches with a glob, and apply several exact
edits to one file atomically.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, Field

MAX_FILE_BYTES = 48_000
MAX_TOTAL_BYTES = 120_000
MAX_INDEX_SYMBOLS = 200
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
}

READ_FILES_TOOL_NAME = "read_files"
INDEX_TOOL_NAME = "index"
GLOB_TOOL_NAME = "glob"
MULTIEDIT_TOOL_NAME = "multiedit"

READ_FILES_DESCRIPTION = """\
Read several files in one call. Use it instead of several `read_file` calls when
the files are independent. Paths are relative to the workspace or absolute
inside it. Each file is truncated to `max_lines` with a marker. Binary files
and unreadable paths are reported per file instead of failing the whole call."""

INDEX_DESCRIPTION = """\
Return a compact skeleton of a source file: imports and the signatures of its
classes, functions and methods, each with its line number. Use it before
`read_file` on a large file to decide which ranges to read. Supports Python,
JavaScript, TypeScript, Go, Rust, Java, C/C++ and Ruby; other files fall back to
a head. Never returns the whole file."""


GLOB_DESCRIPTION = """\
Find files by glob pattern inside the workspace, for example `**/*.py` or
`src/**/*.ts`. Excludes .git, virtualenvs, node_modules, caches and build
directories. Returns paths relative to the workspace, sorted."""

MULTIEDIT_DESCRIPTION = """\
Apply several exact string replacements to one file atomically. Provide the
edits in order; each `old_string` must match exactly once unless `replace_all`
is true. If any edit fails, no change is written. Prefer this over several
`edit` calls on the same file."""


class FileRead(BaseModel):
    path: str
    content: str | None = None
    error: str | None = None
    truncated: Literal[False] | int = False


class ReadFilesArgs(BaseModel):
    paths: list[str] = Field(min_length=1, description="Files to read")
    max_lines: int = Field(
        default=400, ge=1, le=5000, description="Line cap per file"
    )


class ReadFilesResult(BaseModel):
    files: list[FileRead]
    bytes_read: int


class IndexArgs(BaseModel):
    path: str = Field(description="Source file to outline")


class IndexResult(BaseModel):
    path: str
    skeleton: str
    symbols: int


class GlobArgs(BaseModel):
    pattern: str = Field(description="Glob pattern relative to the workspace")
    path: str = Field(default=".", description="Directory to search from")
    max_results: int = Field(default=200, ge=1, le=2000)


class GlobResult(BaseModel):
    matches: list[str]
    truncated: bool


class EditOperation(BaseModel):
    old_string: str
    new_string: str
    replace_all: bool = False


class MultiEditArgs(BaseModel):
    file_path: str = Field(description="File to edit")
    edits: list[EditOperation] = Field(min_length=1)


class MultiEditResult(BaseModel):
    file: str
    edits_applied: int
    bytes_written: int


def _within(cwd: Path, raw: str) -> Path:
    candidate = Path(raw).expanduser()
    path = candidate.resolve() if candidate.is_absolute() else (cwd / candidate).resolve()
    if path != cwd and cwd not in path.parents:
        raise ValueError(f"path escapes the workspace: {raw}")
    return path


def _read_text(path: Path, max_lines: int) -> tuple[str, int | Literal[False]]:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"file is larger than {MAX_FILE_BYTES} bytes: {path.name}")
    data = path.read_bytes()
    if b"\x00" in data[:8192]:
        raise ValueError(f"binary file: {path.name}")
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]), len(lines) - max_lines
    return text, False


def run_read_files(args: ReadFilesArgs, *, cwd: Path) -> ReadFilesResult:
    out: list[FileRead] = []
    total = 0
    for raw in args.paths:
        try:
            path = _within(cwd, raw)
            if not path.is_file():
                raise ValueError(f"no such file: {raw}")
            content, truncated = _read_text(path, args.max_lines)
            total += len(content.encode("utf-8"))
            if total > MAX_TOTAL_BYTES:
                out.append(FileRead(path=raw, error="total read budget exceeded"))
                break
            out.append(FileRead(path=raw, content=content, truncated=truncated))
        except (OSError, ValueError) as exc:
            out.append(FileRead(path=raw, error=str(exc)))
    return ReadFilesResult(files=out, bytes_read=total)


_PY = re.compile(r"^(?P<indent>\s*)(?P<kw>class|def|async\s+def)\s+(?P<name>[A-Za-z_]\w*)")
_GENERIC = re.compile(
    r"^\s*(?:export\s+)?(?:pub\s+)?(?:async\s+)?"
    r"(?:class|interface|struct|enum|trait|impl|fn|func|function|def|type)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)"
)
_IMPORT = re.compile(r"^\s*(?:import|from|use|package|require|#include)\b")


def _skeleton(text: str, suffix: str) -> tuple[str, int]:
    lines = text.splitlines()
    symbols: list[str] = []
    count = 0
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*", "/*")):
            continue
        matched = _PY.match(line) if suffix == ".py" else _GENERIC.match(line)
        is_import = bool(_IMPORT.match(line))
        if matched:
            name = matched.group("name")
            symbols.append(f"{number:>5}  {line.rstrip()}")
            count += 1
        elif is_import and len(symbols) < 40:
            symbols.append(f"{number:>5}  {stripped[:160]}")
        if count >= MAX_INDEX_SYMBOLS:
            symbols.append("... (symbol limit reached)")
            break
    if not symbols:
        head = "\n".join(f"{i:>5}  {line}" for i, line in enumerate(lines[:60], 1))
        return head + ("\n... (head only)" if len(lines) > 60 else ""), 0
    return "\n".join(symbols), count


def run_index(args: IndexArgs, *, cwd: Path) -> IndexResult:
    path = _within(cwd, args.path)
    if not path.is_file():
        raise ValueError(f"no such file: {args.path}")
    text, _ = _read_text(path, 20_000)
    skeleton, count = _skeleton(text, path.suffix.lower())
    return IndexResult(path=args.path, skeleton=skeleton, symbols=count)


def run_glob(args: GlobArgs, *, cwd: Path) -> GlobResult:
    base = _within(cwd, args.path)
    if not base.is_dir():
        raise ValueError(f"not a directory: {args.path}")
    matches: list[str] = []
    truncated = False
    for path in base.glob(args.pattern):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(cwd).parts
        if any(part in _SKIP_DIRS for part in rel_parts):
            continue
        matches.append(str(path.relative_to(cwd)))
        if len(matches) >= args.max_results:
            truncated = True
            break
    matches.sort()
    return GlobResult(matches=matches, truncated=truncated)


def run_multiedit(args: MultiEditArgs, *, cwd: Path) -> MultiEditResult:
    path = _within(cwd, args.file_path)
    if not path.is_file():
        raise ValueError(f"no such file: {args.file_path}")
    text = path.read_text(encoding="utf-8")
    updated = text
    for index, edit in enumerate(args.edits, 1):
        occurrences = updated.count(edit.old_string)
        if occurrences == 0:
            raise ValueError(f"edit {index}: old_string not found")
        if occurrences > 1 and not edit.replace_all:
            raise ValueError(
                f"edit {index}: old_string matches {occurrences} times; "
                "add context or set replace_all"
            )
        updated = updated.replace(
            edit.old_string, edit.new_string, -1 if edit.replace_all else 1
        )
    path.write_text(updated, encoding="utf-8")
    return MultiEditResult(
        file=args.file_path,
        edits_applied=len(args.edits),
        bytes_written=len(updated.encode("utf-8")),
    )
