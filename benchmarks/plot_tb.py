#!/usr/bin/env python3
"""Draw charts over Terminal-Bench runs.

Reads every <root>/*/*/result.json (the layout vibe_bench/tb_bench/run_tb.py
writes) and renders dependency-free SVG charts into --out, plus an index.html
and a rapport.md that show them next to a summary table. With --png, each SVG
is also converted through rsvg-convert when that binary is installed.

The runs themselves live outside this repository, in the vibe_bench scratch
workspace, so point --root (first positional) at it. Run from the repository
root:

    python3 benchmarks/plot_tb.py
    python3 benchmarks/plot_tb.py ../vibe_bench/tb_bench/results --png
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess

# Harness order, and the colour each one gets in every chart.
COLORS = {
    "maki": "#d1495b",
    "vibe": "#2f6db5",
    "vibe@low": "#7fa8d4",
    "vibe@no-check": "#59a14f",
    "vibe@off": "#9a9a9a",
}
FALLBACK_COLORS = ["#b07aa1", "#edc948", "#76b7b2", "#ff9da7", "#bab0ac"]

# Where run_tb.py leaves its results, relative to this repository. The bench
# runs live in the vibe_bench scratch workspace, outside the checkout.
CANDIDATE_ROOTS = [
    Path("results"),
    Path("../vibe_bench/tb_bench/results"),
    Path("../../Documents/beta_labo/vibe_bench/tb_bench/results"),
]

W = 980
INK = "#243040"
GRID = "#dfe4ea"
MUTED = "#6b7785"


# --------------------------------------------------------------------------- data


def sec(record: dict) -> float:
    """Harness-reported work time, falling back to the wall clock."""
    return float(record.get("work_sec") or record.get("elapsed_sec") or 0.0)


def uncached_tokens(record: dict) -> float:
    return float(record.get("input_tokens") or 0) + float(record.get("output_tokens") or 0)


def load(roots: list[Path]) -> dict[str, list[dict]]:
    """Run name -> records.

    A root is either a run directory, holding one <cell>/result.json per
    attempt, or a parent of run directories.
    """
    runs: dict[str, list[dict]] = {}
    for root in dict.fromkeys(roots):
        for pattern in ("*/result.json", "*/*/result.json"):
            for path in sorted(root.glob(pattern)):
                depth = len(path.relative_to(root).parts)
                name = root.name if depth == 2 else path.relative_to(root).parts[0]
                runs.setdefault(name, []).append(json.loads(path.read_text()))
    return dict(sorted(runs.items()))


def by_harness(records: list[dict]) -> dict[str, list[dict]]:
    table: dict[str, list[dict]] = {}
    for record in records:
        table.setdefault(record["harness"], []).append(record)
    return table


def med(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def harnesses_of(runs: dict[str, list[dict]]) -> list[str]:
    seen = {r["harness"] for records in runs.values() for r in records}
    ordered = [h for h in COLORS if h in seen]
    return ordered + sorted(seen - set(ordered))


def color(harness: str, ordered: list[str]) -> str:
    if harness in COLORS:
        return COLORS[harness]
    return FALLBACK_COLORS[ordered.index(harness) % len(FALLBACK_COLORS)]


def label(run: str) -> str:
    """20261125T134436Z -> 25/11 13:44"""
    try:
        return f"{run[6:8]}/{run[4:6]} {run[9:11]}:{run[11:13]}"
    except IndexError:
        return run


# --------------------------------------------------------------------------- svg bits


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def doc(width: int, height: int, title: str, subtitle: str, body: list[str]) -> str:
    head = [
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        txt(24, 34, title, size=17, fill=INK, weight="bold"),
    ]
    if subtitle:
        head.append(txt(24, 54, subtitle, size=11.5, fill=MUTED))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">\n'
        + "\n".join(head + body)
        + "\n</svg>\n"
    )


def txt(x, y, text, size=12, fill=INK, anchor="start", weight=None, rotate=None) -> str:
    extra = ""
    if weight:
        extra += f' font-weight="{weight}"'
    if rotate is not None:
        extra += f' transform="rotate({rotate} {x:.1f} {y:.1f})"'
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}"{extra}>{esc(text)}</text>'
    )


def rect(x, y, w, h, fill, title=None, rx=0, opacity=1.0) -> str:
    tooltip = f"<title>{esc(title)}</title>" if title else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" '
        f'rx="{rx}" fill="{fill}" opacity="{opacity}">{tooltip}</rect>'
    )


def line(x1, y1, x2, y2, stroke=GRID, width=1, dash=None, opacity=1.0) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"{d}/>'
    )


def circle(cx, cy, r, fill, stroke="#ffffff") -> str:
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1"/>'
    )


def polyline(points, stroke, width=2) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linejoin="round"/>'
    )


def nice_max(value: float) -> float:
    """Round up to the next round step so ticks stay readable."""
    if value <= 0:
        return 1.0
    magnitude = 10 ** (len(str(int(value))) - 1)
    for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


def grid_x(body, x0, x1, y, ticks=5) -> None:
    """Vertical guides only, for charts whose x axis is time or categories."""
    for i in range(ticks + 1):
        x = x0 + (x1 - x0) * i / ticks
        body.append(line(x, y[0], x, y[1], GRID))


def axis_x(body, x0, x1, y, top_value, ticks=5, fmt="{:,.0f}") -> None:
    """Vertical guides plus numeric labels, for horizontal bar charts."""
    for i in range(ticks + 1):
        x = x0 + (x1 - x0) * i / ticks
        body.append(line(x, y[0], x, y[1], GRID))
        body.append(txt(x, y[1] + 15, fmt.format(top_value * i / ticks), size=10,
                        fill=MUTED, anchor="middle"))


def legend(body, ordered, x, y, max_width=None) -> None:
    """One row of swatches, wrapped when the harness list grows long."""
    limit = x + (max_width if max_width is not None else W - 40)
    cursor, row = x, 0
    for harness in ordered:
        width = 20 + 7.2 * len(harness)
        if cursor + width > limit:
            cursor, row = x, row + 17
        body.append(rect(cursor, y - 8 + row, 10, 10, color(harness, ordered), rx=2))
        body.append(txt(cursor + 15, y + 1 + row, harness, size=11, fill=INK))
        cursor += width


# --------------------------------------------------------------------------- charts


def chart_pass_rate(runs, ordered, titles=None) -> str:
    """Share of passing cells per run, one line per harness."""
    titles = titles or label
    body: list[str] = []
    top = 100.0
    x0, x1 = 110, W - 40
    y0, y1 = 105, 400
    grid_x(body, x0, x1, (y0, y1), ticks=4)
    for value in (0, 25, 50, 75, 100):
        y = y1 - (y1 - y0) * value / top
        body.append(line(x0, y, x1, y, GRID if value else "#c3cad3"))
        body.append(txt(x0 - 10, y + 4, f"{value}%", size=10, fill=MUTED, anchor="end"))

    names = list(runs)
    step = (x1 - x0) / max(len(names) - 1, 1)
    xs = {name: x0 + step * i for i, name in enumerate(names)}
    for i, name in enumerate(names):
        if len(names) <= 8 or i % 2 == 0:
            body.append(txt(xs[name] + 12, y1 + 34, titles(name), size=9.5, fill=MUTED,
                            anchor="end", rotate=-35))

    for harness in ordered:
        points = []
        for name, records in runs.items():
            cells = [r for r in records if r["harness"] == harness]
            if not cells:
                continue
            share = 100.0 * sum(1 for r in cells if r["passed"]) / len(cells)
            y = y1 - (y1 - y0) * share / top
            points.append((name, xs[name], y, share, len(cells)))
        for (_, ax, ay, _, _), (_, bx, by, _, _) in zip(points, points[1:]):
            body.append(line(ax, ay, bx, by, color(harness, ordered), 1.6, opacity=0.45))
        for name, x, y, share, count in points:
            body.append(
                f'<g>{circle(x, y, 4.5, color(harness, ordered))}'
                f"<title>{esc(harness)} {titles(name)}: {share:.0f}% "
                f"({count} cellules)</title></g>"
            )
    legend(body, ordered, x0, 72)
    body.append(txt((x0 + x1) / 2, 496, "run", size=11, fill=MUTED, anchor="middle"))
    return doc(W, 520, "Taux de réussite par run",
               "Part des cellules passées, par harnais et par run", body)


def chart_per_task(runs, ordered, value_of, title, subtitle, unit, fmt, filename_hint=""):
    """Grouped horizontal bars: one row per task, one bar per harness."""
    stats: dict[str, dict[str, float]] = {}
    for records in runs.values():
        for harness, cells in by_harness(records).items():
            for record in cells:
                stats.setdefault(record["task"], {}).setdefault(harness, [])
                stats[record["task"]][harness].append(value_of(record))
    rows = []
    for task, per_harness in stats.items():
        rows.append((task, {h: med(v) for h, v in per_harness.items()}))
    rows.sort(key=lambda item: max(item[1].values()), reverse=True)

    row_h = 16 + 11 * len(ordered)
    y0 = 95
    height = y0 + row_h * len(rows) + 45
    x0, x1 = 190, W - 90
    top = nice_max(max((max(v.values()) for _, v in rows), default=1))
    body: list[str] = []
    axis_x(body, x0, x1, (y0 - 22, y0 + row_h * len(rows)), top, ticks=5, fmt=fmt)

    for index, (task, per_harness) in enumerate(rows):
        top_y = y0 + index * row_h
        if index % 2 == 1:
            body.append(rect(20, top_y - 6, W - 44, row_h, "#f7f8fa", rx=3))
        body.append(txt(x0 - 12, top_y + (row_h / 2) + 2, task, size=11.5, anchor="end"))
        for slot, harness in enumerate(ordered):
            value = per_harness.get(harness)
            if value is None:
                body.append(txt(x0 + 6, top_y + 12 + slot * 11, "non mesuré", size=9,
                                fill=MUTED))
                continue
            bar_y = top_y + 3 + slot * 11
            width = (x1 - x0) * value / top
            body.append(rect(x0, bar_y, width, 9, color(harness, ordered), rx=2,
                             title=f"{task} {harness}: {value:,.1f} {unit}"))
            body.append(txt(x0 + width + 6, bar_y + 8, f"{value:,.0f}", size=9.5, fill=MUTED))
    legend(body, ordered, x0, 70)
    return doc(W, height, title, subtitle + f" (médiane par tâche, en {unit})", body)


def chart_scatter(runs, ordered) -> str:
    """maki vs the main alternative, one point per task, both axes logarithmic."""
    pairs = ("maki", "vibe")
    stats: dict[str, dict[str, list[float]]] = {}
    for records in runs.values():
        for record in records:
            if record["harness"] in pairs:
                stats.setdefault(record["task"], {}).setdefault(record["harness"], [])
                stats[record["task"]][record["harness"]].append(sec(record))
    points = [
        (task, med(v[pairs[0]]), med(v[pairs[1]]))
        for task, v in stats.items()
        if pairs[0] in v and pairs[1] in v
    ]
    if not points:
        return doc(W, 300, "maki vs vibe", "aucune tâche mesurée sur les deux harnais", [])

    flat = [value for _, a, b in points for value in (a, b) if value > 0]
    lo = 10 ** math.floor(math.log10(min(flat, default=1)))
    hi = 10 ** math.ceil(math.log10(max(flat, default=10)))
    if hi <= lo:
        hi = lo * 10
    ticks = [
        decade * step
        for decade in (10 ** k for k in range(int(math.log10(lo)), int(math.log10(hi)) + 1))
        for step in (1, 2, 5)
        if lo <= decade * step <= hi
    ]

    def place(value: float, low: int, high: int) -> float:
        span = math.log10(hi) - math.log10(lo)
        ratio = math.log10(max(value, lo)) - math.log10(lo)
        return low + (high - low) * ratio / span

    x0, x1 = 95, W - 250
    y0, y1 = 105, 430
    body: list[str] = []
    for value in ticks:
        x, y = place(value, x0, x1), place(value, y1, y0)
        body.append(line(x, y0, x, y1, GRID))
        body.append(txt(x, y1 + 16, f"{value:,.0f}", size=10, fill=MUTED, anchor="middle"))
    for value in ticks:
        y = place(value, y1, y0)
        body.append(line(x0, y, x1, y, GRID))
        body.append(txt(x0 - 10, y + 4, f"{value:,.0f}", size=10, fill=MUTED, anchor="end"))
    body.append(line(x0, y1, x1, y0, "#b9c1cb", 1, dash="5 4"))

    for task, maki_sec, vibe_sec in points:
        x, y = place(maki_sec, x0, x1), place(vibe_sec, y1, y0)
        win = vibe_sec <= maki_sec
        body.append(
            f"<g>{circle(x, y, 6, COLORS['vibe'] if win else COLORS['maki'])}"
            f"<title>{esc(task)}: maki {maki_sec:,.0f}s vs vibe {vibe_sec:,.0f}s</title></g>"
        )
        body.append(txt(x + 10, y + 4, task, size=10.5, fill=INK))
    body.append(txt((x0 + x1) / 2, y1 + 44, "maki (s, échelle log)", size=11, fill=MUTED,
                    anchor="middle"))
    body.append(txt(34, (y0 + y1) / 2, "vibe (s, échelle log)", size=11, fill=MUTED,
                    anchor="middle", rotate=-90))
    body.append(rect(x1 + 30, y0, 12, 12, COLORS["vibe"], rx=2))
    body.append(txt(x1 + 48, y0 + 10, "vibe plus rapide", size=11))
    body.append(rect(x1 + 30, y0 + 24, 12, 12, COLORS["maki"], rx=2))
    body.append(txt(x1 + 48, y0 + 34, "maki plus rapide", size=11))
    body.append(txt(x1 + 30, y0 + 62, "sous la diagonale :", size=10.5, fill=MUTED))
    body.append(txt(x1 + 30, y0 + 77, "vibe termine avant maki", size=10.5, fill=MUTED))
    return doc(W, 510, "Temps par tâche : maki vs vibe",
               "Un point par tâche, médiane du temps de travail", body)


def chart_trend(runs, ordered, titles=None) -> str:
    """Median work time per run, one line per harness."""
    titles = titles or label
    body: list[str] = []
    values = []
    for records in runs.values():
        for harness, cells in by_harness(records).items():
            values.append(med([sec(r) for r in cells]))
    top = nice_max(max(values, default=1))
    x0, x1 = 110, W - 40
    y0, y1 = 105, 400
    grid_x(body, x0, x1, (y0, y1), ticks=5)
    for i in range(6):
        y = y1 - (y1 - y0) * i / 5
        body.append(line(x0, y, x1, y, GRID))
        body.append(txt(x0 - 10, y + 4, f"{top * i / 5:,.0f}", size=10, fill=MUTED, anchor="end"))

    names = list(runs)
    step = (x1 - x0) / max(len(names) - 1, 1)
    xs = {name: x0 + step * i for i, name in enumerate(names)}
    for i, name in enumerate(names):
        if len(names) <= 8 or i % 2 == 0:
            body.append(txt(xs[name] + 12, y1 + 34, titles(name), size=9.5, fill=MUTED,
                            anchor="end", rotate=-35))

    for harness in ordered:
        points = []
        for name, records in runs.items():
            cells = [r for r in records if r["harness"] == harness]
            if not cells:
                continue
            value = med([sec(r) for r in cells])
            points.append((name, xs[name], y1 - (y1 - y0) * value / top, value, len(cells)))
        for (_, ax, ay, _, _), (_, bx, by, _, _) in zip(points, points[1:]):
            body.append(line(ax, ay, bx, by, color(harness, ordered), 1.6, opacity=0.5))
        for name, x, y, value, count in points:
            body.append(
                f"<g>{circle(x, y, 4.5, color(harness, ordered))}"
                f"<title>{esc(harness)} {titles(name)}: {value:,.0f}s "
                f"({count} cellules)</title></g>"
            )
    legend(body, ordered, x0, 72)
    body.append(txt((x0 + x1) / 2, 496, "run", size=11, fill=MUTED, anchor="middle"))
    return doc(W, 520, "Temps médian par run",
               "Médiane du temps de travail des cellules mesurées, par harnais", body)


# --------------------------------------------------------------------------- summary


def summary_rows(runs, ordered) -> list[dict[str, str]]:
    """Per-harness medians, shared by the HTML page and the markdown report."""
    rows = []
    for harness in ordered:
        cells = [r for records in runs.values() for r in records if r["harness"] == harness]
        if not cells:
            continue
        passed = sum(1 for r in cells if r["passed"])
        costs = [float(r.get("cost_usd") or 0) for r in cells]
        rows.append({
            "harnais": harness,
            "cellules": str(len(cells)),
            "reussite": f"{100 * passed / len(cells):.0f}% ({passed}/{len(cells)})",
            "temps": f"{med([sec(r) for r in cells]):,.0f} s",
            "tokens": f"{med([uncached_tokens(r) for r in cells]):,.0f}",
            "cout": f"${med(costs):.3f}" if any(costs) else "non rapporté",
            "tours": f"{med([float(r.get('turns') or 0) for r in cells]):,.0f}",
        })
    return rows


COLUMNS = [
    ("harnais", "harnais"), ("cellules", "cellules"), ("reussite", "réussite"),
    ("temps", "temps médian"), ("tokens", "tokens non cachés"),
    ("cout", "coût médian"), ("tours", "tours médians"),
]


def summary(runs, ordered) -> str:
    head = "".join(f"<th>{esc(title)}</th>" for _, title in COLUMNS)
    rows = []
    for row in summary_rows(runs, ordered):
        cells = "".join(
            f'<td><span class="dot" style="background:{color(row["harnais"], ordered)}">'
            f'</span>{esc(row[key])}</td>' if key == "harnais" else f"<td>{esc(row[key])}</td>"
            for key, _ in COLUMNS
        )
        rows.append(f"<tr>{cells}</tr>")
    return f"<table><tr>{head}</tr>{''.join(rows)}</table>"


INDEX_CSS = """
body{margin:0;padding:32px 40px;background:#f5f6f8;color:#243040;
     font:15px/1.5 Helvetica,Arial,sans-serif}
h1{font-size:22px;margin:0 0 4px} p.sub{color:#6b7785;margin:0 0 26px}
section{background:#fff;border:1px solid #e2e6ec;border-radius:10px;
        padding:18px 20px;margin-bottom:22px}
h2{font-size:15px;margin:0 0 12px}
img{max-width:100%;height:auto;display:block}
table{border-collapse:collapse;font-size:14px}
th,td{padding:7px 12px;text-align:right;border-bottom:1px solid #e8ebf0}
th{color:#6b7785;font-weight:600;text-align:right}
td:first-child,th:first-child{text-align:left}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}
"""


def write_index(out: Path, runs, ordered, charts, titles=None) -> None:
    sections = "".join(
        f'<section><a href="{svg}"><img src="{svg}" alt="{esc(title)}"></a></section>'
        for svg, title, _ in charts
    )
    titles = titles or label
    runs_note = (f"{len(runs)} runs, du {titles(next(iter(runs)))} "
                 f"au {titles(next(reversed(runs)))}")
    page = (
        "<!doctype html><html lang=fr><meta charset=utf-8>"
        "<title>Terminal-Bench : graphiques</title>"
        f"<style>{INDEX_CSS}</style>"
        "<h1>Terminal-Bench : graphiques</h1>"
        f'<p class="sub">{esc(runs_note)}</p>'
        f"<section><h2>Résumé par harnais</h2>{summary(runs, ordered)}</section>"
        f"{sections}"
        "</html>"
    )
    (out / "index.html").write_text(page)


def write_markdown(out: Path, runs, ordered, charts, extension: str, titles=None) -> None:
    """Same content as index.html, as a file to read or paste elsewhere."""
    titles = titles or label
    lines = [
        "# Terminal-Bench : graphiques",
        "",
        f"{len(runs)} runs, du {titles(next(iter(runs)))} "
        f"au {titles(next(reversed(runs)))}.",
        "",
        "Médianes par harnais ; les temps excluent les cellules non mesurées.",
        "",
        "| " + " | ".join(title for _, title in COLUMNS) + " |",
        "|" + "|".join("---" for _ in COLUMNS) + "|",
    ]
    for row in summary_rows(runs, ordered):
        lines.append("| " + " | ".join(row[key] for key, _ in COLUMNS) + " |")
    for svg, title, _ in charts:
        lines += ["", f"## {title}", "", f"![{title}]({Path(svg).stem}.{extension})"]
    lines.append("")
    (out / "rapport.md").write_text("\n".join(lines))


# --------------------------------------------------------------------------- main


def to_png(svg: Path) -> str | None:
    tool = shutil.which("rsvg-convert")
    if not tool:
        return None
    png = svg.with_suffix(".png")
    subprocess.run([tool, "-z", "1.5", str(svg), "-o", str(png)], check=True)
    return png.name


def chart_names() -> list[tuple[str, str]]:
    """File stem and title of every chart, in display order."""
    return [
        ("01-reussite", "Taux de réussite par run"),
        ("02-temps-par-tache", "Temps de travail par tâche"),
        ("03-tokens-par-tache", "Tokens non cachés par tâche"),
        ("04-temps-par-run", "Temps médian par run"),
        ("05-maki-vs-vibe", "maki vs vibe par tâche"),
    ]


def build_charts(runs, ordered, titles=None) -> list[tuple[str, str, str]]:
    """(svg name, title, svg body) for every chart; titles names a run."""
    titles = titles or label
    bodies = {
        "01-reussite": lambda: chart_pass_rate(runs, ordered, titles),
        "02-temps-par-tache": lambda: chart_per_task(
            runs, ordered, sec, "Temps de travail par tâche",
            "Le plus court est le meilleur", "s", "{:,.0f}"),
        "03-tokens-par-tache": lambda: chart_per_task(
            runs, ordered, uncached_tokens, "Tokens non cachés par tâche",
            "Entrée + sortie, hors lectures de cache", "tokens", "{:,.0f}"),
        "04-temps-par-run": lambda: chart_trend(runs, ordered, titles),
        "05-maki-vs-vibe": lambda: chart_scatter(runs, ordered),
    }
    return [(f"{stem}.svg", title, bodies[stem]()) for stem, title in chart_names()]


def write_outputs(runs, ordered, out: Path, png: bool = False, titles=None) -> list[str]:
    """Write every chart plus index.html and rapport.md, and report the file names."""
    out.mkdir(parents=True, exist_ok=True)
    charts = build_charts(runs, ordered, titles)
    for name, _, svg in charts:
        (out / name).write_text(svg)
    converted = [to_png(out / name) for name, _, _ in charts] if png else []
    # The markdown links PNGs only when every chart got one.
    extension = "png" if converted and all(converted) else "svg"
    write_index(out, runs, ordered, charts, titles)
    write_markdown(out, runs, ordered, charts, extension, titles)
    return [f"{name} -> {as_png}" if as_png else name for (name, _, _), as_png in
            zip(charts, converted or [None] * len(charts))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", type=Path, default=None,
                    help=f"run directories (default: first of {CANDIDATE_ROOTS})")
    ap.add_argument("--out", type=Path, default=Path("benchmarks/charts"))
    ap.add_argument("--png", action="store_true", help="also write PNG via rsvg-convert")
    args = ap.parse_args()

    candidates = args.roots or CANDIDATE_ROOTS
    roots = [r for r in candidates if r.is_dir()]
    if not roots:
        print("no run directory found, pass the results path explicitly:", *candidates, sep="\n  ")
        return 1
    runs = load(roots)
    if not runs:
        print("no result.json under", ", ".join(str(r) for r in roots))
        return 1
    written = write_outputs(runs, harnesses_of(runs), args.out, png=args.png)

    print(f"{args.out}/index.html")
    print(f"{args.out}/rapport.md")
    for name in written:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
