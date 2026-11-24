#!/usr/bin/env python3
"""Verify the overfull_hbox task: clean LaTeX log and preserved wording."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PHRASES = [
    "makes the ingestion pipeline resumable",
    "cuts the median latency of the reconciliation job",
    "Nothing else changed for operators",
    "every node must reach it before the rollout proceeds",
    "The legacy address keeps answering for one release",
    "Callers should switch to the resumable variant",
    "the old entry point drops the retry token",
    "are pruned after ninety days",
    "Stop the workers, run the migration, then restart the workers",
]
LONG_TOKENS = [
    "https://internal.example.com/srv/health/very/long/path/segments/and-more-segments/final-check",
    "/var/lib/anhydrite/pipeline/reconciliation/checkpoints/yearly/2026/november/twenty-fourth/batch-0042",
]


def _which(name: str) -> str | None:
    for folder in (Path.home() / ".local/bin", Path("/usr/bin"), Path("/usr/local/bin")):
        candidate = folder / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which(name)


def _norm_tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, joining a word hyphenated over a break."""
    raw = text.split()
    joined: list[str] = []
    for word in raw:
        if joined and joined[-1].endswith("-") and len(joined[-1]) > 1:
            joined[-1] = joined[-1][:-1] + word
        else:
            joined.append(word)
    return [re.sub(r"[^a-z0-9]", "", word.lower()) for word in joined if word]


def _contains_run(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    if n == 0:
        return True
    for start in range(len(haystack) - n + 1):
        if haystack[start : start + n] == needle:
            return True
    return False


def main() -> int:
    workspace = Path(sys.argv[1]).resolve()
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    tex = workspace / "report.tex"
    pdflatex = _which("pdflatex")
    pdftotext = _which("pdftotext")
    check("report.tex exists", tex.is_file())
    check("pdflatex available", pdflatex is not None)
    if not tex.is_file() or pdflatex is None:
        print(json.dumps({"passed": False, "checks": checks}))
        return 0

    env = os.environ.copy()
    env["PATH"] = str(Path(pdflatex).parent) + os.pathsep + env.get("PATH", "")
    env["TEXMFVAR"] = env.get("TEXMFVAR", str(Path.home() / ".TinyTeX/texmf-var"))
    source = tex.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        for suffix in (".tex",):
            shutil.copy(workspace / f"report{suffix}", run_dir / f"report{suffix}")
        proc = None
        for _ in range(2):
            proc = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "report.tex"],
                cwd=run_dir, env=env, capture_output=True, text=True, timeout=180,
            )
        log = (run_dir / "report.log")
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        pdf = run_dir / "report.pdf"
        check("compiles", proc is not None and proc.returncode == 0, f"exit={proc.returncode if proc else 'n/a'}")
        check("pdf produced", pdf.is_file())
        overfull = log_text.count("Overfull \\hbox")
        underfull = log_text.count("Underfull \\hbox (badness 10000)")
        check("no overfull hbox", overfull == 0, f"count={overfull}")
        check("no underfull hbox", underfull == 0, f"count={underfull}")

        pdf_words: list[str] = []
        if pdftotext is not None and pdf.is_file():
            text = subprocess.run(
                [pdftotext, str(pdf), "-"], capture_output=True, text=True, timeout=120
            ).stdout
            pdf_words = _norm_tokens(text)
        hay = "".join(pdf_words)
        squash = lambda text: re.sub(r"[^a-z0-9]", "", text.lower())  # noqa: E731

        for token in LONG_TOKENS:
            check(f"preserved: {token[:40]}...", squash(token) in hay)
        for phrase in PHRASES:
            check(
                f"wording: {phrase[:40]}",
                _contains_run(pdf_words, _norm_tokens(phrase)),
            )

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
