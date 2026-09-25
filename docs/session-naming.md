# Automatic session naming

All agents and contexts may name **their own session** automatically when the task becomes
clear, and refresh their own generated title when scope materially changes. This includes
Pi roles (Morty, Neo, Iztac), OpenRig control seats, Claude Code, Codex, editor chats, delegated
agents, headless workers, and personal/nonengineering work. No naming-only approval is
needed. This is permission to use available naming controls, not a claim every client
exposes one to the agent.

## Small, consistent rules

- Preserve a title explicitly chosen by the owner unless asked to change it. When title
  provenance is uncertain, preserve an existing meaningful title rather than guessing.
- Engineering: `kind(area): Description #ref`, as defined in `ROLES.md`. Omit an unknown
  reference; do not invent it. Use a real repository scope or `repo` when no scope fits.
- Other work: a short, plain descriptive title, such as `Plan October travel` or
  `Compare AI account allowances`; do not impose engineering syntax on personal contexts.
- Do not put secrets, account identifiers, customer data, raw prompts or billing details
  in titles. Titles are labels, not transcripts or proof of status.
- Preserve native session/thread IDs, account selection, ownership and worktree bindings.
  Naming does not take over a session, resume it, change its scope, or authorize execution.
- Do not automatically rename another agent's live session. A launcher may provide an
  initial title when creating a new child session. Do not bulk-edit historical titles.

## Use the owning runtime

| Surface | Supported path and boundary |
| --- | --- |
| Claude Code | Installed CLI `-n/--name` sets a new session's display name. The interactive `/rename` command is a user-facing native control; do not assume an agent can invoke slash commands as tools. |
| Codex | Use an exposed native session-name control. The official app-server protocol has `thread/name/set`; use it only through an already integrated client. Do not start a parallel app-server or write SQLite just to rename. |
| OpenClaw (retired) | Not used. Its preserved sessions are archives and are never renamed. |
| OpenRig | Name the underlying harness conversation through a supported control. Rig names, seat IDs, member labels and native conversation titles are distinct; changing one does not prove the others changed. |
| VS Code / other clients | Use the client's exposed native naming action if available. Otherwise retain its automatic title or suggest a concise title; do not invent a rename API. |
| Filesystem index | `ai-session title` is an **index-only** display override. See [Session index](session-index.md). It never renames a native conversation. |

Confirm the returned label/title after a native operation when that interface supports a
read. Report an unavailable control accurately; do not claim successful native naming from
an index update, message send, terminal title or instruction alone.

## Loop workers

The loop supplies `--name` when starting a new Claude worker, using the task's issue title,
branch kind and issue number. The title is a single bounded, whitespace-normalized CLI
argument, never shell code. The existing loop `resume` verb starts a new worker attempt in
the existing worktree; it does not rename or resume an existing native conversation. Its
new attempt receives the current issue title. Existing sessions and transcripts are untouched.

## Evidence

- Local `claude --help`, inspected 2026-09-24, documents `-n, --name <name>` as the display
  name shown in the prompt box, resume picker and terminal title.
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) and
  [interactive mode](https://code.claude.com/docs/en/interactive-mode).
- [Codex app-server](https://developers.openai.com/codex/app-server), `thread/name/set`.

These controls are version-dependent. Check the installed interface before expanding the
integration; naming must not weaken sandboxes, change credentials, or create another service.
