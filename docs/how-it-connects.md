# How everything connects

A map of the AI setup on this machine, written for the person who uses it. Read the
first two sections and you can use the whole thing. The rest is reference.

## The five words

**Account.** One subscription you have logged into. There are four:

| Account | Provider | Plan | Where its files live |
| --- | --- | --- | --- |
| `anthropic-gmail` | Anthropic, Claude Code | Max | `~/.claude` (the machine default) |
| `openai-apple` | OpenAI, Codex | Pro Lite | `~/.codex` (the machine default) |
| `anthropic-apple` | Anthropic, Claude Code | Max | `~/.local/share/dev-platform/accounts/anthropic-apple` |
| `openai-gmail` | OpenAI, Codex | Pro Lite | `~/.local/share/dev-platform/accounts/openai-gmail` |

**Home.** The folder an account's files live in: its login, its settings, its history of
past sessions. Two accounts use the folders Claude and Codex create by default. The other
two have their own separate folders, so they never mix. A home is not a project; it is the
agent's own memory and identity, wherever the project happens to be.

**Seat.** One coding agent, running in one terminal window, working in one folder. A seat
is either Claude Code or Codex, and since today a seat can be told which account to be.

**Rig.** A named group of seats. A rig with one seat is the normal case. A rig with four
seats is a team. OpenRig ships templates for teams.

**OpenRig.** The program that starts, watches and stops seats. It runs as a background
service on this machine, called the daemon, and it has a full-screen dashboard you open
in your terminal. It uses tmux underneath, which is why every seat is a tmux window.

That is the whole vocabulary. Everything below is these five things arranged.

## The map

```
   you, in a terminal
        |
        |  dev-workspace            ai-usage            ai-account / ai-profile
        v                             v                        v
   +--------------------+     +----------------+     +----------------------+
   |  OpenRig dashboard |     | usage readout  |     | account bindings and |
   |  (rig tui)         |     | all 4 accounts |     | home provisioning    |
   +--------------------+     +----------------+     +----------------------+
        |                             ^                        |
        v                             |                        v
   +--------------------+             |              +----------------------+
   |  OpenRig daemon    |-------------+              | ~/.config/dev-platform|
   |  port 7433         |  seat status line cache    |   accounts.json      |
   +--------------------+                            | (which account has   |
        |                                            |  which home)         |
        | starts seats in tmux                       +----------------------+
        v
   +----------+ +----------+ +----------+ +----------+
   | seat     | | seat     | | seat     | | seat     |
   | claude   | | codex    | | claude   | | codex    |
   +----------+ +----------+ +----------+ +----------+
        |            |            |            |
        v            v            v            v
     account A    account B    account C    account D   (each seat reads and
     home         home         home         home         writes only its own)
```

The one arrow that matters: a seat is bound to exactly one account home. It logs in as
that account, it consumes that account's quota, and its history is written into that home
and nowhere else.

## What OpenRig writes into your project folder, and why

When a seat starts in a folder, OpenRig places three small files there:

- `.claude/settings.local.json`: tells Claude to run OpenRig's status line, so the daemon
  can watch context usage.
- `.openrig/context-collector.cjs`: that status line script.
- `CLAUDE.md` for Claude, `AGENTS.md` for Codex: guidance blocks added to the file, or the
  file created if it is missing. They tell the agent which seat it is and how to behave.

This is OpenRig treating the folder as the seat's workspace. It is harmless in a scratch
folder or one of your own projects. It is the reason the launcher refuses to start a seat
directly inside a professional repository checkout: those files would show up in someone
else's git status.

For project work the rule is one seat per working branch. The control seat and the Codex
overseer run from an engagement folder outside the repository. Each worker seat runs in the
worktree the loop cut for its issue, and is removed before its branch is folded, which puts
the guidance files back. `docs/rig-working-branches.md` has the commands.

## Day to day

**See how much you have left.** Nothing changes.

```bash
ai-usage
```

Codex numbers are live. Claude numbers are a recent reading with an age, because Anthropic
exposes usage only inside a running session; a status line captures it as it renders.
An account that has not been used since the collector was installed reads as unknown, which
is the truth, never zero.

**Open the dashboard.** Nothing changes. Press `?` inside it for every command.

```bash
dev-workspace
```

**Start one seat on a chosen account.** Always plan first; it refuses an account that is
out of quota or not verified, and it launches nothing.

```bash
dev-workspace plan claude --account anthropic-apple --cwd /path/to/folder
dev-workspace start claude --account anthropic-apple --cwd /path/to/folder
```

Each account gets its own rig name, so two accounts never collide. Reusing a rig resumes
its original session in its original folder.

**Start a team from a template.** List the templates, preview one, and launch it:

```bash
rig specs ls
rig specs preview conveyor
rig up conveyor --cwd /path/to/folder
```

To put each seat of a team on a different account, copy the template's `rig.yaml`, add
`config_home: <that account's home>` under the seats you want pinned, change `local:`
agent references to `path:/absolute/...`, and `rig up` your copy. A seat without
`config_home` uses the machine default for its runtime.

Templates deliver their role briefs by typing text into each agent on startup. If you want
silent seats, point the members at the platform's own agent, which sends nothing:
`path:~/.local/share/dev-platform/current/integrations/openrig/agents/control`.

**Attach to a seat, detach, stop a team.**

```bash
tmux attach -t <seat-name>        # Ctrl-b then d to detach
rig down <rig-name>               # stops every seat, keeps a snapshot
```

## Where things are stored

| What | Where |
| --- | --- |
| Which account has which home | `~/.config/dev-platform/accounts.json` (no secrets) |
| The four account homes | see the table at the top |
| The platform commands | `~/.local/bin/*` -> `~/.local/share/dev-platform/current/bin/*` |
| The activated platform release | `~/.local/share/dev-platform/current` -> `releases/<commit>` |
| OpenRig itself | `~/.local/share/dev-platform/openrig-runtime/app` (patched), `app-stock-cc75efdd` (original) |
| OpenRig's state and database | `~/.openrig` |
| Per-account rig specs the launcher generates | `~/.local/state/dev-platform/openrig/` |
| Usage readings | `~/.local/state/dev-platform/usage/<account>.json` |
| Pi role conversations | `~/.local/state/dev-platform/sessions/conversations/` |

## What was changed on this machine, and how to undo each

- **OpenRig is a local fork.** Build `0.5.14 (60f98ffb)` adds the per-seat `config_home`
  field. Stock 0.5.14 is parked beside it. Undo: swap the two `app` directories and restart
  the daemon. Provenance and the upstream contribution notes are in the migration workspace.
- **The daemon runs outside OpenClaw.** It used to inherit OpenClaw's environment, including
  a proxy URL that no longer exists. It now starts from a clean environment. Undo: nothing to
  undo; starting it from an OpenClaw shell would reintroduce the problem.
- **The tmux server was scrubbed.** Its global environment carried that same dead proxy, so
  every new seat inherited it. The launcher now removes such variables before every start,
  and `ai-env doctor` reports them.
- **The two isolated homes were equipped.** Guard hooks, global instructions, the usage
  status line, and the answer to Claude's first-run Chrome dialog. `ai-profile plan <account>`
  shows what a home is missing; `ai-profile apply <account>` fixes it, idempotently, never
  touching a credential.
- **A platform release was cut and activated.** `current` points at it. Undo: point `current`
  back at the previous release directory.

## Known limits

- **Claude usage is a snapshot.** No command can ask Anthropic for it; only a running session
  reports it. Expect an age on every Claude number.
- **The dashboard shows Codex seats as "needs attention".** OpenRig judges a seat by the
  terminal's foreground process, and on this machine `codex` is a Node wrapper, so the check
  reads the wrapper instead of the real binary. Claude seats verify correctly. Reported upstream.
- **A stopped rig cannot be restored with `rig up --existing`.** The harness never relaunches.
  This is stock OpenRig behavior, reproduced with and without account pinning. Start a fresh
  rig instead.
- **A seat launch can drop the usage status line from its account home.** Rerun
  `ai-profile apply <account>` afterward if the Claude number for that account stops updating.

## When something looks wrong

| Symptom | Cause | Fix |
| --- | --- | --- |
| Daemon dies at start with `ERR_DLOPEN_FAILED` | Wrong Node on PATH | Start it through `dev-workspace` or `bin/rig`, which use the pinned Node 24 |
| A new seat sits on "Connection refused, retrying" | Inherited dead proxy URL | `ai-env doctor` shows it; `dev-workspace start` removes it; or `tmux set-environment -g -u ANTHROPIC_BASE_URL` |
| A seat times out after 30 seconds, never interactive | Claude's first-run Chrome dialog in a fresh home | `ai-profile apply <account>` records the answer |
| `ai-account status` says every account is unverified | Run from inside a Claude desktop session, which sets a provider variable | Run it from a plain terminal |
| A Codex seat shows "needs attention" but works | The foreground-process check, see Known limits | Ignore, or report upstream |
