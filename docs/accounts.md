# Account selection

`ai-account` is a small **new-launch selector**, not a credential broker or a universal
hot-switch. Authentication stays in each tool's native home and OS credential store.
It does not copy tokens, reset login, change billing, adopt Desktop sessions, start
workers, or run a daemon. No default account is inferred and no fallback is automatic.

## Ordered workflow

1. `ai-account monitor --table` gives a compact native-terminal view; omit `--table`
   for JSON integration output. It shows five stable IDs in order: `anthropic-gmail`,
   `anthropic-apple`, `openai-gmail`, `openai-apple`, `zai`. Unknown is not zero.
2. `ai-account login-plan anthropic-apple` describes the isolated home and native
   command. Complete sign-in in a trusted local browser/terminal, never by passing
   passwords, tokens, or login codes through chat. This command itself does not log in.
3. Configure the isolated home's platform rules, hooks and shared skills before
   using it for engineering. Native homes include configuration as well as login;
   do not copy credential files or blindly copy settings containing secrets.
4. Bind the existing native home after checking its identity:

   ```sh
   ai-account bind anthropic-gmail --home ~/.claude --native-default --expected-email owner@example.invalid
   ai-account bind openai-gmail --home ~/.codex --native-default --expected-email owner@example.invalid
   ```

   `--native-default` leaves both profile environment variables unset and is accepted
   only for the actual default home. Setting `CLAUDE_CONFIG_DIR=~/.claude` is not
   assumed equivalent to leaving it unset: native identity checks proved different
   behavior on the installed client. Omit this flag for separately logged-in homes.

   Replace the example email with the intended login identity (Apple relay identity
   for an Apple login), not the forwarding inbox. A mismatch refuses the binding.
   The private registry is `~/.config/dev-platform/accounts.json`, mode 0600. It
   contains home paths and expected identities, never credentials.
5. `ai-account plan anthropic-gmail` reports the scope and environment conflicts.
   `ai-account select anthropic-gmail` verifies identity and saves the default for
   subsequent `ai-account run` launches and compatible future development-loop
   workers. `ai-account selected` reads that same default without probing or changing
   anything. Existing sessions do not change.
6. `ai-account run -- --name 'fix(parser): Handle empty input'` starts Claude using
   the selected native home. A Codex selection starts Codex with the same literal
   argument forwarding; supply that harness's arguments. `run --account ID -- ...`
   pins one launch without changing the default. Native configuration/auth overrides
   in arguments or inherited environment are rejected, not silently removed.

Run this selector from a clean trusted host environment. An OpenClaw process may
inherit provider keys or proxy settings; those conflict and must not silently override
a subscription selection. `plan` reports variable **names only**. It never prints
their values. Native config routing overrides are also rejected conservatively;
review them rather than bypassing the check. Binding a native home does not certify
all engineering configuration inside it or override the platform's execution policy.

Directory-changing arguments (`--cd`, `-C`) and attached configuration/profile flags
are refused: start the selector in the intended project so that directory is checked.
The configuration scan is a conservative observed-conflict guard, **not a security
sandbox or a complete evaluator** of native plugins, includes, system settings or
credential helpers. Native client security and the existing platform guard remain
responsible for those boundaries. New profile homes need their own native setup.

## Monitor and limitations

### Existing development-loop workers

The loop resolves the same `ai-account select` default for future worker attempts,
including the loop's `resume` (which starts a new conversation). An explicitly
requested `LOOP_ACCOUNT_ID=anthropic-gmail` or `anthropic-apple` overrides that default
for one invocation. `go` verifies the native identity before changing steer or creating
a worktree. Dispatch still uses the existing supervisor, limits, guard and ledger;
the account selector only wraps the native launch. Each attempted launch appends
its stable account ID to `workers/<issue>.account.jsonl`. This is launch intent,
not proof the worker completed; inspect its exit/log evidence as usual.
Unreadable or malformed selection state stops dispatch; it never falls back to an
unbound launch.

No selected default and no override means unchanged legacy behavior, not a guessed
account. The selected default applies only to future attempts. OpenAI/z.ai selections
fail clearly because this loop currently has only a Claude worker adapter. Existing
workers remain untouched. Do not set this variable globally unless that default is
explicitly intended; prefer the owner-directed loop invocation.

`status ID` and `monitor` are timestamped, one-shot native observations. Claude uses
`claude auth status --json`; it cannot establish remaining allowance, so quota stays
unknown and the user can inspect native `/usage`. Codex uses a short-lived stdio
app-server, `account/read` with `refreshToken:false`, and `account/rateLimits/read`.
No model thread/turn is created. Quota fields are whitelisted.
Independent quota pools retain bounded native pool IDs and primary/secondary window
labels; they are not added together into an invented total. Raw auth responses,
native stderr and credential contents are never relayed. The native client can write
its ordinary diagnostics and refresh according to its own implementation; this tool
never reads or rewrites credential files. Receipt totals and quota percentages are
not actual spend, renewal status or the number of subscriptions actively billing.

| Surface | What changes |
| --- | --- |
| Claude Code / Codex through `ai-account run`, compatible loop workers | New process gets its bound native home; current processes unchanged |
| Existing CLI launches bypassing this selector | Unchanged; cannot claim ecosystem-wide propagation |
| OpenClaw | Native personal-account default is separate; `models accounts use` affects new sessions only and requires signed-in-person access. Connected accounts supports OpenAI API/ChatGPT but Anthropic API keys, not Claude subscription tokens |
| OpenRig 0.5.14 | Both Claude and Codex seats exist; provider-switch execution is not wired. Its strict member schema lacks per-seat environment fields and CODEX_HOME is daemon-wide, so safe per-seat profile injection is not claimed |
| Claude Desktop / ChatGPT apps | Native app login and running sessions unchanged |
| z.ai | Visible planned provider, blocked until plan/authentication/protected delivery are verified |

A safe broader rollout must bind the same verified identity in each supported
runtime, report pending surfaces and checkpoint active work before explicit handoff.
Use OpenClaw Settings → Profile → Connected accounts, and the chat model menu's
Account control where supported. Its managed Codex auth bridge is separate from a
personal CLI home; a CLI identity check does not establish the OpenClaw session's
account. Never substitute Anthropic API billing for a requested Max subscription.
Do not wrap this limitation in a success message or overwrite shared auth underneath
workers. This selector is a foundation for that rollout, not an atomic global switch.

## Native contracts

- [Claude authentication](https://code.claude.com/docs/en/authentication):
  `CLAUDE_CONFIG_DIR` scopes configuration and the macOS Keychain entry.
- [Codex advanced configuration](https://developers.openai.com/codex/config-advanced):
  `CODEX_HOME` scopes config, authentication and native state.
- [Codex app-server](https://developers.openai.com/codex/app-server): account/read
  and account/rateLimits/read. Installed API behavior must be verified, not assumed
  from a newer documentation version.
- [OpenRig getting started](https://www.openrig.dev/docs/getting-started): native
  Claude and Codex seats, distinct from provider account rebinding.
