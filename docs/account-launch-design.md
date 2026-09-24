# Account service at the execution boundary

Design recommendation, 2026-09-24. Not implemented or enabled by this document.

## One shared launch contract

Evolve the existing ai-account selector into a small account-selection and launch component. Pi launchers, OpenRig worker creation and direct terminal launches call the same contract. They supply runtime, required provider/model capability, stable conversation ID, resolved cwd/scope, and either a pinned account or a named pool policy. The caller's permission to run work is independent of account availability.

The service selects an eligible account, atomically reserves a concurrency slot, resolves that runtime's verified native profile, and starts the process through its adapter. It records the real launch outcome and execution association in the existing session index. Failed launches release reservations. Exited/crashed executions are reconciled against their runtime owner; PID existence alone is not definitive identity. Reservations coordinate local concurrency and are not provider-guaranteed quota reservations.

A terminal adapter opens a direct user terminal when requested. Inside OpenRig, Rig owns the tmux pane and invokes the account-aware execution adapter within it. The account service does not create a second pane manager or swarm scheduler. A daemon-wide account environment cannot safely isolate seats that need different accounts. Wrapping only rig up is insufficient: later spawns and handovers must traverse the same execution boundary.

## Runtime bindings and allowance

Account identity, runtime credential binding and allowance pool are distinct. For example, OpenAI Apple may have one verified Codex binding and a separate Pi binding. The service stores references to native profiles, never a universal copied credential. Pi uses its own supported provider login. A Codex login alone does not establish that Pi is authenticated or entitled to use every model.

If both bindings are verified to draw on the same account/model allowance, they reference the same usage pool. Never display them as two subscriptions or add their remaining percentages. Preserve separate windows and model-specific pools where the provider exposes them. Account selection never silently changes subscription billing into API billing.

Select Pi's auth profile independently from its conversation storage. An account change must not make histories disappear into another account's default session directory. Claude/Codex adapters register their native history locators under the stable conversation association.

## Policy

“Most usage” is interpreted as most usable remaining allowance.

1. Honor an explicit pin, allowed provider/model, enabled accounts, valid native login and concurrency limits.
2. For auto selection, use recent comparable allowance observations and existing local assignments. Treat each limiting window separately; do not compare incompatible provider percentages as equivalent work capacity.
3. Keep a running session sticky. New workers may choose a different eligible account. Rate limits trigger cooldown and a policy-controlled checkpointed transition, not blind prompt replay or global credential replacement.
4. Unknown/stale quota stays visibly unknown. Refresh within bounded cost/time; apply the user's configured fallback preference or leave work pending if no eligible account can be selected. Do not silently label unknown accounts best.
5. Named-agent defaults and worker defaults can differ. OpenAI Apple remains the user's pinned initial Pi choice until the user selects an automatic Pi policy. Both paths use the service.

The human TUI controls pin/auto, eligible accounts, concurrency and draining. It displays selection reasons, observation age, live assignments and reset windows. No repeated model prompting is required. Account choice is deterministic code, not an LLM decision.

## Minimal implementation

Keep one core implementation with a machine-readable CLI and small Pi/Claude/Codex adapters. Reuse existing private configuration, filesystem locking and session records. Cached observations plus launch-time validation avoid probing all providers for every command. No HTTP server, proxy for model requests, wrapper for every tool, or new always-running daemon is needed initially. A local IPC service can be added later if push updates or cross-process needs justify it, keeping the same contract.

Sequence: extend the native-profile registry to runtime bindings and shared allowance references; add deterministic selection and atomic reservations; integrate the direct terminal and Pi launcher; integrate OpenRig at actual worker creation and handover; expose that same state through the chosen TUI.

Acceptance must include simultaneous different-account workers, concurrent selections respecting limits, Pi history remaining in place across a checkpointed account transition, failed-launch reservation recovery, verified runtime identity, and no changes to unrelated active sessions.

## Current evidence and limitations

The existing local ai-account run selects and verifies a bound Claude/Codex profile and execs the native tool; it has no automatic remaining-allowance policy or Pi adapter. Its Claude auth-status probe cannot establish remaining quota. Current local OpenRig integration documents unwired provider switching and absent verified per-seat profile injection. These gaps must be implemented and tested; wrapping the top-level commands does not resolve them.

Codex credential storage is configurable between file, OS credential store, automatic and ephemeral modes. Profile isolation must be checked against the actual native storage mode, not assumed merely from a directory name. Official documentation: https://learn.chatgpt.com/docs/auth#credential-storage
