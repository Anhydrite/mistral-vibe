---
name: vibe-shell
description: Shell conventions when running commands in Mistral Vibe. Use before writing a `bash` tool call or a script that shells out. Covers the working directory, quoting the user's shell, combined commands and long-running processes.
metadata:
  display-name: Vibe Shell
  short-description: Shell conventions for tool calls
  default-prompt: Use $vibe-shell to follow Vibe shell conventions.
---

# Vibe Shell

Conventions for any command an agent runs through the `bash` tool.

## Working directory

- Each call runs in a fresh, stateless shell whose working directory is the workspace. Do not prefix a command with `cd <workspace>`: it costs tokens and hides the intent.
- Use `cd` only to leave the workspace for a known path, or `git -C <repo>` to target another repository.
- A `cd` never reaches the next call, so a command that depends on it must repeat it or use absolute paths.

## Quoting

- The shell is the user's, usually zsh. `echo ===` fails with `== not found`, because zsh reads `=word` as a command path; quoting the separator (`echo "==="`) is always safe.
- Quote every argument that could expand: paths with spaces, `*`, `?`, `$`, `!`.
- In zsh, an unmatched glob is an error rather than a literal, so quote the pattern or use `noglob`.

## One call, one purpose

- Prefer one call that checks several things (`pwd; ls; git status --short`) over several calls: they run in sequence and each costs a turn.
- `2>/dev/null` on an exploratory command hides the reason a path is wrong. Keep stderr unless the noise is known and irrelevant.

## Processes

- Never stop a process by name or pattern (`pkill`, `killall`, `pgrep | xargs kill`): those names match every Vibe session, IDE integration and test run on the machine.
- Start long-running work with the process tools where they exist, and stop only what you started, by the PID or process group recorded at start.

## Files

- Use `read_file`, `write_file`, `edit` and `glob` rather than `cat`, `sed`, `tee` or `find`: they bound their output and respect the workspace.
- Reach for the shell when the operation is a pipeline, a build, a test run or a git command.
