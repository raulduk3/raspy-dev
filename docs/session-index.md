# Session index and environment doctor

`bin/ai-session` keeps a local, reconstructible index of Claude Code, Codex, OpenClaw and
VS Code chat sessions. `bin/ai-env doctor` reports on the local toolchain. Both are local only:
no daemon, scheduler or database service, and neither writes native client storage.
The opt-in Laya probe makes one local inference call through the installed helper, which
may append its own metadata-only audit record; the default doctor makes no model call.

## ai-session

The scanner also reads native Claude/Codex home locators from the non-secret
`~/.config/dev-platform/accounts.json` registry. Shared/default homes are deduplicated;
isolated homes retain separate native identities. Missing stores remain unavailable,
not deleted. Discovery does not read credential files or verify the current account.
Claude resume plans for isolated stores include the corresponding `CLAUDE_CONFIG_DIR`.
Resume commands clear inherited `CODEX_HOME` and `CLAUDE_CONFIG_DIR` before applying
the recorded native home. Conflicting provider credential/routing environment
settings refuse resume; this prevents a terminal's unrelated login route from
silently changing a recovered session. This does not verify current login identity.

```
ai-session [--state-root DIR] scan [--limit N] [--home DIR] [--no-openclaw]
ai-session list [--json] [--runtime claude|codex|openclaw|copilot] [--limit N] [--search TEXT]
ai-session show ID
ai-session title ID TEXT [--expect-revision N]
ai-session handoff ID [--import FILE|- --expect-revision N]
ai-session resume ID [--execute]
```

`list` returns at most 20 matches by default. `--search` matches a case-insensitive
substring in title, native ID or working directory, never transcript content. `--limit 0`
explicitly requests all matches; JSON includes `total` and `has_more`. Text rows truncate
long titles and paths for readability; `show` retains the full metadata.

State lives under `~/.local/state/dev-platform/sessions` (or `--state-root`, or
`AI_SESSION_STATE`), owner-only:

- `manifests/<id>.json`: versioned manifest, replaced atomically under a per-session `flock`
  in `locks/`. Every write bumps `revision`.
- `handoffs/<id>.md`: a handoff you wrote, imported from a file or stdin (64 KiB limit).
  Import requires `--expect-revision`; a stale revision exits 3.
- `events/<id>/*.json`: immutable, uniquely named event files, published by fsync + atomic rename.
- `sources.json`: last scan result per native source (`ok`, `truncated`, `error`, `unavailable`).

Files starting with `.` are partial writes and are ignored. Deleting `manifests/` and
rescanning rebuilds the index; titles set with `title` and handoffs live only here, so keep
the directory if you want them.

A session ID is the runtime plus a digest of the native store and native ID, so the same
native ID in two Codex homes or two OpenClaw agents never collides.

### Titles are index-only

`ai-session title ID TEXT --expect-revision N` changes only this index's display override.
It does not rename a Claude, Codex, OpenClaw, VS Code or OpenRig conversation. `show` keeps
both the last observed native `title` and the local `title_override`; rescanning preserves
the override and native identity. Read the current revision before writing and do not
replace an owner-assigned title. Follow [Session naming](session-naming.md) for automatic
self-naming and supported native capabilities; the index is not a native rename API.

### What each adapter reads

| Runtime | Source | Fields kept |
|---|---|---|
| Codex | `state_*.sqlite` `threads`, read-only, schema checked; `session_index.jsonl` fallback | id, rollout_path, cwd, title/name, git_branch, archived, updated_at |
| Claude Code | `projects/*/sessions-index.json`; else the first 40 lines / 256 KiB of each transcript | sessionId, cwd/projectPath, gitBranch, timestamp/modified, customTitle, transcript/index paths, transcript_missing |
| OpenClaw | `openclaw sessions --all-agents --limit all --json` | agentId, key, sessionId, store path |
| VS Code | `workspaceStorage/*/workspace.json`, `chatSessions/*.json` | folder, sessionId, customTitle, dates |

Message bodies, prompts and request content are never stored. Codex homes are `~/.codex`
(owner `user`) and `~/.openclaw/agents/*/agent/codex-home` (owner `openclaw`); no home is
inferred from a transcript field. VS Code files that are not a recognized chat session
object are indexed with status `unsupported`.

### Status

Status is `unknown` unless native evidence says otherwise: `stale` when a complete scan of
its source no longer finds the record or a Claude index references a missing transcript, `unsupported` for unrecognized formats. File
modification time is never taken as proof a session is running. A source that errors or
is truncated (by `--limit`, default 500 per source, or OpenClaw `hasMore`/`errors`) leaves
absent entries unchanged and is reported in the scan output (successfully read records may
update during a truncated scan). A vanished previously discovered source is `unavailable`,
not evidence its records were deleted; existing manifests and handoffs remain untouched.

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
ai-env doctor [--json] [--probe-laya] [--home DIR] [--platform-root DIR]
```

Read-only. Reports, with states `ok`, `missing`, `unavailable`, `unverified`, `broken`:

- whether `claude`, `codex`, `openclaw`, `code`, `gh`, `git`, `jq`, `python3`, `laya-decide` are on PATH;
- missing canonical platform skills (directories containing `SKILL.md`) and broken symlinks in `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, and links whose
  name matches a platform skill but point somewhere else (divergent). Canonical source is
  `~/Dev/dev-platform`, not the doctor executable’s checkout; override with `--platform-root`;
- whether `bin/check` exists;
- Laya: parses `com.raulduk3.laya.plist` with `plistlib`, validating the laya-serve
  entrypoint, loopback host, port 18791, preload enabled, and one matching launch config.
  Checks TCP port 18791 with bounded `lsof`, counting distinct listener PIDs regardless of
  process name (the actual service can be Python). Missing `lsof` is `unverified`.
- `--probe-laya` invokes `laya-decide` with a fixed innocuous two-option JSON input and a
  20-second timeout. Only a valid shadow recommendation, with no automatic application
  and routing metadata, verifies inference. A helper-reported unavailable result is
  `unavailable`, not healthy. Recommendation quality always remains `unverified`; no
  default inference runs. Raw state, helper output, launch arguments and environment
  values are never printed.

It never installs, restarts, edits configuration or prints credentials or config contents.

## Cross-runtime conversations

`ai-session conversation` adds an explicit association above native sessions, in the same state root. Original transcripts are not moved or rewritten. Accounts do not define conversation identity.

```sh
ai-session conversation create --agent morty --title 'Personal planning'
ai-session conversation create --agent iztac --title 'Implement account controls' --project owner/repo --workspace /path/to/checkout
ai-session conversation create --agent iztac --title 'Explore a new project' --formation --workspace /path/to/formation
ai-session conversation create --agent neo --title 'Host maintenance' --resource local-host
ai-session conversation list
ai-session conversation bind CONVERSATION_ID INDEXED_NATIVE_ID --expect-revision REVISION
ai-session conversation show CONVERSATION_ID
```

Existing project names resolve to stable IDs through `~/.config/dev-platform/repos.conf`; `--repos FILE` selects another catalog configuration. The workspace must resolve to the same Git repository, including linked worktrees. Formation is an explicit temporary scope for a real directory before a catalog project exists. Morty cannot be project-bound; Neo needs an explicit system resource or project scope. No creation command launches a runtime.

Each conversation has `conversations/ID/session.json`, `handoff.md`, and a reserved `native/pi/` folder. Native associations stay in existing index manifests and survive scans. Binding checks the expected native-record revision and refuses reassignment to another conversation. Project/formation bindings require a matching observed native workspace. This keeps associations evidence-based but means unavailable historical workspaces need a separate migration/rebinding procedure.

These commands establish storage and association, not complete runtime lifecycle enforcement. The role launcher must still apply neutral/project cwd, resource isolation, native Pi session paths and account ownership. Formation-to-project promotion, explicit worker/successor relationships, relocated source identities and OpenRig execution bindings remain pending. A created conversation does not prove any of those behaviors.
