# Local account environments

Candidate deployment for four account-pinned OpenRig hosts. One pinned image, four instances, no credential swapping or proxy. Account environments own execution; project/conversation records own the work. **Image build and two OpenAI environment runtime checks passed on Docker Desktop (Linux arm64). Native account login, worker messaging and recovery remain unverified.**

The source image now also includes Pi 0.87.1. That addition has not been built or
deployed: earlier image checks cover the coding-worker image without Pi. The
runtime checker now requires Pi and will reject an older image. Do not recreate
an environment during an active login or worker session simply to satisfy this
check. Pi's native configuration uses the selected account's persistent home;
this does not import or convert Codex/Claude credentials. Canonical conversation
mounts, role resources and account-service launch integration remain necessary.
See [Pi integration](../../../docs/pi-container-integration.md).

## Prepare and run

Docker Engine and Compose must be available. Preparation creates private host directories and opaque control tokens, preserving existing tokens on retry. It never copies provider credentials or edits the active OpenRig host registry.

```sh
python3 integrations/openrig/containers/prepare.py /absolute/private/account-environments
docker compose --env-file /absolute/private/account-environments/compose.env -f integrations/openrig/containers/compose.yaml config --quiet
docker compose --env-file /absolute/private/account-environments/compose.env -f integrations/openrig/containers/compose.yaml build
```

Start only `openai-apple` and `openai-gmail` for the first simultaneous-account/recovery acceptance, then the two Anthropic services. Use `up -d SERVICE...` with the same Compose/env-file arguments. No automatic restart or worker dispatch is configured. The daemon is foreground under Docker's init; no kernel agent is implicitly requested through `rig daemon start`.

Each service publishes container port 7433 to localhost ports 17433–17436, in this order: anthropic-apple, anthropic-gmail, openai-apple, openai-gmail. The OpenRig listener binds its container network interface; only its localhost host port is published. Each account has a separate Docker network. In OpenRig 0.5.14 the bearer token gates selected routes (including transport), not the whole API: ordinary rig reads and other control routes are not globally authenticated. Treat these as trusted local-user endpoints, not hardened remote API hosts. Do not publish the ports on all host interfaces.

## Runtime checks

```sh
python3 integrations/openrig/containers/check.py /absolute/private/account-environments openai-apple openai-gmail
```

This checks actual containers, pinned versions, non-root execution, separate networks, declared mounts, localhost publication, health and transport rejection of missing/other-account tokens. It does not prove native login, worker startup, message delivery or resume.

## Native login and launch

Use Compose `exec` to enter the chosen running environment. For Codex, run `codex login --device-auth`; for Claude, start `claude` and complete its native `/login` flow. The human completes browser authentication. Never paste credentials into chat, the image, Git, or Compose configuration.

Verify native identity for each account before launching a Rig. No login is assumed from the service name. The persistent home holds `.codex`, `.claude`, `.openrig`, native session histories and tmux-related state. Control tokens live separately under that account's `secrets` directory. Processes use the host user's numeric UID/GID so private bind-mounted files remain writable without running as root.

Install the selected project checkout or worktree into each account's `workspace` directory, visible at `/workspace`. Do not mount all of the Mac home. A linked Git worktree whose common Git directory is outside this mount needs that directory explicitly accessible; prefer an independent checkout for initial acceptance. Different account workers must not write the same checkout.

`hosts.candidate.json` contains proposed HTTP hosts and bearer-file references, not secrets. After endpoints pass verification, register each with native `rig host add` using its `--id`, `--transport http`, `--url` and `--bearer-file`. Do not replace an existing hosts registry wholesale. Use explicit host IDs when sending messages or launching work.

## Filesystem/session integration still required

Record the environment host ID, project, actual host/container workspace mapping, native runtime and native session ID against the existing conversation. The persistent home is native software storage; the conversation index references it rather than copying transcripts into a second live store. Container paths such as `/workspace` are not host paths: discovery/resume must translate through an explicit environment binding. Use `ai-session scan --no-openclaw --environments-root /absolute/private/account-environments` to scan the persistent native homes. The index translates the two declared mount paths, retains container paths, reports unavailable homes honestly, and refuses host-native resume of these OpenRig-owned records. Actual host-targeted Rig resume and verified seat/occupant associations remain pending.

No automatic usage-based routing is implemented by this deployment. Accounts stay pinned; choose a host for new work and use a checkpointed handoff for changing execution environments. Pi must use these same account environments through the account service, while retaining its own role/session lifecycle. Host-level Morty tools still need explicit capability integration.

## Acceptance before activation

- Build exact image and confirm CLI/runtime versions.
- Verify two simultaneous same-provider logins resolve to distinct expected accounts.
- Launch an appropriate one-seat Rig in each, then verify actual native identity and messages.
- Recreate a container using the same directories and verify history plus native resume.
- Register the host and verify host-targeted inventory, messaging and transcript reads.
- Bind real worker sessions into the existing conversation index with correct path mappings.
- Repeat for the other provider. Only then enable all four for Iztac.

Do not delete environment directories or credentials when stopping/recreating containers. Retain their history in the preservation/backup process. No old OpenClaw state is removed by this deployment.
