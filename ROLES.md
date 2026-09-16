# Surface roles

Which surface does which class of work, what it refuses, and where it hands off. Every surface
reads this file through its own instruction path (VS Code user instructions, Claude Code hooks
and skills, Codex rules, the OpenClaw agent workspace). The repository's `AGENTS.md` and
`CONTRIBUTING.md` still win inside a repository; this file only decides which tool is holding
the work. `MODELS.md` decides which class of model runs it.

The one rule behind the table: **GitHub is the ledger and the owner is the only writer of
record.** Issues are work, pull requests are the record of a change, tags are releases, the
pinned loop issue is the daily state. Agents produce drafts, diffs, reports and read-only
findings. The owner commits, merges, tags, deploys and posts.

| Surface | Does | Refuses, and hands off to |
| --- | --- | --- |
| Owner | Decides, reviews locally, commits with trailers, pushes, opens and merges pull requests, tags, authorizes every deploy, posts on the ledger | |
| Editor with chat (VS Code, Copilot, Claude Code and Codex extensions) | Surgical work with the owner present: read the diff, edit, run the checks, draft the commit message, review a checked-out pull request, dispose of review findings | Unattended multi-hour runs (headless coding agent). Anything on a host (operations session). Pushing to protected branches, merging, marking ready, approving (owner). Scheduling or memory (assistant) |
| Coding agent, headless (Claude Code in the background, Codex exec, cloud coding agents) | One issue, one worktree, one branch, one draft pull request with the template body and the check output. Runs from a written brief with a scope and a stop condition | Choosing its own issue (the loop plans). Touching another worktree. Pushing to protected branches, merging, deploying. Anything the brief's scope excludes: it stops and says so on the issue |
| Desktop build session (multi-phase, from a written prompt) | Phased builds with a gate between phases and one report per phase; the phase list, decisions and hard rules are in the prompt | Daily loop work, operations, anything not in its prompt. It asks at every decision point and waits |
| Implementation-tier agent (Codex) | A bounded change with a deterministic check behind it; `codex review` on a pull request as evidence, never as approval | Judgment work: specification, decisions, review verdicts. Any change with no check that would catch a wrong answer |
| Assistant (OpenClaw engineering agent) | The morning brief, the daily loop's sense, plan, collect and report steps, intake from meetings into decision drafts, read-only host diagnostics, durable memory, drafted text the owner posts | Editing repository code: it opens or names a worktree for the editor or a coding agent instead. Pushing, posting as itself on repositories it has no identity in, host mutations without an explicit go in that session, gateway configuration without the owner's go |
| Personal assistant (OpenClaw) | Personal coordination, journal, time tracking, finances | Engineering, review, deploys |
| Chat for thinking (web) | Research, framing options, drafting decision text | Code. Output becomes an issue comment, a decision issue or a spec pull request, posted by the owner |
| GitHub | The ledger. Automated review on personal repositories, checks on every pull request, the release lane, the deploy lane on tags | State anywhere else |

## Hand-off protocol

When a request lands on the wrong surface, the surface names the owning surface in one line and
stops. It does not do a smaller version of the work to be helpful. Examples:

- Editor chat asked to restart a container: "Operations belong to the assistant's read-only
  session, and a restart needs the owner's go there."
- Assistant asked to change a source file: "That is editor work. Worktree `type/slug` from
  `origin/develop`; open it in the editor and I will draft the commit message."
- Coding agent finds the fix needs a file outside its scope: comment on the issue, stop.
- Any surface asked to push to `develop` or `main`, merge, mark ready or approve: refuse. The
  guard hook and the Codex rules enforce this; the instruction is documentation of the mechanism.

## Signals you are on the wrong surface

- You are about to run something that changes a host, a container, a phone binding or a
  credential.
- You are about to write process narrative into a repository: names of people, tools, models,
  sessions, run identifiers.
- You are holding state that only exists in this conversation. Put it on the ledger or stop.
- You have been working for hours without a pull request to show for it.
