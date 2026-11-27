# Startup measurements

Question: does bypassing the Rust TUI for headless runs cut startup?

`vibe-headless` opens the app server in-process and drives one turn through
the public session API (`LocalHarness`), instead of exec'ing `vibe-rs`.

Same machine, same model (`mistral/deepseek-v4-1-flash-1017`), same prompt
(`OK`, one turn), fresh `VIBE_HOME` per run, wall clock:

| run | `vibe` (Rust TUI) | `vibe-headless` |
|---|---|---|
| 1 | 6.55 s | 6.44 s |
| 2 | 6.58 s | 14.06 s (network outlier) |
| 3 | 6.49 s | 6.24 s |

The TUI is not the cost. Breakdown of a headless run on a real task:

- turn (model + tools): 7.45 s
- graceful close: 0.23 s
- process start, imports and bootstrap: ~2.5 s

The dominant fixed cost is the Python app-server import and bootstrap:
`import vibe.app_server.local` alone takes ~1.25 s; the rest is config layers,
model catalog and session setup.

Conclusion: keep `vibe-headless` as an automation entry point (no TUI, clean
JSON export), but it does not win the wall-clock race against maki. A real
startup win needs a long-lived server process that subsequent runs attach to,
not another client.
