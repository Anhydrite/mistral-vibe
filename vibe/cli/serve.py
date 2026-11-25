"""Long-lived app-server prewarm daemon.

`vibe-headless` pays the Python app-server bootstrap and its lazy imports on
every invocation: about two seconds before any work starts. This process pays
them once, then serves requests by **forking a child per request**, so every
run still gets a fresh process — no session state leaks between runs — while
inheriting the loaded modules from the parent.

Protocol: one JSON line per connection, the same shape `vibe-headless` writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any

from vibe import __version__
from vibe.cli.headless import _bootstrap


def _warm(model: str | None) -> None:
    """Import what a session start would import lazily, then open and close a
    throwaway session so every lazy path and in-memory cache is hot.

    Children forked afterwards still get a fresh session: only module state and
    read-only caches are shared, no session is.
    """
    import tempfile

    import vibe.app_server._runtime  # noqa: F401
    import vibe.app_server._unified_harness_backend_adapter  # noqa: F401
    import vibe.app_server.local  # noqa: F401
    from mistralai_vibe_local_harness.vibe import _completion  # noqa: F401

    _ = __version__
    with tempfile.TemporaryDirectory() as tmp:
        try:
            asyncio.run(
                _run_request(
                    {
                        "cwd": tmp,
                        "prompt": "Reply with a single word.",
                        "model": model,
                        "max_turns": 0,
                    }
                )
            )
        except Exception:  # noqa: BLE001 - warming is best effort
            pass


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
    started = time_monotonic()
    harness = LocalHarness(options)
    session = await harness.start()
    ready = time_monotonic()
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
        except Exception:  # noqa: BLE001
            pass
    closed = time_monotonic()
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
        "duration_sec": round(closed - started, 3),
        "timings": {
            "start_sec": round(ready - started, 3),
            "work_sec": round(closed - ready, 3),
        },
        "config": {"active_model": model, "cwd": cwd},
    }


def time_monotonic() -> float:
    import time

    return time.monotonic()


def _serve_one(conn: socket.socket) -> None:
    chunks = []
    with conn:
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        try:
            request = json.loads(b"".join(chunks).decode())
            response = asyncio.run(_run_request(request))
        except Exception as exc:  # noqa: BLE001
            response = {"outcome": "error", "error": f"{type(exc).__name__}: {exc}"}
        conn.sendall(json.dumps(response, ensure_ascii=False).encode() + b"\n")


def _serve(path: Path, model: str | None = None) -> None:
    _bootstrap()
    _warm(model)
    if path.exists():
        path.unlink()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    os.chmod(path, 0o600)
    listener.listen(8)
    print(json.dumps({"ready": True, "socket": str(path)}), flush=True)
    while True:
        try:
            conn, _ = listener.accept()
        except KeyboardInterrupt:
            return
        pid = os.fork()
        if pid == 0:
            try:
                listener.close()
                _serve_one(conn)
            finally:
                os._exit(0)
        conn.close()
        os.waitpid(pid, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vibe-serve")
    parser.add_argument(
        "--socket",
        default=os.environ.get("VIBE_SOCKET"),
        help="unix socket path (default: $VIBE_SOCKET)",
    )
    parser.add_argument("--warm-model", default="deepseek-v4-1-flash-1017")
    args = parser.parse_args(argv)
    if not args.socket:
        print("vibe-serve: --socket or VIBE_SOCKET is required", file=sys.stderr)
        return 2
    _serve(Path(args.socket), args.warm_model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
