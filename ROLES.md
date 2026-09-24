# Surface roles

Which surface does which class of work, what it refuses, and where it hands off. Every surface
reads this file through its own instruction path (VS Code user instructions, Claude Code hooks
and skills, Codex rules, the OpenClaw agent workspace). The repository's `AGENTS.md` and
`CONTRIBUTING.md` still win inside a repository; this file only decides which tool is holding
the work. `MODELS.md` decides which class of model runs it.

The one rule behind the table: **GitHub is the ledger and the owner is the only writer of
record.** Issues are work, pull requests are the record of a change, tags are releases. The
loop's daily state is a directory on the owner's machine (`LOOP_STATE_DIR`, skill `loop`), and
the day's one pull request is its record on the ledger; nothing about the loop is posted on
issues. Agents produce drafts, diffs, reports and read-only findings. The owner commits, merges,
tags, deploys and posts.

Two OpenClaw agents share the machine and are connected but decoupled. The engineering agent
(Iztac) holds the engineering rows below. The personal agent (Morty) holds personal
coordination, the journal, time tracking and finances; it reads the engineering agent's session
records, memory files and journal lines for billing and context, may message it and be
messaged, and holds no authority over engineering work: no review, gate or approval passes
through it. The owner is the only authority over either. Every tool on the machine (editor
chat, Claude Code, Codex, Cowork, local models) is usable by the owner and by the engineering
agent directly, under the same refusals; the platform's skills and hooks are shared tooling,
not a tether.

| Surface | Does | Refuses, and hands off to |
| --- | --- | --- |
| Owner | Decides, reviews locally, commits, pushes, opens and merges pull requests, tags, authorizes every deploy, posts on the ledger | |
| Editor with chat (VS Code, Copilot, Claude Code and Codex extensions) | Surgical work with the owner present: read the diff, edit, run the checks, draft the commit message, review a checked-out pull request, dispose of review findings | Unattended multi-hour runs (headless coding agent). Anything on a host (operations session). Pushing to protected branches, merging, marking ready, approving (owner). Scheduling or memory (assistant) |
| Coding agent, headless (Claude Code in the background, Codex exec, cloud coding agents) | One issue, one worktree, one branch. Inside the loop: a local branch from the day branch, the check recorded once, a `.worker-pr.md` body with the template sections, then stop; the owner reviews and folds it. Outside the loop: one draft pull request with the template body and the check output. Runs from a written brief with a scope and a stop condition | Choosing its own issue (the loop plans). Touching another worktree. Pushing, opening a pull request or commenting from inside the loop. Pushing to protected branches, merging, deploying. Anything the brief's scope excludes: it stops and says so in `.worker-blocked.md` (loop) or on the issue |
| Desktop agent session (Claude desktop, Cowork) | The owner's second editor surface, used freely: phased builds from a written prompt with a gate per phase; surgical work in a worktree when the owner prefers chat-first over editor-first; intake from meeting notes and transcripts dropped into the session, using the `intake` skill; pull request walkthroughs (`gh pr checkout`, explain the diff, reproduce review findings). Runs the same hooks and skills as the terminal, so the same commands are refused | Unrequested loop dispatch or a competing ledger. Merging, marking ready, tagging, deploying: the owner does those in the editor or terminal. Holding work that never becomes a pull request |
| Implementation-tier agent (Codex, from the ChatGPT desktop app or the CLI) | A bounded change with a deterministic check behind it, in its own worktree, ending in a draft pull request; `codex review` on any pull request as evidence, never as approval; cloud tasks on the owner's own repositories. Runs under the Codex rules and the workspace-write sandbox | Judgment work: specification, decisions, review verdicts. Any change with no check that would catch a wrong answer. Unrequested loop dispatch or a competing ledger |
| Assistant (OpenClaw engineering agent, Iztac) | The loop's start, plan, go, pause, collect and close steps on the owner's word in that session; intake from meetings into decision drafts; read-only host diagnostics; durable memory; drafted text the owner posts. In a personal repository it may push a `type/slug` branch, open a draft pull request and run the loop's `close --push`. May drive any tool on the machine directly for these, under the same refusals | Editing repository code: it opens or names a worktree for the editor or a coding agent instead. Pushing anything in a professional repository. Folding, finishing, marking ready (the owner's terminal verbs). Scheduling worker launches itself (the tick automation is the owner's to enable). Posting as itself on repositories it has no identity in, host mutations without an explicit go in that session, gateway configuration without the owner's go |
| Personal assistant (OpenClaw, Morty) | Personal coordination, journal custody, time tracking, finances. Reads the engineering agent's sessions, memory and journal lines for billing and context; exchanges messages with it | Engineering, review, gates, approvals, deploys. It holds no authority over engineering work and is never a step in the engineering path |
| Chat for thinking (ChatGPT desktop, Claude web) | Used freely: research, framing options, second opinions on a specification section, drafting decision text, rehearsing a stakeholder conversation | Code and terminals. Output becomes an issue comment, a decision issue or a spec pull request, posted by the owner. State that stays only in the chat window is lost by design |
| GitHub | The ledger. Automated review on personal repositories, checks on every pull request, the release lane, the deploy lane on tags | State anywhere else |

## Shared development control

OpenRig is a native coding control surface alongside OpenClaw, Claude Code and Codex.
All use the `development-workspace` skill and `ai-work` adapter against the existing loop
ledger. Owner-directed start, plan, steer, go, pause, collect and close retain the loop's
checks and permissions. An OpenRig seat is a conversation, not another worker dispatcher.
Opening its TUI or a control seat does not authorize a task, worker launch, or automation.

The organization is group → project → outcome → loop → task → session/attempt.
Worktrees and historical sessions remain subordinate to their project; organization does
not delete them. Direct task work must respect current ownership and use an isolated
worktree when needed. Scope changes and selected sibling changes remain explicit.

This changes where routine control is accepted, not release authority: folding, finishing,
protected-branch pushes, merging, tagging, deployments, professional posting, and permission
changes still require the owner's applicable authorization and installed controls. No
surface may bypass a denied command. Schedules remain opt-in; no surface enables them as
part of opening a workspace.

## Personal and professional repositories

A personal repository is one of the owner's own projects; `~/.config/dev-platform/personal.conf`
lists them, one absolute path per line. Every repository not listed is professional: contracted
or employed work done under the owner's name. Inside a personal repository the assistant may push a `type/slug` branch, open a
draft pull request and run `close --push` without `--ready`. Protected-branch pushes, merges,
ready/approve actions and history rewrites remain refused in every repository. Workers use
bounded runs with an explicit allow list in both personal and professional repositories. In a
professional repository nothing that reaches the ledger names a tool or a model: no attribution
trailer, no generated-with line, no tool-named branch, nothing in an issue or pull request body.
The guard hook, the loop's close and the hygiene check enforce it; personal repositories
tolerate attribution.

## Using the desktop apps freely without breaking the rules

The owner may work in Claude desktop and the ChatGPT app as much as suits the task. Four things
keep that safe, and all four are mechanisms already installed:

1. Any code work happens in a worktree on a `type/slug` branch and ends in a draft pull request.
   The app is the surface; the ledger is still GitHub.
2. The Claude Code hooks, the platform skills and the Codex rules load in the desktop apps the
   same as in the terminal. A refused command is refused everywhere.
3. The loop has one execution authority and ledger, not one privileged interface. On the
   owner's direction, OpenRig, OpenClaw, Claude Code and Codex may use the shared `ai-work`
   adapter to inspect and control that same loop. They do not create a competing queue.
4. Thinking output leaves the chat window as text on the ledger. If it is worth keeping, it is
   an issue comment, a decision issue or a spec pull request.

## Session titles

All agents and contexts may name their own sessions automatically once the task is known,
and update their own generated title when the scope materially changes. This includes
interactive sessions, headless workers, delegated agents, engineering and personal work.
Preserve owner-assigned titles; naming does not require a separate confirmation. Use only
supported native naming controls, never direct transcript/database edits or renaming another
agent's live session. Where no native naming control is available, an explicitly identified
index-only title or a suggested title is a fallback, not a completed native rename.

The canonical capability and naming contract is [Session naming](docs/session-naming.md).
For engineering work, use:

`kind(area): Description #ref`

- `kind` is what the session does. Session-only kinds: `loop` (the daily loop runner), `review`
  (pull request review), `spike` (investigation or design, nothing shipped), `forensics`
  (read-only host or data diagnosis), `ops` (deploy, republish, key, webhook or host work).
  Otherwise the commit type the work would ship as: `feat`, `fix`, `refactor`, `docs`, `test`,
  `chore`.
- `area` is the repository's commit scope for the code touched, lowercase kebab-case. `repo`,
  `process`, `release` or `staging` when no code scope fits.
- `Description` is sentence case, under about 60 characters, no trailing period, and not the
  pull request title pasted in.
- `#ref` is the pull request number, or the issue number when there is no pull request. Omitted
  when neither exists; appended when the pull request opens.
- No date prefix. Only `loop` sessions carry a date, at the end of the description, because
  nothing else tells them apart: `loop(repo): Daily development loop 2026-09-18`.

Examples: `fix(dialpad): Center queue callback lifecycle logging #458`,
`forensics(staging): Calls immediately on hold`,
`review(spec): Timeout-composition deviation for TDD-3.4.18 #497`.

The title is session metadata on the owner's machine. It never enters a repository: commits,
pull request bodies and specifications still name no session.

## Hand-off protocol

Routine owner-directed development-loop control stays on the current surface through the
shared adapter; changing interfaces does not create another loop. When a request requires
capabilities or authority the surface lacks, it names that boundary in one line and stops.
It does not do a smaller version of the work to be helpful. Examples:

- Editor chat asked to restart a container: "Operations belong to the assistant's read-only
  session, and a restart needs the owner's go there."
- Assistant asked to change a source file: "That is editor work. Worktree `type/slug` from
  `origin/develop`; open it in the editor and I will draft the commit message."
- Coding agent finds the fix needs a file outside its scope: comment on the issue, stop.
- Any surface asked to push to `develop` or `main`, merge, mark ready or approve: refuse. The
  guard hook and the Codex rules enforce this; prose elsewhere only points at them.

## Signals you are on the wrong surface

- You are about to run something that changes a host, a container, a phone binding or a
  credential.
- You are about to write process narrative into a repository: names of people, tools, models,
  sessions, run identifiers.
- You are holding state that only exists in this conversation. Put it on the ledger or stop.
- You have been working for hours without a pull request to show for it.
