---
name: morning-brief
description: Produce the morning brief in the fixed format: pull requests awaiting the owner, open decisions, CI and testing health, the last deploy-log row, new intake since yesterday, the last loop cycle, then today's loop plan. Read-only; delivered to the owner, never posted.
---

# morning-brief

## Setup, once per machine

`~/.config/dev-platform/brief.conf` names the repositories, the CI branch, the deploy-log path,
the testing host and compose project (read over one fixed `ssh` command), the production health
URL, and the note folders scanned for new intake. The scripts read nothing else.

## Procedure

1. `scripts/brief.sh` prints the brief. `--no-vps` skips the host probe.
2. `scripts/morning.sh` prints the brief followed by today's loop plan (`loop/scripts/loop-sense.sh`)
   and writes both under `LOOP_STATE_DIR/<date>/`.
3. Schedule `morning.sh` as a deterministic command on weekday mornings, delivered to the owner.
   It needs no model.

Format is fixed: `BRIEF <date>`, then `prs:`, `decisions:`, `health:`, `deploy log:`,
`intake (24h):`, `loop:`, then `PLAN <date>`.
