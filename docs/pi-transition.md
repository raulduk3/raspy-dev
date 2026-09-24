# Pi ecosystem transition

Status: implementation in progress. OpenClaw remains available. No retirement is authorized by a successful component check alone.

Priority correction: session ownership, scope and filesystem continuity come first. Follow [Shared session contract](session-context-contract.md) before expanding agent launches. Morty is personal and project-independent; Iztac requires a project or formation workspace; Neo starts with explicit system or project scope. Authentication alone is not readiness to migrate.

## Required acceptance

- Full original personal and agent records preserved; hashes and representative restoration verified. Live preliminary copies are not final quiescent archives.
- Morty, Iztac and Neo retain source-linked historical access and role boundaries.
- Shared skills/tools no longer depend on paths that retirement will remove.
- Pinned Pi runtime passes startup and real authenticated session checks; native sign-in stays native and credentials are not copied into project files.
- Iztac starts in an explicit project or project-formation workspace, with the shared development workflow.
- Rig opens in that engineering context; focused native code windows operate on the same tasks/worktrees.
- All four account profiles independently verified, with native account isolation. Existing sessions unaffected by new-launch selection.
- Account/session service connects to Rig and a human TUI: eligible accounts, usage observation age, assignments, concurrency, drain and checkpointed transitions.
- Rig owns team coordination; dev-platform retains engineering gates and primitives. Existing loops transfer ownership explicitly; no duplicate dispatch.
- One complete engineering task demonstrates account attribution, steering, takeover, verification, review and restoration.
- Personal integrations and explicitly authorized schedules tested individually.
- Reversible OpenClaw shutdown trial succeeds before removal; protected historical archive remains.

## Implemented in this branch

`integrations/pi/package.json` and lockfile pin Pi 0.87.1; install with `npm ci --ignore-scripts`. Dependencies remain local to the integration directory. No global installation or default login is changed.

`bin/ai-history --archive <preservation-directory> --agent iztac find <text>` searches preserved conversation labels. `windows <conversation-key>` lists saved windows and their predecessor links (up to the requested limit). `read <session-id> --after <event-sequence>` pages original user/assistant text. `--limit` precedes the subcommand and bounds scanned events, including non-message events. The returned cursor advances even if a page contains only tool events. This is an initial title locator and transcript reader, not full-text or semantic retrieval.

The archive contract is `sqlite-consistent/{main,hermes,neo}.sqlite`. SQLite is opened read-only and query-only. Histories are reference data, never current instructions. Output can contain private original conversation content; keep it local and retrieve only relevant passages.

## Outstanding integration constraints

The observed installed Rig provider switch implementation returns `switch_execution_not_yet_wired`. A profile label or TUI menu cannot establish successful account binding. The account service must verify runtime identity and report actual results.

The owner selected OpenAI Apple for the initial named-agent conversations, independently of the four-account worker pool. Native Pi sign-in uses a separate agent configuration directory; existing Codex credentials are not copied. Authentication and a real inference/tool round trip remain acceptance gates. A working `--version` does not prove inference or tool behavior. Do not substitute API billing for subscription access.

The existing account selector has only a Claude development-loop worker adapter. Codex execution integration and both providers' Rig account isolation remain acceptance work.

## Role resource loading

`integrations/pi/role-resources.mjs` is the reusable resource-loading component for the future account-bound launcher. It consumes an already validated conversation, absolute conversation/platform/auth/identity paths, and returns explicit cwd, Pi resources, in-memory settings and the conversation's native session directory.

Personal Morty and system Neo use a neutral workspace within the conversation home and load no repository context. Project/formation Iztac and project Neo use the bound workspace and Pi's repository-context discovery. All roles load shared session-entry guidance and their explicitly supplied identity file; only Iztac receives the engineering skill. Automatic extensions, skills, prompt templates and themes are disabled. The Perplexity extension is explicitly loaded; live search remains unverified.

Pass `historyArchive` as an absolute preservation-directory path to expose the
`agent_history` tool. The embedded tool binds the role from the conversation,
ignoring inherited `AI_AGENT_ROLE` and `AI_HISTORY_ARCHIVE` values. Without an
archive argument, history is unavailable rather than silently discovered. The
standalone `history.ts` extension continues to require both explicit environment
variables. Neither path reads a live OpenClaw database or needs its process.

`node integrations/pi/check-role-history.mjs` exercises the actual registered
tools and CLI against three real SQLite fixture stores: correct original text,
conflicting inherited values, rejection of another role's session ID, and
unchanged archive bytes. A separate read-only check against the actual preserved
main/hermes/neo databases also completed find/windows/read for each role with
unchanged SHA-256 hashes and no private content printed. This is tool routing,
not OS isolation: same-user shell access can still read accessible files. It also
does not prove an authenticated model selects relevant memories correctly.

`node integrations/pi/check-role-context.mjs` verifies all five role/scope combinations from two unrelated invoking directories using the installed Pi loader. It demonstrates context selection and paths, not authenticated execution, native resume, account selection, process ownership or OpenRig integration. The OpenAI Apple Pi auth profile still lacked an `openai-codex` credential at the latest local check; Codex authentication is separate.

## Persistent role sessions

`integrations/pi/role-session.mjs` constructs a real Pi `AgentSession` using the
explicit role resources. Its caller supplies the already selected `modelRuntime`,
model and account reference; it does not choose credentials, infer login identity,
or create a second account service. The reference is an association, not proof of
authenticated account identity.

New native transcripts use `conversationHome/native/pi`. A native custom entry
records the conversation ID, role and account reference. Resume requires an exact
existing file in that directory, matching stored association and workspace.
Unbound historical Pi transcripts need a deliberate adoption procedure; this
component does not silently relabel them. An account change needs an explicit
handover rather than changing the stored reference behind an active session.

`node integrations/pi/check-role-session.mjs` runs the real SDK offline, writes
a native fixture transcript using Pi's APIs, resumes its original message, checks
account/conversation/outside-path rejection, and confirms existing bytes remain
unchanged. Fixture assistant text is not an inference result. Pi delays creating
the transcript file until an assistant message exists; an empty session object
does not establish persisted history.

This component is not yet the terminal launcher. The launcher must hold exclusive
writer ownership while resuming a file, connect the verified account selection,
and handle native TUI new/resume/fork/import transitions without losing the role
and conversation bounds. Authenticated inference, terminal interaction and
concurrent-writer/recovery acceptance remain open. Do not expose an unrestricted
native TUI around this factory and assume those transitions are already governed.

`lib/ai_ecosystem/pi_launch.py::exec_conversation` provides the POSIX writer
boundary for that launcher. A dedicated launch process acquires a nonblocking
`flock` on the conversation's persistent `.pi-writer.lock`, then replaces itself
with the selected absolute runtime executable. The descriptor survives exec;
there is no supervisor daemon or PID ledger. Never delete the lock file to
recover: process termination releases the OS lock. `DEV_PLATFORM_PI_LOCK_FD`
identifies the descriptor for the launched runtime; keep it open for its lifetime.

`tests/test_pi_launch.py` checks real Python-to-Node exec, competing launch
rejection, normal exit, forced-crash recovery and failed-exec cleanup. This
primitive is not yet wired into a public terminal command. Direct SDK callers
can still bypass it, so the session factory alone does not guarantee exclusive
ownership. The lock is cooperative and local to a filesystem that supports POSIX
flock; it is not a distributed coordination protocol for future remote swarms.

`integrations/pi/role-runtime.mjs` connects the session component to Pi's native
`AgentSessionRuntime`, the host expected by its native terminal UI. `/new`,
`/resume` and `/fork` reconstruct the same explicit role resources. Resume
reapplies the conversation's native session directory instead of retaining Pi's
default-directory fallback; an unpersisted fork retains its native ID, branch
and association. The native before-switch event rejects outside or unbound
resume/import targets before the current session is replaced.

The offline session check exercises those native lifecycle operations and verifies
the original transcript stays unchanged. It does not render the terminal, supply
a verified account environment, restrict native model/login menus or connect the
OS writer lock. Those remain launcher acceptance requirements. No replacement
TUI or custom branching/transcript format has been introduced.

## Native terminal boundary

`integrations/pi/role-terminal.mjs::runRoleTerminal` opens Pi's own
`InteractiveMode` using the bound runtime. It requires a real terminal and the
inherited launch-lock descriptor matching this conversation's lock file. The
descriptor check confirms wiring, not an unforgeable same-user security boundary;
the Python exec launcher must acquire the actual OS lock first.

`python3 -B integrations/pi/check-role-terminal.py` performs that real exec/PTY
chain with a temporary home, empty auth store, explicit offline mode and no
prompts. It observes native rendering of the session-entry context, role workspace
and Perplexity extension, exits with native Ctrl+D, then reacquires the same lock.
The check invokes the actual terminal implementation rather than a fake terminal.

This connects terminal rendering and writer ownership in the tested path. A
user-facing command still needs to resolve a real conversation, identity and
verified account through the account service. Authenticated inference, protected
search credentials, real account attribution and management of model/login menu
choices remain open; the offline fixture's account reference is explicitly fake.
