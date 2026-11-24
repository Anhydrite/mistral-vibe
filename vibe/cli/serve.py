"""Long-lived app-server daemon.

`vibe -p` pays the Python app-server bootstrap on every invocation. This
process pays it once and then answers one request per connection over a unix
socket: the client sends a JSON line, the daemon runs the turn and replies
with the same JSON shape `vibe-headless` writes.

Every request carries its own working directory and model; requests are
served one at a time, so the process-wide working directory is safe.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from vibe import __version__
from vibe.cli.headless import _bootstrap


async def _run_request(request: dict[str, Any]) -> dict[str, Any]:
    from vibe.app_server._runtime import ClientDescriptor
    from vibe.app_server.events import StatsUpdated, TurnCompleted
    from vibe.app_server.local import (
        LocalHarness,
        LocalHarnessOptions,
        NewSessionIntent,
    )
    from vibe.app_server.protocol import (
        ClientCapabilities,
        ClientInfo,
        CompletionConfig,
        SessionOptions,
    )

    cwd = str(Path(request["cwd"]).resolve())
    os.chdir(cwd)
    model = request.get("model")
    options = LocalHarnessOptions(
        client=ClientDescriptor(
            info=ClientInfo(name="vibe-serve", version=__version__),
            capabilities=ClientCapabilities(),
        ),
        session_options=SessionOptions(
            cwd=cwd,
            completion=(
                CompletionConfig(type="mistral", model=model) if model else None
            ),
            auto_approve=bool(request.get("auto_approve", True)),
            max_turns=request.get("max_turns"),
            headless=True,
            trust_workspace=True,
        ),
        session=NewSessionIntent(),
    )
    started = time.monotonic()
    harness = LocalHarness(options)
    session = await harness.start()
    stats: Any = None
    final_text = ""
    error = None
    try:
        await session.enqueue(request["prompt"])
        async for event in session.events():
            if isinstance(event, StatsUpdated):
                stats = event.params.stats
            elif isinstance(event, TurnCompleted):
                break
        for entry in reversed(session.history):
            if getattr(entry, "type", None) == "message" and entry.role == "assistant":
                final_text = entry.text
                break
    except Exception as exc:  # noqa: BLE001 - reported to the client
        error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            await session.close()
            await harness.close()
        except Exception:  # noqa: BLE001 - a close failure must not kill the daemon
            pass
    elapsed = round(time.monotonic() - started, 3)
    usage = {
        "input_tokens": getattr(stats, "session_prompt_tokens", 0) if stats else 0,
        "output_tokens": (
            getattr(stats, "session_completion_tokens", 0) if stats else 0
        ),
        "cached_input_tokens": (
            getattr(stats, "session_cached_tokens", 0) if stats else 0
        ),
    }
    return {
        "outcome": "error" if error else "finished",
        "error": error,
        "text": final_text,
        "session_id": session.session_id,
        "usage": usage,
        "cost_usd": getattr(stats, "session_cost", 0.0) if stats else 0.0,
        "steps": getattr(stats, "steps", 0) if stats else 0,
        "duration_sec": elapsed,
        "config": {"active_model": model, "cwd": cwd},
    }


async def _handle(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        line = await reader.readline()
        if not line.strip():
            return
        request = json.loads(line)
        response = await _run_request(request)
        writer.write(json.dumps(response, ensure_ascii=False).encode() + b"\n")
        await writer.drain()
    except Exception as exc:  # noqa: BLE001 - one bad request must not stop serving
        payload = {"outcome": "error", "error": f"{type(exc).__name__}: {exc}"}
        try:
            writer.write(json.dumps(payload).encode() + b"\n")
            await writer.drain()
        except Exception:  # noqa: BLE001
            pass
    finally:
        writer.close()


async def _serve(path: Path) -> None:
    _bootstrap()
    if path.exists():
        path.unlink()
    server = await asyncio.start_unix_server(_handle, path=str(path))
    os.chmod(path, 0o600)
    print(json.dumps({"ready": True, "socket": str(path)}), flush=True)
    async with server:
        await server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vibe-serve")
    parser.add_argument(
        "--socket",
        default=os.environ.get("VIBE_SOCKET"),
        help="unix socket path (default: $VIBE_SOCKET)",
    )
    args = parser.parse_args(argv)
    if not args.socket:
        print("vibe-serve: --socket or VIBE_SOCKET is required", file=sys.stderr)
        return 2
    try:
        asyncio.run(_serve(Path(args.socket)))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
