---
name: loop
description: Run the development loop on a repository with one local day branch and a file ledger: sense sprint-ready issues read-only, dispatch one headless worker per issue in its own worktree up to the cap, fold reviewed worker branches into the day branch, close the day with one pull request to develop. The steer file is the gate; a missing steer means pause.
---

# loop

The repository sees exactly what its policy asks for: one branch cut from `develop`, one pull
request to `develop` with the template body and the check output, merged by the owner. The
batching is local. Workers branch from a local day branch and never push; the owner reviews each
worker branch on this machine and folds it into the day branch; at close the day branch is
pushed once under an ordinary `type/slug` name. No bot, no comment on any issue, no `loop/*` ref
on the remote, no CI until the one pull request opens, one Testing deploy per day.

State: `LOOP_STATE_DIR/<owner__repo>/` (layout in the header of `scripts/loop.sh`). `steer` is
the gate: first word `go` or `pause`, and a missing file means pause. `day-branch` names the
open day (`loop/<date>`); its worktree is `.claude/worktrees/day-<date>` in the checkout.

## Setup, once per machine

`~/.config/dev-platform/repos.conf`: one line per repository, `owner/repo <tab> checkout path
<tab> owner|bot`. `owner` means the two GitHub writes the loop makes (`pr create` at close,
`issue close` at finish) use the human's own `gh` login and happen only in the owner's terminal;
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

Who runs what: the assistant runs `start`, `plan`, `go`, `pause`, `collect` and `close` (without
`--push`) on the owner's word in that session; the owner runs `fold`, `close --push`, `finish`
and `tidy --apply` in a terminal (they refuse without one); the tick automation runs `tick`.

1. `scripts/loop.sh status <owner/repo>`: steer, open day, running workers, worker branches and
   their state, folded issues, the day pull request.
2. `scripts/loop.sh start <owner/repo>`: fetch, cut `loop/<date>` from `origin/develop` into the
   day worktree, record it, write the PLAN. Refuses while a day is open.
3. `scripts/loop.sh go <owner/repo> [only N ...|skip N ...]`: write `steer: go`, plan, dispatch a
   worker per selected issue not yet dispatched, up to 3 running. Model per issue by tier:
   `spec`, `decision`, `privacy`, `security` labels use the judgment tier; `documentation` the
   mechanical tier; everything else the implementation tier. `scripts/loop.sh tick` does the same
   from a schedule and prints `NO_REPLY` unless steer says go and a day is open;
   `scripts/loop.sh pause` stops it.
4. A worker: one issue, one worktree, one `type/slug-N` branch from the day branch. It commits,
   runs `hooks/check-once.sh` (which records the passing tree), writes `.worker-pr.md` with the
   four template sections and `Closes #N`, and stops. It never pushes, opens a pull request or
   comments. A worker that finds the fix outside its scope, or the issue already resolved, writes
   `.worker-blocked.md` and stops; the owner widens the scope or closes the issue.
5. `scripts/loop.sh collect <owner/repo>`: the CYCLE report from the ledger and the worktrees,
   with its one metrics line.
6. `scripts/loop.sh fold <owner/repo> N ...`: the owner, after reading the worker's diff
   (`git diff loop/<date>..<branch>`) and `.worker-pr.md` in its worktree, merges the branch into
   the day branch with a merge commit, keeps the body under the ledger, removes the branch and
   worktree. Refuses a running worker, a blocked one, a dirty worktree, a branch that commits a
   `.worker-*` file, and a conflict (aborted; resolve by hand in the day worktree, then rerun).
7. `scripts/loop.sh close <owner/repo> [--as type/slug] [--title ...]`: run the check once on the
   day head (fails closed), write `pr.md` from the folded bodies with one `Closes #N` per issue,
   print the exact push and create commands. `--push` pushes the day branch as `type/slug`
   (default `fix/<date>`) and opens the one draft pull request to `develop` (`--ready` opens it
   ready). After more folds, `close --push` again pushes the update to the same pull request and rewrites its
   title and body from `pr.md`.
8. The owner reviews and merges it on GitHub, one CI run and one Testing deploy.
   `scripts/loop.sh finish <owner/repo> <pr>` then closes each folded issue with `Merged in #pr.`
   (closing keywords never fire on a non-default branch), deletes the pushed branch, removes the
   day worktree and branch, and writes `steer: pause`.
9. `scripts/loop.sh tidy <owner/repo>` weekly, read-only: remote branches merged into `develop`,
   clean worktrees with no live session whose branch is merged or a pointer to `main`, local
   branches in the same state. `--apply` bundles every ref to the ledger first, then deletes.

Writes to GitHub go through `scripts/ghx <owner/repo> <gh args>`, which picks the identity from
`repos.conf` and refuses merge, ready and review on every repository.
