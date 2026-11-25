Run a shell command and return its output.

- Each call starts in the workspace root: a `cd` lasts only that call, so relative paths resolve from there. Use absolute paths when you leave the workspace.
- Prefer `read_file`, `edit` and `write_file` over `cat`, `sed` and shell redirection.
- `timeout` is in seconds (default 300). No background execution: do not launch long-running or blocking processes.
- A denied command was refused by the user; adjust instead of retrying it verbatim.
- Git: no interactive flags. Use `gh` for GitHub. Commit or push only when asked; create a branch first if on the default branch.
