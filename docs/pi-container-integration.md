# Pi through containerized account access

Owner requirement: Pi must use the account environments selected by the account
service. The initial named-agent preference is OpenAI Apple. A separate host Pi
login is not the target. This document is a reviewed integration proposal, not
evidence that the containers are running or that authentication is complete.

## Verified compatibility and missing pieces

The candidate image uses Node 24.14.0. Pinned Pi 0.87.1 requires Node >=22.19.0,
so the declared Node versions are compatible. The candidate image currently
includes a source change to install Pi 0.87.1 alongside OpenRig, Claude Code and
Codex. The Pi addition has not been built/deployed; the running coding-worker
image is not Pi acceptance evidence. The image does not yet include the
dev-platform role resources. Its current mounts expose the account's persistent
home and a workspace, not the canonical conversation, journal or history inputs.

Pi's documented provider login stores credentials in its selected `auth.json`.
Its ModelRuntime accepts an explicit auth path. The inspected pinned distribution
does not provide an established automatic import from `CODEX_HOME/auth.json` or
Claude's native credential file. Native-client authentication, Pi authentication,
account identity and subscription entitlement are separate checks, even within
one account environment. Do not invent a token conversion layer to hide this.

Source: [Pi provider authentication](https://pi.dev/docs/latest/providers), the
pinned Pi package manifest/ModelRuntime, and the current container Dockerfile,
Compose mounts and entrypoint. No credential contents were inspected for this
review and no authentication or billable request was made.

## Proposed native execution path

1. The existing account service selects a verified eligible environment for
   `client=pi` and the requested conversation. Unknown usage remains unknown;
   worker login success does not prove Pi availability. OpenAI Apple is the
   initial preference, not a fact inferred from a container name.
2. The same pinned account image includes Pi and the committed platform resources.
   Avoid an additional model gateway, credential broker or always-on Pi daemon.
   Pi's native auth/config lives under that environment's persistent home;
   supported native authorization there may still be necessary when the owner
   returns. Keep each client's credential format intact.
3. The account service starts the bound terminal through the OS-lock exec boundary
   inside the selected environment. The role/runtime/terminal components accept
   its explicit model runtime and paths. Account attribution must be verified
   separately from the stored account reference.
4. The terminal uses Pi's native interaction, tools and session lifecycle. OpenRig
   remains the control surface for coding workers; Pi does not become a second
   seat scheduler. Ordinary native Claude/Codex use remains available.

## Storage and capabilities

Keep one canonical conversation home independent of which account executes it.
Mount that specific home at a stable container path; acquire its lock there and
keep native Pi files under its `native/pi` directory. Do not create four copies
of a conversation under four account homes. Cross-account handover must preserve
the conversation but explicitly associate the successor native session. Native
workspace paths and their host mappings must remain resolvable on resume.

Iztac gets the explicitly selected project/worktree. Morty gets a neutral
conversation workspace and only the journal/task resources needed for the task.
Neo gets an explicit system resource or project. Being in an account container
must not silently grant all roles a coding-project context. Read-only preserved
history can be mounted by role, retaining the expected SQLite layout without
mounting unrelated histories or the entire original home.

Containerization changes available tools. Host applications, macOS services and
hardware access are not automatically available inside it. Inventory and test
the actual Morty/Neo capabilities before declaring parity. If host-side execution
is required, use a supported explicit interface for that capability; do not
silently mount the whole home, expose the Docker socket or invent a model proxy.
This capability placement remains a design/acceptance item, not a settled claim.

## Acceptance order

- Add Pi/resources through the account task's maintained image procedure and
  prove the pinned binary plus role loader run in the real image.
- Establish supported native Pi authentication in the selected account
  environment, then verify actual account identity and intended billing access.
- Run a real terminal conversation and tool call against explicit mounts.
- Stop/recreate the environment and resume the same conversation/native history;
  prove concurrent writers are refused on the actual mounted filesystem.
- Verify relevant journal, history, search and host-operation capabilities.
- Demonstrate a checkpointed handover to another verified account without
  relabeling the old native session or copying its credentials.

The macOS offline PTY and flock tests are useful component evidence, not evidence
that Docker Desktop bind mounts, container restart or cross-environment handover
already satisfy these checks. Leave authentication/approval steps pending while
the owner sleeps. Do not build or launch around another task's sandbox denial.
