Run a shell command and return its output.

- Use absolute paths. Each call starts a fresh shell: cwd and environment do not persist.
- Prefer `read_file`, `edit` and `write_file` over `cat`, `sed` and shell redirection.
- `timeout` is in seconds (default 300). No background execution: do not launch long-running or blocking processes.
- A denied command was refused by the user; adjust instead of retrying it verbatim.
- Git: no interactive flags. Use `gh` for GitHub. Commit or push only when asked; create a branch first if on the default branch.
