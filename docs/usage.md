# Usage across all four accounts

`bin/ai-usage` shows quota for all four accounts (`anthropic-apple`, `anthropic-gmail`,
`openai-apple`, `openai-gmail`) in one table. Add `--json` for the full structured view.

Run it with the same environment guard every other native command in this platform needs,
because the desktop app sets provider-override variables the account probes deliberately
refuse:

```
env -u ANTHROPIC_BASE_URL -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT python3 bin/ai-usage
```

## What is live and what is cached

**Codex (`openai-apple`, `openai-gmail`) is live.** The native Codex app-server exposes
`account/rateLimits/read` over stdio JSON-RPC, and `lib/ai_ecosystem/accounts.py` already
probes it on every call. `bin/ai-usage` reuses that same probe (through
`environment_service.host_observations`) — it does not reimplement it. Every Codex row you
see was queried the moment the command ran; its freshness always reads `live`.

**Claude (`anthropic-apple`, `anthropic-gmail`) is cached, and that is a hard limit, not a
bug.** `claude auth status --json` — the only thing the account probe can ask a Claude
native profile without opening a paid session — does not expose quota at all. There is no
API to poll for it. The one real signal is Claude Code's own status line: on every render,
Claude Code hands the status line command a JSON payload that includes a `rate_limits`
object for subscription accounts (five-hour and seven-day windows, each a used-percentage
and a reset time). `integrations/claude/usage-collector.py` is installed as that status line
command; it captures the reading and caches it to
`~/.local/state/dev-platform/usage/<account-id>.json`.

That means a Claude reading only updates **while a session is actually running in that
account's home**. If no session has run there since the account was set up, there is no
reading — not a stale one, none at all. If a session ran two hours ago and none since, the
reading is two hours old. `bin/ai-usage` never queries Claude for usage; it only ever reads
whatever the most recent session happened to leave behind.

## How the collector gets installed

`integrations/claude/usage-collector.py` does not install itself. The account-provisioning
tool (owned by a different task) registers it as the `statusLine` command in each Claude
account's native settings, invoked as:

```
python3 <platform-root>/integrations/claude/usage-collector.py --account <account-id>
```

This document does not claim that wiring exists yet for any given account — only that this
is the contract the collector honors: that exact invocation, writing to that exact cache
path, 0600 file inside a 0700 directory.

## What the collector will and will not do

- It reads the status line JSON payload from stdin and looks only at `rate_limits.five_hour`
  and `rate_limits.seven_day` (each a `used_percentage` number and a `resets_at` Unix
  timestamp — the field names documented inside the installed Claude Code binary and
  corroborated by OpenRig's own equivalent collector).
- It writes only the account id, a capture timestamp, and those two windows to the cache.
  Nothing else from the payload — not the session id, not the transcript path, not the
  working directory — ever reaches the cache.
- If the payload does not parse, or carries no usable rate-limit window, it changes nothing:
  an old real reading is never overwritten with a blank one, because "no data this render"
  does not mean "the account has no usage."
- It cannot crash a Claude session. Any failure — bad JSON, a write error, a missing flag —
  prints one harmless status line and exits 0, always.

## A second source: OpenRig seats

A Claude seat launched by OpenRig runs OpenRig's own status line, not the platform's,
because OpenRig writes a project-level `.claude/settings.local.json` into the seat's
folder and project-level wins. Those seats therefore never write the platform cache.
`ai-usage` reads OpenRig's seat-keyed cache as well (`~/.openrig/state/provider-usage/`,
one file per seat) and attributes each reading to an account by the seat's home: a seat
pinned with `config_home` belongs to the account registered at that home; an unpinned
seat ran in the daemon's default home, which is the account bound as `native_default`.
The daemon database is opened read-only for that mapping and nothing is written to it.

Across both sources the freshest reading that still has a live window wins, and the row
names its source (`status line cache` or `OpenRig seat <name>`). A seat whose runtime is
Codex contributes nothing, since Codex usage is queried live. Stock OpenRig 0.5.14
discarded every window because it expected a string reset time and Claude sends a number;
the patched runtime on this machine normalizes both, and the fix is offered upstream.

## Reading the table honestly

Every row carries an explicit `source` and `freshness`, not just a number:

| Freshness reads | Meaning |
| --- | --- |
| `live` | Queried the native probe just now (Codex only). |
| `status line cache, N minutes old` | A real captured reading, N minutes old (Claude). |
| `stale: status line cache, N minutes old` | Same, but old enough (30+ minutes) that it should not be treated as current. |
| `unknown: no reading yet` | No cache file exists. Not zero usage — no observation at all. |
| `unknown: last reading's windows have since reset` | The cached window's `resets_at` has passed; showing that old percentage against a window that already reset would be a fabricated number, so it is dropped instead. |
| `unknown: account not verified` | The account is not bound, or its native identity does not match the binding; no cached reading is shown even if a cache file exists, because it may belong to a different login than the one currently in force. |

**Unknown is unknown. A stale reading is not a current one.** `bin/ai-usage` never
interpolates, never estimates, and never substitutes zero for "no data." If you see a
percentage in this table, it is either a live probe result or a real number that Claude Code
itself reported at the timestamp shown next to it — nothing in between.
