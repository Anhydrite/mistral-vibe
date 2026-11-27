"""A batch call counts its targets: three files read at once, one edited."""

from __future__ import annotations

from e2e.app_server.events import (
    assistant_msg,
    batch_tool,
    reasoning,
    turn_completed,
    turn_started,
    user_msg,
)
from e2e.app_server.scenario import Timeline, take_snapshot

handshake = {
    "config/read": {"config": {"showThinkingNodes": True}},
    "runtime/read": {"runtime": {"config": {"showThinkingNodes": True}}},
}

_PROMPT = "read the notes and fix the typo"

# The batch calls arrive as generic `tool` effects holding several targets, so
# the folded header counts what they touched, not how often they ran:
# "Read 4 files, edited 1 file, thought".
timeline: Timeline = [
    f"{_PROMPT}\r",
    turn_started(),
    user_msg(_PROMPT),
    reasoning("Reading the notes first, then fixing the typo."),
    batch_tool("read_files", {"paths": ["a.md", "b.md", "c.md"]}, "a.md, b.md and c.md"),
    batch_tool("index", {"path": "d.py"}, "d.py"),
    batch_tool(
        "multiedit",
        {"file_path": "a.md", "edits": [{"old_string": "teh", "new_string": "the"}]},
        "a.md",
    ),
    assistant_msg("Answered."),
    turn_completed(),
    take_snapshot(),
]
