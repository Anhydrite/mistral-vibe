#!/usr/bin/env python3
"""Verify the prove_plus_comm task: a sorry-free Lean proof."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

FORBIDDEN = [
    r"\bsorry\b",
    r"\badmit\b",
    r"\baxiom\b",
    r"\bnative_decide\b",
    r"\bomega\b",
    r"\bdecide\b",
    r"\bNat\.add_comm\b",
    r"\badd_comm\b",
]


def _lean() -> str | None:
    for folder in (Path.home() / ".local/lean/bin", Path("/usr/local/bin")):
        candidate = folder / "lean"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("lean")


def main() -> int:
    workspace = Path(sys.argv[1]).resolve()
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    proof = workspace / "Proof.lean"
    lean = _lean()
    check("Proof.lean exists", proof.is_file())
    check("lean available", lean is not None)
    if not proof.is_file() or lean is None:
        print(json.dumps({"passed": False, "checks": checks}))
        return 0

    source = proof.read_text(encoding="utf-8", errors="replace")
    code = "\n".join(
        line.split("--")[0] for line in source.splitlines()
    )
    check(
        "declares plus_comm",
        re.search(r"theorem\s+plus_comm\s*\(\s*\w+\s+\w+\s*:\s*Nat\s*\)", code)
        is not None,
    )
    check("uses induction", re.search(r"\binduction\b", code) is not None)
    for pattern in FORBIDDEN:
        check(f"forbidden {pattern}", re.search(pattern, code) is None)

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        shutil.copy(proof, run_dir / "Proof.lean")
        proc = subprocess.run(
            [lean, "Proof.lean"],
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PATH": str(Path(lean).parent) + os.pathsep + os.environ.get("PATH", "")},
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        check("compiles", proc.returncode == 0, output.strip()[:400])
        check("no error output", "error" not in output.lower(), output.strip()[:400])

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
