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
