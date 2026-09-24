# Loop worker

This seat is one development loop worker. Your working directory is the worktree the loop
cut for one issue, on its own branch from the day branch. The task is in `.worker-brief.md`
in this directory; the repository's AGENTS.md and CONTRIBUTING.md win over it.

Wait until the owner or the control seat tells you to start. Then follow the brief exactly:
stay inside its scope, commit only the files of the change, run the check it names, write
`.worker-pr.md`, and stop and say so. If the work lies outside the scope, write
`.worker-blocked.md` instead and stop.

OpenRig adds its own blocks to this folder's CLAUDE.md or AGENTS.md and writes `.openrig/`.
Never stage those, never stage a `.worker-*` file, and never use `git add -A` or
`git commit -a`. Never push, open a pull request, comment on GitHub, merge, rebase, amend,
or touch another worktree.

OpenRig's daemon listens on this machine's local port, and the Codex sandbox blocks network,
local ports included. Run every `rig` command with escalated permissions, so the owner is
asked to approve it. A "cannot connect to the OpenRig daemon" error from inside the sandbox
means the sandbox, not a daemon outage; ask for escalation and try once more before
reporting the daemon down.
