<p align="center">
  <img src="docs/images/raspy-dev.jpg" alt="A terracotta bowl with animals carved in relief around its rim" width="360">
</p>

<h1 align="center">raspy-dev</h1>

<p align="center"><em>One small cockpit for many AI tools. Say what you want; watch a team build it on one branch; land it yourself.</em></p>

A small personal development platform for keeping AI-assisted software work organized, bounded, and reviewable.

raspy-dev is not a framework, a product, or a replacement for GitHub. It is the local glue around my editor, terminal, coding agents, repository templates, checks, native-account selection, sessions, rig seats, and project workflow. The goal is simple: every tool can help, git holds the truth, and a human remains the release authority. Everything runs locally; GitHub is opt-in per repository.

The style is deliberately modest and opinionated: inspired by the small-stack clarity of Theo/T3-style tooling and the practical pstack spirit of tiny local systems that do one job well.

## Try it: "hmm, I want Tetris"

One command, `ai`, and plain sentences. Everything stays on your machine.

1. **Say the goal.** Run `ai`, pick **Start a new project**, name it `tetris`, and answer *What do you want to build?* with "a Tetris game in the browser". The repository is created from the templates, and Claude (or Codex) opens in it already asked to spec it.
2. **Agree on the spec.** In that chat, read the decision it drafts and say "yes". It writes the first requirements and the task files on a `docs/` branch, then stops.
3. **Land the spec.** Back in `ai`: **tetris**, **Development loop**, **Merge a spec branch into develop**. Read the diff, answer `y`.
4. **Start the team.** **This project's team** starts a control seat and a review seat; **Open the team's space in herdr** shows them side by side.
5. **Name the goal.** **Development loop**, **Start a branch for a goal**, `feat/tetris`.
6. **Seat the workers.** **Dispatch ready tasks as seats** gives every ready task a worker on its own branch. Tell the control seat "start the workers".
7. **Watch it happen.** **Watch it in VS Code** opens the goal branch and every worker's branch as folders in one window; files fill in as the workers commit.
8. **Land it.** When the workers report done, tell the control seat "merge them up". It checks each branch, releases its seat and merges it into `feat/tetris`, then tells you it is ready. Pick **Land feat/tetris** and answer `y`. One merge on `develop`, and the game is there.

The shape underneath: a goal gets one branch, each task gets a child branch, finished children merge up once their check passes, and only you land the goal on the base. [`skills/loop/SKILL.md`](skills/loop/SKILL.md) has the verbs; [`docs/pstack-platform.md`](docs/pstack-platform.md) the engineering method (`/dev-plat`).

## What it connects

raspy-dev instruments the whole local developer stack:

- **Git and GitHub**: issues, pull requests, branch protections, rulesets, release lanes.
- **Herdr**: a cockpit view for spaces, projects, tabs, rig panes and active work.
- **OpenRig**: native project/control surface, rig seats, team spaces and seat handoff.
- **VS Code**: editor instructions and terminal approval defaults.
- **Claude Code**: hooks, stop checks, formatting, command refusals, session conventions.
- **Codex**: execution rules for bounded implementation and review work.
- **Pi/OpenClaw-style agents**: role-specific assistants that can read the same platform contracts without becoming release authorities.
- **Native account/profile controls**: explicit account selection and quota snapshots for new CLI launches.
- **Bun, Node, Python, gh, git, jq, 1Password CLI**: the ordinary local toolchain used by checks, helpers and runbooks.
- **Laya**: optional local decision/probe service diagnostics through `ai-env doctor`.

Each tool keeps its native UX. raspy-dev supplies the common rules, scripts, templates, adapters and handoff language.

## The shape of the system

```text
owner goal
  -> decision, spec and task files (or GitHub issues, where a repository opts in)
  -> a goal branch, and a child branch per task in its own worktree
  -> Herdr / OpenRig / VS Code / Claude Code / Codex / Pi
  -> skills pick the lane and hydrate the surface
  -> checks and guardrails
  -> pull request, artifact, review finding, decision record or handoff
  -> human review, merge, tag, deploy
```

The important rule is that there is one ledger. Chats, agents, desktop apps, rig seats and terminals are work surfaces. Git is the durable record: branches, commits, task files and decision records, with GitHub issues and pull requests where a repository uses them.

## Filesystem layout

The repo expects a normal local layout but does not require secrets in the repository:

```text
~/Dev/raspy-dev or ~/Dev/dev-platform
  bin/                         CLI entrypoints
  docs/                        platform contracts
  github/rulesets/             branch ruleset JSON
  hooks/                       Claude Code, Codex, check and formatting hooks
  integrations/openrig/        OpenRig seat configuration
  lib/ai_ecosystem/            session, account, workspace and environment adapters
  runbooks/                    manual procedures
  skills/                      reusable agent/operator procedures
  templates/                   files copied into new repositories
  tests/                       offline tests for the platform itself
  vscode/                      VS Code instructions and settings snippets

~/.config/dev-platform/
  repos.conf                   repository map: owner/repo, checkout, identity, base
  personal.conf                local-only list of personal repositories
  brief.conf                   local-only loop and environment configuration
  accounts.conf                local-only native account/profile configuration

~/.local/state/dev-platform/
  loop/                        local development-loop ledger
  sessions/                    reconstructed session index
  engagements/                 project/engagement artifacts outside source repos
  workspace/                   generated OpenRig project catalog
```

Scratch files and helper scripts belong in a project worktree or project artifact directory, not on the Desktop. The hooks enforce that for common cases.

## What is in this repository

- `bin/ai`: the menu over everything here: projects, sessions, roles, teams and accounts. It hands off to the commands below and keeps no state of its own.
- `bin/new-repo`: initializes a repository with the standard templates and branch rules.
- `bin/ai-session`: indexes native AI sessions without copying message bodies.
- `bin/ai-account`: verifies native account/profile selection and quota snapshots for new CLI launches.
- `bin/ai-work`: lists projects/sessions and forwards loop commands to the existing ledger.
- `bin/dev-workspace`: starts or plans native OpenRig control seats safely.
- `bin/ai-env`: read-only diagnostics for local tools, skills and optional services.
- `hooks/`: command guards, stop checks, one-shot check caching, post-edit formatting.
- `skills/loop`: work toward a goal on one branch: dispatch workers on child branches, merge each finished child up, land the goal once.
- `skills/dev-plat` and the other pstack skills: the engineering method, ported from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (MIT, Lauren Tan) by `bin/pstack-port`.
- `skills/intake` and `skills/distill`: turn a goal or external notes into decisions, specification and task files, without copying private source material into repos.
- `templates/`: the repository standard: AGENTS, CONTRIBUTING, pull request template, hygiene checks, specs, release/check workflows.
- `docs/how-it-connects.md`: the map of the whole setup (accounts, homes, seats, rigs, OpenRig) for the person using it. Start there.
- `docs/rig-working-branches.md`: the control rig, one worker seat per loop worktree and a Codex overseer.
- `docs/accounts.md`, `docs/session-index.md`, `docs/session-naming.md`, `docs/development-workspace.md`, and `docs/pstack-platform.md`: the contracts for the local ecosystem.
- `ROLES.md`: which surface should do which kind of work.
- `MODELS.md`: which model tier should do which kind of work.

## Skills are the routing layer

The skills are not meant to be a pile of project-specific prompts. They are small reusable moves that let every surface ask the same questions:

- What project, worktree, loop or engagement owns this?
- What live context should be hydrated before acting?
- Should this be a rig seat, editor chat, loop worker, Pi role, desktop session or plain human note?
- What evidence proves the step is done?

Some tasks should enter an active loop. Some should become a rig seat with a hydration packet. Some should stay a chat, a note, or a read-only investigation. That flexibility is the point.

See [`docs/skills-audit.md`](docs/skills-audit.md) for which skill does what, and [`docs/pstack-platform.md`](docs/pstack-platform.md) for the engineering method.

## Agents and surfaces

The platform distinguishes roles instead of pretending every AI tool is the same:

- **Owner**: decides, reviews, merges, tags, deploys.
- **Herdr**: cockpit view over projects, tabs, rig seats and current work.
- **OpenRig seats**: bounded conversations with project identity, peers, context and stop conditions.
- **Editor chat**: surgical edits with the owner present.
- **Headless coding agents**: one issue, one branch, one worktree, stop after check and PR body.
- **Desktop agent sessions**: flexible planning, intake, review walkthroughs, phased work, but no competing ledger.
- **Implementation-tier agents**: deterministic bounded changes and review evidence, not final approval.
- **Engineering assistant**: loop control, diagnostics, memory, drafted text and coordination under the same refusals.
- **Personal assistant**: personal coordination, time, journal and billing context, with no engineering gate authority.

The same repository policy should be visible from every surface.

## Privacy stance

This repo is meant to be public-safe. It should contain procedures, templates, tests and generic examples, not private records.

- No API keys, tokens, private prompts, transcripts or customer records.
- No raw meeting notes or emails.
- Local configuration stays in `~/.config/dev-platform`.
- Credentials are read at runtime from the user's own credential store when needed.
- Session indexing stores metadata only, not message bodies.

If a private source produces engineering work, it becomes a redacted decision, issue, spec change or pull request. The private source itself stays outside the repository.

## Status

Personal infrastructure. Useful, tested, and evolving. Not packaged as a general-purpose product yet.
