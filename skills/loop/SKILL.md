---
name: loop
description: Run the continuous development loop on a repository: sense sprint-ready issues read-only, dispatch one headless worker per issue in its own worktree up to the cap, collect draft pull requests, report one metrics line. Label is the go; `steer: pause` is the brake.
---

# loop

State lives on GitHub: one pinned issue titled `Development loop` per repository. Workers push
`type/slug` branches and open draft pull requests under the owner's login. Nothing here merges,
marks ready, pushes to a protected branch or deploys.

## Setup, once per machine

`~/.config/dev-platform/repos.conf`: one line per repository, `owner/repo <tab> checkout path
<tab> owner|bot`. `owner` means writes use the human's own `gh` login and happen only on the
owner's word in that session; `bot` means the machine user's token from 1Password. Optional
`~/.config/dev-platform/brief.conf` sets `LOOP_STATE_DIR` (default `~/.local/state/dev-platform/loop`).

## Issue conventions

Every implementable issue body carries two plain lines: `Scope: <comma-separated path prefixes>`
and `Depends on: #N, #M` or `Depends on: none`. Only issues labeled `sprint-ready` with both lines
are selected. Scopes must be pairwise prefix-disjoint within one tick; dependencies must be closed.

## Procedure

1. `scripts/loop.sh status <owner/repo>`: running workers, open draft pull requests, last steer.
2. `scripts/loop.sh start <owner/repo>`: create and pin the loop issue if missing, post the PLAN.
3. `scripts/loop.sh tick <owner/repo>`: dispatch a worker for each selected issue not yet
   dispatched, up to 3 running. Scheduled every 15 minutes; prints `NO_REPLY` when idle. Model
   per issue by tier: `spec`, `decision`, `privacy`, `security` labels use the judgment tier;
   `documentation` uses the mechanical tier; everything else the implementation tier.
4. `scripts/loop.sh go <owner/repo> [only N | skip N]`: manual cycle, posts the steer first.
5. `scripts/loop.sh collect <owner/repo>`: post the CYCLE comment with its metrics line.
6. Steering, as comments on the loop issue: `steer: go | pause | skip <n> | only <n> | budget <tokens> | note <text>`.
   `steer: pause` stops the ticker until the next `steer: go`.

A worker that finds the issue already resolved, or the fix outside its scope, comments on the
issue and stops without pushing. That is the scope rule working; widen the scope or close the issue.

Writes to GitHub go through `scripts/ghx <owner/repo> <gh args>`, which picks the identity from
`repos.conf` and refuses merge, ready and review on every repository.
