# Host-native account service

`ai-environment` defaults to host execution. Account profiles change native client
configuration, not process HOME, filesystem visibility or project cwd. No daemon,
model proxy, credential conversion or automatic turn replay is involved.

```sh
ai-environment status --table
ai-environment choose codex
ai-environment plan --client codex --provider openai --cwd /absolute/project
ai-environment run --client codex --provider openai --cwd /absolute/project --
ai-environment run --client claude --provider anthropic --preferred-account anthropic-apple --allow-unknown-quota --cwd /absolute/project --
```

Automatic selection uses the greatest remaining observed Codex core quota among
verified native profiles; exhausted, unavailable and unknown-quota profiles are
not automatic fallbacks. Claude's native auth status does not expose quota, so
its use requires an explicit account and unknown-quota override. An explicitly
requested unavailable account never silently switches to another. Status is a
fresh observation, not a reservation or guarantee against concurrent usage.

The existing private account registry remains authoritative:
`~/.config/dev-platform/accounts.json`. `--registry` can select another explicit
registry. Container enrollments and logins do not enroll host-native profiles.

## Native profiles and sign-in

```sh
ai-environment profile --client codex --account openai-apple --prepare
ai-environment profile --client claude --account anthropic-apple --prepare
ai-environment profile --client pi --account openai-apple --prepare
ai-environment profile --client pi --account openai-apple --check
```

Profile output provides the native sign-in argv and environment. Apply that
environment only to the selected command in a trusted local terminal. Complete
each native sign-in there; do not copy credentials between applications or
containers. Codex profiles explicitly request file-based native credential
storage. Pi profiles use `PI_CODING_AGENT_DIR`; native Pi uses `/login`.

Native worker identity enrollment remains:

```sh
ai-account bind openai-apple --home /absolute/native/config-root --expected-email YOUR_ACCOUNT_EMAIL
```

Binding checks the native client's reported identity before saving. Different
named accounts for the same provider cannot bind the same identity or profile.
Do not use a default-profile binding to claim independent credential storage.
Claude macOS credential isolation still requires real two-profile verification;
directory preparation alone is not proof of independent Keychain behavior.

Pi's native `auth check --no-refresh` only establishes local configuration. In
the pinned runtime, even expired synthetic OAuth credentials can produce native
`ready`. The service therefore reports `configured` plus capability `unverified`,
and refuses Pi launch until actual identity/authentication verification is
integrated. Its check does not refresh credentials, print tokens or infer access
from Codex/Claude logins. Profile preparation never changes existing bindings.

## Launch and continuity contract

Plans return `version: 1`, `execution_kind: host`, selected account, capability,
quota and observation time, actual host cwd, plus a profile object. `profile.home`
is the absolute native **client configuration root**, never process HOME.
`profile.environment` contains only the appropriate client directory override;
an existing explicit `native_default` binding has no override. `identity_ref` is
a fingerprint of the enrolled identity, not a credential. History remains owned
by the native client under its bound profile; adapters resolve version-specific
locations. Plans contain no provider tokens.

The run command revalidates native identity/configuration immediately before
replacing itself with the native client. It inherits the terminal and native exit
behavior; it does not supervise or replay the session. Resume/fork commands
require `--preferred-account` naming the original binding. Example:

```sh
ai-environment run --client codex --provider openai --preferred-account openai-apple --cwd /absolute/project -- resume NATIVE_SESSION_ID
```

The native client validates its own session identifier. This service does not
yet prove an indexed conversation-to-native-session binding for arbitrary direct
resume commands. Pi conversation locks and native role bindings remain its
consumer's responsibility.

OpenRig plans expose candidate profile information but refuse launch until its
adapters persist and propagate profile identity through launch, history lookup,
resume and fork. A PATH wrapper cannot substitute for those changes. Existing
Rig daemons, desktop clients and live workers are not switched by this service.

Docker worker inspection remains available explicitly:

```sh
ai-environment --execution-kind container --root /absolute/account-environments status
```

Host failures never fall back to Docker. Existing container credentials and
histories remain untouched. Profile separation is not an OS security sandbox.
