# pstack on this platform

pstack is Lauren Tan's (poteto's) set of engineering skills for Cursor, MIT licensed. This
platform uses it as its engineering method: `/poteto-mode` is the front door for any engineering
task that needs rigor, and its playbooks, principles and routed skills are the shared contract
between every tool, agent and seat that writes code here. Her text is kept as she wrote it. This
page says what her Cursor-specific names mean on this machine. Where her text and this page
disagree about a tool name, this page wins. Where they disagree about method, hers wins.

## Where it lives

| Path | What |
| --- | --- |
| `vendor/pstack/` | Her tree, unmodified, at the commit in `vendor/pstack/UPSTREAM`. Never edit it. |
| `skills/<name>/` | The installed copies, built by `bin/pstack-port`. The list is `integrations/pstack/ported.txt`. |
| `integrations/pstack/overlays/<name>/` | Whole-file adaptations that replace the vendored file. Today only `setup-pstack`. |
| `~/.config/dev-platform/pstack-models.md` | The per-role model file `/setup-pstack` writes (her `pstack-models.mdc`). |

A port changes two things in every skill: the frontmatter `name` becomes the folder name, and one
line after the frontmatter points here. `bin/pstack-port --check` (run by `bin/check`) fails when
`skills/` drifts from a fresh port.

To take a newer pstack: replace `vendor/pstack/` with the new upstream path, update `UPSTREAM`,
run `bin/pstack-port`, read `git diff skills/`, and fix any overlay the upstream change touched.

Not ported: `make-bot-ui` (it drives Cursor Automations webhooks) and the `automations/benny`
skills (Cursor Automations triage and reproduce bots). They stay in `vendor/` for reference.

## Reaching a skill her text names

Her skills set `disable-model-invocation: true`: a person starts one with `/<name>`, and
`poteto-mode` reaches the rest by reading them. "The **how** skill" means read
`skills/how/SKILL.md` in full, next to the skill you are in (installed:
`~/.agents/skills/how/SKILL.md`, or `~/.local/share/dev-platform/current/skills/how/SKILL.md`).
Pi roles have skill discovery off; they read the same files by path.

## Cursor names and what they are here

| Her text says | On this platform |
| --- | --- |
| A `Task` subagent, `Task` tool | Claude Code's `Agent` tool (`run_in_background: true`, `subagent_type: general-purpose`). Codex: its own subagents, or `codex exec` started in the background. |
| `subagent_type: "poteto-agent"` | `general-purpose`, with the brief's first line: read `skills/poteto-mode/SKILL.md` in full, including its Principles index. |
| A model slug in `model:` | The first word of the role's line in `pstack-models.md`. Claude `Agent` takes `fable`, `opus`, `sonnet`, `haiku`; the effort token applies only where a process is started (`claude --effort`). A `codex:<model>` entry runs as `codex exec --model <model>`. |
| `environment: "cloud"`, cloud VM, `cloud_base_branch` | There is no cloud. A worker runs on this machine in its own git worktree: `Agent` with `isolation: "worktree"`, a loop worker, or an OpenRig worker seat (`dev-workspace add-worker`). A base branch means the worktree is cut from that local branch. |
| `~/.cursor/rules/pstack-models.mdc` | `~/.config/dev-platform/pstack-models.md`, written by `/setup-pstack`. Missing file or line: her skill default, read through this table. |
| `.cursor/skills/` (project), `~/.cursor/skills/` (user) | `.claude/skills/` and `.agents/skills/` in the repository; `~/.claude/skills/` and `~/.agents/skills/` for the user. A skill for every repository belongs in this platform's `skills/`. |
| Cursor's built-in `create-skill` | The Authoring playbook with the `skill-creator` skill where the client has it. Validate with `tests/test_skill_frontmatter.py`'s rules: strict YAML, `name` equal to the folder, a whole description. |
| `AskQuestion` | `AskUserQuestion` in Claude Code. Elsewhere, a question with numbered options. |
| `agent-transcripts/` for the active workspace | Claude Code: `~/.claude/projects/<workspace path with / as ->/*.jsonl`. Codex: `~/.codex/sessions/<yyyy>/<mm>/<dd>/*.jsonl`, filtered by `cwd`. Her rule stands: only the active workspace's records. |
| Cursor's `/loop`, wake chain, heartbeat | Claude Code's `/loop` and a background `Monitor` or shell watcher. The development loop's `dev-loop tick` is the owner's to schedule, never an agent's. |
| `cursor-team-kit` `/deslop` | The `simplify` skill on the diff. |
| `control-ui` | The built-in browser pane or Claude in Chrome, or the `run` skill. |
| `control-cli` | The real terminal, or the `run` skill. |
| Cursor's built-in babysit skill | Not present. Her Babysit playbook is the only one. |
| Bugbot, agentic security review | GitHub review comments when a repository has them; `/code-review` and `/security-review` otherwise. Same skeptical triage. |
| MCPs "the Cursor environment" exposes | The session's MCP servers; `ToolSearch` lists deferred ones. |
| The Cursor dashboard (cloud agent status) | `rig ps` and `rig_rig_nodes` for seats; `dev-loop status` for loop workers. |
| `origin pr` (Origin forge) | Not installed. `gh` is the forge. |
| `gt` (Graphite) | Not installed. Her Opening a PR playbook already says never require it. `orch frontier set` needs it; until a gh-based frontier exists, compute the frontier from `gh pr list` and `git`. |
| `bun scripts/...` (orch, watch-pr) | Run with `~/.bun/bin/bun` from `skills/poteto-mode/scripts` after `bun install`. |

## Repositories without a forge

`repos.conf` marks each repository `local`, `owner` or `bot`. A `local` repository has no pull
requests. Every step that opens, edits or watches a pull request becomes: the branch is ready,
its briefing-style body (her Opening a PR sections) is in the worker's `.worker-pr.md`, and the
owner merges it into the base with `git merge --no-ff` in a terminal. Tasks are `docs/tasks/`
files (see the `intake` and `loop` skills); a task number is the issue number her text cites.

## What the guard hook leaves to the owner

`hooks/pre-tool-use-guard.sh` refuses these for every agent in every repository. Her playbooks
run them; here the agent stops at the step and hands it to the owner, with the exact command.

| Her step | Refused | What happens here |
| --- | --- | --- |
| Opening a PR: rebase into small ordered commits; amend a just-made commit | `git rebase`, `git commit --amend`, `git reset --hard` | Commit in the intended order as you go. A fix to an earlier commit is a new commit. |
| Stacks: a child rebases onto its parent's tip; Shipping rebases the bottom PR onto trunk | `git rebase`, force push | Merge the parent into the child (`git merge <parent>`), or ask the owner to restack. |
| Shipping, Autopilot-full: merge the verified bottom PR | `gh pr merge`, merges into `develop` or `main` | Stop at merge-ready with the per-PR verdict. The owner merges. |
| Babysit: mark ready | `gh pr ready` | Opening ready (`gh pr create` without `--draft`) is allowed and is her default. |
| Pushing | Push to `develop` or `main`, force push, a bare `git push` | Push only the named `type/slug` branch. |
| Deploys, restarts | docker, systemctl, ssh mutations | The owner, every time. |

In a professional repository (not in `personal.conf`) nothing that reaches GitHub names a tool or
model, and the platform's publication rules decide whether an agent pushes at all.

## Seats and the development loop

In her Orchestrate playbook one coordinator owns the program and writes briefs; workers own units;
a verifier on a different model family checks each unit. On OpenRig that is: the `control.lead`
seat runs `/poteto-mode` and follows Orchestrate; each `workers.*` seat runs `/poteto-mode` with
the playbook its brief names (Feature, Bug fix, Refactoring); the `review.overseer` seat runs
`/interrogate` on a finished unit. Every brief carries her fields: GOAL, SCOPE, CONTEXT,
ACCEPTANCE, VERIFY, TIMEBOX, FORBIDDEN, REPORT, STANDING. The seat definitions under
`integrations/openrig/agents/` do not yet install these skills; that is the next change.

### Branches, not days

Today the loop gathers a day's work on an invented `loop/<date>` branch: workers branch from it,
`fold` merges them into it, and `close` merges or pushes it once. Her model has no aggregation
branch, and neither should the loop:

- A unit is a task and its one branch, `type/slug-N`. Its parent is the base when `Depends on:
  none`, else the branch of the task it depends on. Dependent tasks form a stack.
- Landing is continuous. A unit whose verdict is recorded for its head and whose parent has
  landed is merge-ready. Locally the owner merges it into the base; on GitHub it is one pull
  request, the root targeting the base and each child its parent, landed bottom-up.
- The ledger is per repository, not per day: one row per unit (task, branch, parent, head, verdict),
  like her `units.tsv` and `ledger.tsv`. `status` shows the frontier (the lowest unlanded unit
  of each stack).
- `start`, `day-branch`, `fold`, `close` and `finish` give way to dispatch, verify and land.
  `dev-loop tasks` and the `docs/tasks/` files stay: they are her units, written down.

This is a design; `skills/loop/scripts/loop.sh` still runs days until that change is made.
