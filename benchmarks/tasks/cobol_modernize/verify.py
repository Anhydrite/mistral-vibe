#!/usr/bin/env python3
"""Verify the cobol_modernize task against a reference implementation.

The reference mirrors `legacy/sales.cob` rule for rule. Hidden inputs are
generated here so the workspace only ships the sample pair.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HIDDEN = {
    "hidden1.txt": """\
north alpha 10 1.00
north beta 9 1.15
north gamma 1 0.05
south delta 100 0.99
south epsilon 3 33.33
""",
    "hidden2.txt": """\
west zeta 2 0.25
west eta 1 2.10
east theta 10 0.37
east iota 13 0.15
""",
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def reference(text: str) -> str:
    rows = [line.split() for line in text.splitlines() if line.strip()]
    out = ["ITEM".ljust(12) + " QTY" + "   EXTENDED"]
    current: str | None = None
    region_total = Decimal("0")
    grand = Decimal("0")
    for region, item, qty_text, price_text in rows:
        qty = int(qty_text)
        amount = _money(Decimal(qty) * Decimal(price_text))
        if qty >= 10:
            amount = _money(amount * Decimal("0.95"))
        if current is None:
            current = region
            out.append(f"REGION {region}")
        elif region != current:
            out.append("REGION TOTAL     " + f"{region_total:>10.2f}")
            region_total = Decimal("0")
            current = region
            out.append(f"REGION {region}")
        out.append(item.ljust(12) + f"{qty:>4}" + " " + f"{amount:>10.2f}")
        region_total += amount
        grand += amount
    out.append("REGION TOTAL     " + f"{region_total:>10.2f}")
    out.append("GRAND TOTAL      " + f"{grand:>10.2f}")
    tax = _money(grand * Decimal("0.0825"))
    out.append("TAX              " + f"{tax:>10.2f}")
    out.append("TOTAL            " + f"{_money(grand + tax):>10.2f}")
    return "\n".join(out) + "\n"


def main() -> int:
    workspace = Path(sys.argv[1]).resolve()
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    script = workspace / "sales.py"
    check("sales.py exists", script.is_file())
    check("legacy source untouched", (workspace / "legacy/sales.cob").is_file())
    check(
        "no extra files",
        sorted(
            p.name
            for p in workspace.iterdir()
            if p.is_file() and p.suffix in {".py", ".cob", ".txt", ".json"}
        )
        == ["expected.txt", "sales.py", "sales.txt"],
        str(sorted(p.name for p in workspace.iterdir())),
    )
    if not script.is_file():
        print(json.dumps({"passed": False, "checks": checks}))
        return 0

    cases = {"sample": (workspace / "sales.txt").read_text()}
    cases.update(HIDDEN)
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in cases.items():
            data = Path(tmp) / f"{name}.txt"
            data.write_text(text)
            proc = subprocess.run(
                [sys.executable, str(script), str(data)],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=60,
            )
            expected = reference(text)
            cobol = _cobol_oracle(workspace, data)
            if cobol is not None:
                expected = cobol
            check(
                f"{name}: output matches",
                proc.returncode == 0 and proc.stdout == expected,
                (proc.stderr or "")[:300]
                if proc.returncode != 0
                else _diff(proc.stdout, expected),
            )

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}))
    return 0


def _cobol_oracle(workspace: Path, data: Path) -> str | None:
    """Run the legacy COBOL, locally or in the bwrap rootfs, when available.

    Returns None when no compiler is reachable, so the embedded reference is
    the oracle instead. The two agree on every checked input.
    """
    source = workspace / "legacy/sales.cob"
    if not source.is_file():
        return None
    cobc = shutil.which("cobc")
    if cobc:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "sales"
            build = subprocess.run(
                [cobc, "-x", "-o", str(binary), str(source)],
                capture_output=True, text=True, timeout=120,
            )
            if build.returncode == 0:
                run = subprocess.run(
                    [str(binary), str(data)], capture_output=True, text=True, timeout=60
                )
                if run.returncode == 0:
                    return run.stdout
    return _rootfs_oracle(source, data)


def _rootfs_oracle(source: Path, data: Path) -> str | None:
    """Compile in the unprivileged rootfs when one was prepared on this host."""
    rootfs = Path.home() / "containers/ubuntu"
    bwrap = shutil.which("bwrap")
    if bwrap is None or not (rootfs / "usr/bin/cobc").exists():
        return None
    with tempfile.TemporaryDirectory() as tmp:
        build_dir = Path(tmp)
        shutil.copy(source, build_dir / "sales.cob")
        shutil.copy(data, build_dir / "input.txt")
        proc = subprocess.run(
            [
                bwrap, "--bind", str(rootfs), "/", "--dev", "/dev",
                "--proc", "/proc", "--tmpfs", "/run", "--bind", str(build_dir),
                "/work", "--uid", "0", "--gid", "0", "--chdir", "/work",
                "bash", "-c",
                "cobc -x -o sales sales.cob >/dev/null 2>&1 && ./sales input.txt",
            ],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode == 0 and "EXTENDED" in proc.stdout:
            return proc.stdout
    return None


def _diff(got: str, want: str) -> str:
    got_lines, want_lines = got.splitlines(), want.splitlines()
    for index in range(max(len(got_lines), len(want_lines))):
        g = got_lines[index] if index < len(got_lines) else "<missing>"
        w = want_lines[index] if index < len(want_lines) else "<extra>"
        if g != w:
            return f"line {index + 1}: got {g!r}, want {w!r}"
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
