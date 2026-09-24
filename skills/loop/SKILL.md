---
name: "loop"
description: "Direct an existing repository development loop from any owner-directed coding surface, with one ledger, isolated workers and recorded checks."
---

# loop

The repository sees exactly what its policy asks for: one branch cut from the resolved base, one pull
request to that base with the template body and the check output, merged under the owner’s explicit authorization. The
batching is local. Workers branch from a local day branch and never push; the owner reviews each
worker branch on this machine and folds it into the day branch; at close the day branch is
pushed once under an ordinary `type/slug` name. No bot, no comment on any issue, no `loop/*` ref
on the remote, no CI until the one pull request opens, delivery according to that repository’s workflow.

Use the installed `dev-loop` command (the platform loop script), or `ai-work loop` for supported control verbs. State: `LOOP_STATE_DIR/<owner__repo>/` (layout in the header of `dev-loop`). `steer` is
the gate: first word `go` or `pause`, and a missing file means pause. `day-branch` names the
open day (`loop/<date>`); its worktree is `.claude/worktrees/day-<date>` in the checkout.

## Setup, once per machine

`~/.config/dev-platform/repos.conf`: one line per repository, `owner/repo <tab> checkout path
<tab> owner|bot [base-branch]`. `owner` means the two GitHub writes the loop makes (`pr create` at close,
`issue close` at finish) use the human's own `gh` login and require the owner’s authorization and the script’s supported execution surface;
`bot` means the machine user's token from 1Password. `~/.config/dev-platform/brief.conf` sets
`LOOP_STATE_DIR` (default `~/.local/state/dev-platform/loop`).

## Issue conventions

Every implementable issue body carries two plain lines: `Scope: <comma-separated path prefixes>`
and `Depends on: #N, #M` or `Depends on: none`. Only issues labeled `sprint-ready` with both lines
are selected. Scopes must be pairwise prefix-disjoint within one dispatch; dependencies must be
closed, or already folded into the open day branch. `Scope:` lists code and test prefixes. The
documentation lines the repository requires in the same change (specification text, status
markers, lock digests) are always in scope and are not checked for overlap. An issue that an open
pull request cites, that is folded, or that holds a local worker branch is not reselected.

## Procedure

Owner-directed OpenRig, OpenClaw, Claude Code and Codex sessions may run `start`, `plan`, `go`, `pause`, `collect` and local `close` against the same ledger. The script still requires an owner terminal for `fold`, `finish`, `tidy --apply` and ready publication. A personal repository permits authorized draft `close --push`; professional publication remains owner-controlled. Do not schedule `tick` or launch a competing dispatcher. `pause` stops future dispatch, not running workers.

1. `dev-loop status <owner/repo>`: steer, open day, running workers, worker branches and
   their state, folded issues, the day pull request.
2. `dev-loop start <owner/repo>`: fetch, cut `loop/<date>` from the resolved remote base into the
   day worktree, record it, write the PLAN. Refuses while a day is open.
3. `dev-loop go <owner/repo> [only N ...|skip N ...]`: write `steer: go`, plan, dispatch a
   worker per selected issue not yet dispatched, up to configured `LOOP_CAP` (default 3). Model per issue by tier:
   `spec`, `decision`, `privacy`, `security` labels use the judgment tier; `documentation` the
   mechanical tier; everything else the implementation tier. `dev-loop tick` does the same
   from a schedule and prints `NO_REPLY` unless steer says go and a day is open;
   `dev-loop pause` prevents further dispatch; already-running workers continue.
4. A worker: one issue, one worktree, one `type/slug-N` branch from the day branch. It commits,
   runs `hooks/check-once.sh` (which records the passing tree), writes `.worker-pr.md` with the
   four template sections and `Closes #N`, and stops. It never pushes, opens a pull request or
   comments. A worker that finds the fix outside its scope, or the issue already resolved, writes
   `.worker-blocked.md` and stops; the owner widens the scope or closes the issue.
5. `dev-loop collect <owner/repo>`: the CYCLE report from the ledger and the worktrees,
   with its one metrics line.
6. `dev-loop fold <owner/repo> N ...`: the owner, after reading the worker's diff
   (`git diff loop/<date>..<branch>`) and `.worker-pr.md` in its worktree, merges the branch into
   the day branch with a merge commit, keeps the body under the ledger, removes the branch and
   worktree. Refuses a running worker, a blocked one, a dirty worktree, a branch that commits a
   `.worker-*` file, and a conflict (aborted; resolve by hand in the day worktree, then rerun).
7. `dev-loop close <owner/repo> [--as type/slug] [--title ...]`: run the check once on the
   day head (fails closed), write `pr.md` from the folded bodies with one `Closes #N` per issue,
   print the exact push and create commands. `--push` pushes the day branch as `type/slug`
   (default `fix/<date>`) and opens the one draft pull request to the recorded base (`--ready` opens it
   ready). After more folds, `close --push` again pushes the update to the same pull request and rewrites its
   title and body from `pr.md`.
8. The owner reviews and merges it on GitHub, the repository’s required checks and delivery workflow.
   `dev-loop finish <owner/repo> <pr>` then closes each folded issue with `Merged in #pr.`
   (closing keywords never fire on a non-default branch), deletes the pushed branch, removes the
   day worktree and branch, and writes `steer: pause`.
9. `dev-loop tidy <owner/repo>` weekly, read-only: remote branches merged into the recorded base,
   clean worktrees with no live session whose branch is merged or a pointer to `main`, local
   branches in the same state. `--apply` bundles every ref to the ledger first, then deletes.

Writes to GitHub go through `scripts/ghx <owner/repo> <gh args>`, which picks the identity from
`repos.conf` and refuses merge, ready and review on every repository.

## Worker seats

With `LOOP_SEAT_RIG=<running rig>`, dispatch cuts the worktree and brief as usual and gives the
issue an interactive seat in that rig's `workers` pod instead of a headless worker
(`dev-workspace add-worker`; `LOOP_SEAT_RUNTIME` claude or codex; a Codex seat takes
`LOOP_SEAT_ACCOUNT` or its native home). Seats are not counted by `status`, `collect` or the cap. The owner removes the seat
(`dev-workspace remove-worker`) before fold; fold refuses while its block remains and refuses a
branch that commits OpenRig's managed context. See `docs/rig-working-branches.md`.

## Base and execution limits

The fourth `repos.conf` column pins the base. Without it, a personal repository uses its remote default branch; a professional repository uses `develop`. An open day retains its recorded `day-base`. Read status before starting from another surface. `LOOP_WORKER_MAX_TURNS`, `LOOP_WORKER_MAX_SECONDS` and `LOOP_WORKER_TOKEN_CEILING` declare worker bounds; token ceiling is a prompt budget, not a provider spending cap. Quota failure stops the lane rather than silently switching accounts.
