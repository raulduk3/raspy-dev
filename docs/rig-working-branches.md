# Rigs on working branches

Direction recorded 2026-09-24. This is the target shape for the Iztac control rig.
It reuses the loop skill's existing branch contract; it does not invent a second one.

## The rule

One rig is one project engagement. Every seat's working directory is a Git worktree
on a branch the loop already knows about. No seat works in the checkout itself and
no two seats share a worktree.

| Seat | Runtime and account | Working directory | Branch |
| --- | --- | --- | --- |
| Root (`lead`) | Claude Code, verified Anthropic account | the day worktree `.claude/worktrees/day-<date>` | `loop/<date>` |
| Worker (one per issue) | Claude Code or Codex, account chosen by the account service | that issue's worker worktree | `type/slug-N` cut from `loop/<date>` |
| Overseer | Codex, the other provider on purpose | the day worktree, read-only | `loop/<date>` |

The root seat is the Iztac control surface described in
`integrations/openrig/agents/control`. It plans through the adapted pstack
workflow and the loop ledger. It spawns the rest: it asks the loop to cut a
worker worktree, then adds one member to the rig for that worktree. Workers do
not create their own branches and do not add seats.

The overseer reads worker diffs (`git diff loop/<date>..<branch>`), each worker's
`.worker-pr.md` and the recorded check, and reports. It never folds, pushes or
answers a permission prompt for a worker. Folding stays with the owner, exactly as
the loop skill says today. Putting the overseer on a Codex account gives an
independent reading from a different provider and keeps one provider's quota from
gating both writing and review.

## How it maps onto what exists

- **Branches and worktrees** come from the loop skill. `loop.sh` already cuts
  `loop/<date>` into the day worktree and `type/slug-N` into a worker worktree per
  issue. A rig adds seats to those directories; it does not replace the script.
- **Accounts** come from the account service. Each member carries `config_home` for
  an isolated home, or nothing for a native-default account, the same way
  `dev-workspace` renders a single control seat today. Usage per seat is attributed
  through that pin.
- **Seats** come from OpenRig. A rig starts with the root and overseer pods and an
  empty workers pod. Each dispatched issue becomes one `rig add <rig> workers
  <member-fragment>`, which is the same call that added the overseer to
  `apple-four` today. The member fragment is four lines: id, agent, runtime, cwd,
  plus `config_home` when the account is isolated.
- **Templates** live in `integrations/openrig`. The control agent stays silent at
  boot. Issue briefs are delivered the way the loop already delivers them, in the
  worker's directory, not through OpenRig startup files.

## What has to be built

1. A spec `integrations/openrig/iztac-control.yaml` with pods `root`, `workers`
   (empty) and `review`, rendered per account by `dev-workspace` the way the
   single-seat spec is rendered now.
2. A `dev-workspace add-worker <rig> <issue>` step that reads the worker worktree
   path from the loop ledger, resolves the account, writes the fragment to
   `~/.local/state/dev-platform/openrig/` and calls `rig add`. Interactive seats
   replace the headless worker for that issue; the worker contract (commit, run
   `hooks/check-once.sh`, write `.worker-pr.md`, stop) is unchanged.
3. Managed files in worktrees. OpenRig writes `.claude/settings.local.json`,
   `.openrig/` and `CLAUDE.md` into every seat's directory. In a personal
   repository they are harmless. In a professional repository a worker worktree
   must exclude them before the seat starts (`.git/info/exclude` is per repository,
   so the add step writes the entries), and `fold` must refuse a branch that
   commits any of them, as it already refuses `.worker-*` files. This is the one
   blocking item; until it exists, rigs stay in personal repositories and external
   folders, which is what `dev-workspace` enforces today.
4. Removal. When the owner folds an issue, the seat for it comes down with the
   worktree. `rig down` on the rig ends the engagement; the day branch survives it.

## Proven today

`rig add` onto a running rig works with the patched daemon: `intake-overseer@apple-four`
is a Codex seat on the native Apple home, added to a live four-seat Claude rig
without restarting anything. Per-seat account pinning through `config_home` was
proven earlier the same day. Nothing above needs a change to OpenRig.
