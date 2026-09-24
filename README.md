# raspy-dev

<p align="center">
  <pre>
        ╭────────────────────────────────────────────╮
        │                raspy-dev                   │
        │     one tiny cockpit for many AI tools     │
        ╰───────────────┬────────────────────────────╯
                        │
        ╭───────────────┼─────────────────────────────╮
        │               │                             │
      GitHub          Herdr                        OpenRig
   ledger + PRs    cockpit view                   rig seats
        │               │                             │
        ╰──── VS Code · Claude · LLM · Codex · Pi ────╯
                        │
              checks · skills · sessions
  </pre>
</p>

A small personal development platform for keeping AI-assisted software work organized, bounded, and reviewable.

raspy-dev is not a framework, a product, or a replacement for GitHub. It is the local glue around my editor, terminal, coding agents, repository templates, checks, native-account selection, sessions, rig seats, and project workflow. The goal is simple: every tool can help, but GitHub remains the ledger and a human remains the release authority.

The style is deliberately modest and opinionated: inspired by the small-stack clarity of Theo/T3-style tooling and the practical pstack spirit of tiny local systems that do one job well.

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
owner decision
  -> GitHub issue / decision / pull request
  -> local project checkout or worktree
  -> Herdr / OpenRig / VS Code / Claude Code / Codex / Pi
  -> skills pick the lane and hydrate the surface
  -> checks and guardrails
  -> pull request, artifact, review finding, decision record or handoff
  -> human review, merge, tag, deploy
```

The important rule is that there is one ledger. Chats, agents, desktop apps, rig seats and terminals are work surfaces. GitHub issues and pull requests are the durable record.

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

- `bin/new-repo`: initializes a repository with the standard templates and branch rules.
- `bin/ai-session`: indexes native AI sessions without copying message bodies.
- `bin/ai-account`: verifies native account/profile selection and quota snapshots for new CLI launches.
- `bin/ai-work`: lists projects/sessions and forwards loop commands to the existing ledger.
- `bin/dev-workspace`: starts or plans native OpenRig control seats safely.
- `bin/ai-env`: read-only diagnostics for local tools, skills and optional services.
- `hooks/`: command guards, stop checks, one-shot check caching, post-edit formatting.
- `skills/loop`: the local development loop: plan, dispatch bounded workers, collect, fold, close.
- `skills/intake` and `skills/distill`: turn external notes into decision/spec work without copying private source material into repos.
- `templates/`: the repository standard: AGENTS, CONTRIBUTING, pull request template, hygiene checks, specs, release/check workflows.
- `docs/accounts.md`, `docs/session-index.md`, `docs/session-naming.md`, `docs/development-workspace.md`, and `docs/skills-layer.md`: the contracts for the local ecosystem.
- `ROLES.md`: which surface should do which kind of work.
- `MODELS.md`: which model tier should do which kind of work.

## Skills are the routing layer

The skills are not meant to be a pile of project-specific prompts. They are small reusable moves that let every surface ask the same questions:

- What project, worktree, loop or engagement owns this?
- What live context should be hydrated before acting?
- Should this be a rig seat, editor chat, loop worker, Pi role, desktop session or plain human note?
- What evidence proves the step is done?

Some tasks should enter an active loop. Some should become a rig seat with a hydration packet. Some should stay a chat, a note, or a read-only investigation. That flexibility is the point.

See [`docs/skills-layer.md`](docs/skills-layer.md) for the target shape and the cleanup plan for the current skills.

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
