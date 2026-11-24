"""Headless client that runs a turn in-process, without the Rust TUI.

`vibe -p` normally execs the Rust client, which starts an app server over
stdio. This module opens the same app server in-process and drives one turn
through the public session API. It exists for automation, where the terminal
UI is pure startup cost.
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibe-headless", add_help=True)
    parser.add_argument("prompt", nargs="?", help="Prompt to run")
    parser.add_argument("-p", "--prompt-text", dest="prompt_text")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--agent")
    parser.add_argument("--approval-policy")
    parser.add_argument("--auto-approve", "--yolo", action="store_true")
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--max-price", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--time-limit", type=float)
    parser.add_argument("--enabled-tools", action="append")
    parser.add_argument("--disabled-tools", action="append")
    parser.add_argument("--system-prompt-file", type=Path)
    parser.add_argument("--output", choices=("text", "json"), default="text")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--continue", dest="continue_session", action="store_true")
    parser.add_argument("--resume")
    parser.add_argument("--trust", action="store_true")
    return parser


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file is not None:
        return args.prompt_file.read_text(encoding="utf-8")
    if args.prompt_text is not None:
        return args.prompt_text
    if args.prompt is not None:
        return args.prompt
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("vibe-headless: no prompt given")


_BOOTSTRAPPED = False


def _bootstrap() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    from vibe.core.config import load_dotenv_values
    from vibe.core.config.harness_files import init_harness_files_manager
    from vibe.core.paths import bootstrap_vibe_home

    bootstrap_vibe_home()
    load_dotenv_values()
    init_harness_files_manager("user", "project")
    _BOOTSTRAPPED = True


async def _run(args: argparse.Namespace) -> int:
    _bootstrap()
    from vibe.app_server.events import StatsUpdated, TurnCompleted
    from vibe.app_server.local import (
        ContinueSessionIntent,
        LocalHarness,
        LocalHarnessOptions,
        NewSessionIntent,
        ResumeSessionIntent,
    )
    from vibe.app_server._runtime import ClientDescriptor
    from vibe.app_server.protocol import (
        ClientCapabilities,
        ClientInfo,
        CompletionConfig,
        SessionOptions,
    )

    prompt = _read_prompt(args)
    cwd = str(Path.cwd().resolve())
    system_prompt = None
    if args.system_prompt_file is not None:
        system_prompt = args.system_prompt_file.read_text(encoding="utf-8")

    session_options = SessionOptions(
        cwd=cwd,
        completion=(
            CompletionConfig(type="mistral", model=args.model) if args.model else None
        ),
        agent=args.agent,
        approval_policy=args.approval_policy,
        auto_approve=bool(args.auto_approve),
        max_turns=args.max_turns,
        max_price=args.max_price,
        max_session_tokens=args.max_tokens,
        enabled_tools=args.enabled_tools,
        disabled_tools=args.disabled_tools or [],
        headless=True,
        trust_workspace=True,
        system_prompt=system_prompt,
    )
    if args.resume:
        intent = ResumeSessionIntent(session_id=args.resume)
    elif args.continue_session:
        intent = ContinueSessionIntent()
    else:
        intent = NewSessionIntent()
    options = LocalHarnessOptions(
        client=ClientDescriptor(
            info=ClientInfo(name="vibe-headless", version=__version__),
            # No terminal: the session must not wait on UI callbacks.
            capabilities=ClientCapabilities(),
        ),
        session_options=session_options,
        session=intent,
    )

    harness = LocalHarness(options)
    started = time.monotonic()
    session = await harness.start()
    stats: Any = None
    final_text = ""
    try:
        await session.enqueue(prompt)
        async for event in session.events():
            if isinstance(event, StatsUpdated):
                stats = event.params.stats
            elif isinstance(event, TurnCompleted):
                break
        for entry in reversed(session.history):
            if getattr(entry, "type", None) == "message" and entry.role == "assistant":
                final_text = entry.text
                break
        turn_done = time.monotonic()
    finally:
        await session.close()
        await harness.close()
    closed = time.monotonic()
    elapsed = round(closed - started, 3)

    usage = {
        "input_tokens": getattr(stats, "session_prompt_tokens", 0) if stats else 0,
        "output_tokens": (
            getattr(stats, "session_completion_tokens", 0) if stats else 0
        ),
        "cached_input_tokens": (
            getattr(stats, "session_cached_tokens", 0) if stats else 0
        ),
    }
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    export = {
        "outcome": "finished",
        "stop_reason": None,
        "error": None,
        "session_id": session.session_id,
        "usage": usage,
        "cost_usd": getattr(stats, "session_cost", 0.0) if stats else 0.0,
        "steps": getattr(stats, "steps", 0) if stats else 0,
        "duration_sec": elapsed,
        "timings": {
            "turn_sec": round(turn_done - started, 3),
            "close_sec": round(closed - turn_done, 3),
        },
        "config": {"active_model": args.model, "cwd": cwd},
    }

    if args.output == "json":
        print(json.dumps({"result": final_text, **export}, ensure_ascii=False))
    else:
        if final_text:
            print(final_text)
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "export.json").write_text(
            json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.time_limit:
            return asyncio.run(asyncio.wait_for(_run(args), args.time_limit))
        return asyncio.run(_run(args))
    except TimeoutError:
        print("vibe-headless: time limit reached", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
