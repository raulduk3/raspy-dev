# Session index and environment doctor

`bin/ai-session` keeps a local, reconstructible index of Claude Code, Codex, OpenClaw and
VS Code chat sessions. `bin/ai-env doctor` reports on the local toolchain. Both are local only:
no daemon, scheduler, database service, network call or model call, and neither writes native
client storage.

## ai-session

```
ai-session [--state-root DIR] scan [--limit N] [--home DIR] [--no-openclaw]
ai-session list [--json] [--runtime claude|codex|openclaw|copilot]
ai-session show ID
ai-session title ID TEXT [--expect-revision N]
ai-session handoff ID [--import FILE|- --expect-revision N]
ai-session resume ID [--execute]
```

State lives under `~/.local/state/dev-platform/sessions` (or `--state-root`, or
`AI_SESSION_STATE`), owner-only:

- `manifests/<id>.json`: versioned manifest, replaced atomically under a per-session `flock`
  in `locks/`. Every write bumps `revision`.
- `handoffs/<id>.md`: a handoff you wrote, imported from a file or stdin (64 KiB limit).
  Import requires `--expect-revision`; a stale revision exits 3.
- `events/<id>/*.json`: immutable, uniquely named event files.
- `sources.json`: last scan result per native source (`ok`, `truncated`, `error`).

Files starting with `.` are partial writes and are ignored. Deleting `manifests/` and
rescanning rebuilds the index; titles set with `title` and handoffs live only here, so keep
the directory if you want them.

A session ID is the runtime plus a digest of the native store and native ID, so the same
native ID in two Codex homes or two OpenClaw agents never collides.

### What each adapter reads

| Runtime | Source | Fields kept |
|---|---|---|
| Codex | `state_*.sqlite` `threads`, read-only, schema checked; `session_index.jsonl` fallback | id, rollout_path, cwd, title/name, git_branch, archived, updated_at |
| Claude Code | `projects/*/sessions-index.json`; else the first 40 lines / 256 KiB of each transcript | sessionId, cwd/projectPath, gitBranch, timestamp/modified, customTitle |
| OpenClaw | `openclaw sessions --all-agents --limit all --json` | agentId, key, sessionId, store path |
| VS Code | `workspaceStorage/*/workspace.json`, `chatSessions/*.json` | folder, sessionId, customTitle, dates |

Message bodies, prompts and request content are never stored. Codex homes are `~/.codex`
(owner `user`) and `~/.openclaw/agents/*/agent/codex-home` (owner `openclaw`); no home is
inferred from a transcript field. VS Code files that are not a recognized chat session
object are indexed with status `unsupported`.

### Status

Status is `unknown` unless native evidence says otherwise: `stale` when a complete scan of
its source no longer finds the record, `unsupported` for unrecognized formats. File
modification time is never taken as proof a session is running. A source that errors or
is truncated (by `--limit`, default 500 per source, or OpenClaw `hasMore`/`errors`) leaves
existing entries as they were and is reported in the scan output.

### Resume

`resume` prints a JSON plan with the exact argv, working directory, environment and a
shell-quoted `command`; it runs nothing by default.

- Claude Code: `cd <cwd> && claude --resume <id>`.
- Codex (`~/.codex` only): `cd <cwd> && CODEX_HOME=<home> codex resume <id>`.
- OpenClaw, VS Code chat and OpenClaw-managed Codex sessions: exit 2 with the native place to
  resume. Never reported as success.

A native ID that is not a plain identifier, or a missing absolute cwd, makes the session
unsupported. `--execute` runs only a supported plan, only from an interactive terminal, with
argv and no shell. There is no pause, steer or cancel.

## ai-env doctor

```
ai-env doctor [--json] [--probe-laya] [--home DIR]
```

Read-only. Reports, with states `ok`, `missing`, `unavailable`, `unverified`, `broken`:

- whether `claude`, `codex`, `openclaw`, `code`, `gh`, `git`, `jq`, `python3`, `laya` are on PATH;
- broken symlinks in `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, and links whose
  name matches a platform skill but point somewhere else (divergent);
- whether `bin/check` exists;
- Laya: `*laya*.plist` launch configurations by name, and a single loopback listener (via
  `lsof`; `unverified` without it). `--probe-laya` runs `laya --help` with a 10 second bound;
  without it the probe is `unverified`.

It never installs, restarts, edits configuration or prints credentials or config contents.
