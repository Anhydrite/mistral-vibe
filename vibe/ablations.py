"""Ablation switches used by the benchmark runs.

``VIBE_ABLATE`` holds a comma-separated list of module names. Unset, every
switch is off and the CLI behaves exactly as configured. The switches exist so
a benchmark can turn one module off at a time without editing files between
runs, and they are read each time they are asked rather than cached, so a
long-lived process still sees the environment it was started with.
"""

from __future__ import annotations

import os


def ablated(name: str) -> bool:
    """Whether ``name`` is listed in ``VIBE_ABLATE``."""
    raw = os.environ.get("VIBE_ABLATE", "")
    return name in {part.strip() for part in raw.split(",") if part.strip()}
