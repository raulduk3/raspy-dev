---
name: development-workspace
description: >-
  Locate and enter a project, resume or join existing development work, or review and
  merge a branch outside the loop, from a native coding session. Resolve workspace and
  ownership before shared edits; do not automatically start a sprint or adopt an agent
  identity.
---

# Development workspace

Ricky gives the goal in ordinary language. Resolve the working context, then
continue using the skills relevant to that goal. Shared `/develop` handles
general orientation; this skill handles project attachment and continuity.

1. **Locate the work.** Read the repository instructions and inspect its actual
   Git root, branch and worktree. Use `ai-work --help` and the existing catalog
   when locating a project. A proposed project can use an explicit formation
   directory; do not invent a repository association from a window title.
2. **Reconcile ownership.** Inspect the existing assignment, checkpoint and live
   workers before editing shared files. A direct Claude/Codex window is independent
   unless explicitly associated with existing work. For assigned work, retain its
   coordinator and isolated worktree. A Rig seat or new terminal does not create
   a sprint or authorize another writer.
3. **Choose the procedure.** For an Iztac conversation, use
   [Iztac engineering](../../agents/iztac/skills/iztac-engineering/SKILL.md).
   An assigned engineering worker uses the relevant portion of its supplied
   workflow without assuming Iztac's identity. Independent work follows repository
   instructions and `/dev-plat`, pstack's engineering front door
   (`docs/pstack-platform.md` maps its Cursor names to this machine); do not load
   the Iztac framework automatically. `new-repo` starts a project; `distill`/`intake` turn a goal
   or source into decisions, specification and tasks; `loop` applies only when operating
   the development loop. A `local` repository (third column of `repos.conf`) keeps its
   tasks in `docs/tasks/` and merges on this machine; only the others use GitHub.
4. **Act and explain.** State the outcome, useful completion check and next action
   briefly for substantial work. Use native tools, explain decisions in terms of
   the concrete task, and distinguish observed results from assumptions. A status
   question does not authorize implementation, recurring monitoring or dispatch.
5. **Keep continuity.** Use the existing conversation/task checkpoint. Record
   project, branch/worktree, relevant native session references, verified progress,
   evidence, running work and the next action. `ai-session handoff --help` describes
   revision-checked updates for indexed sessions. Keep unindexed work's checkpoint
   with its existing task artifact; do not create another task database. Native
   transcripts stay native, and unknown account attribution stays unknown.

## Review and merge a branch outside the loop

Loop workers are reviewed and folded with `dev-loop fold`. Any other branch (an offshoot
worktree, a Codex or Claude session's branch) is reviewed the same way: read
`git diff <base>...<branch>` and the branch's own notes, run the repository's check on its head in
its worktree, and report findings with evidence. Do not edit a worktree another session holds.
The owner merges: in a local repository with `git merge --no-ff <branch>` in their terminal; in a
GitHub-backed one through its pull request. Never merge into `develop` or `main` yourself.

Use the account service/native controls for new execution environments; do not
change active credentials as part of project attachment. OpenRig owns supported
worker terminals and messaging. A running loop retains ownership until an explicit
handover. Follow repository publication rules and the user's authorization.

The fuller adapted pstack workflow and principles live with Iztac. This shared
entry point deliberately contains no separate copy of them and no OpenClaw-only
tooling or scheduled morning-brief procedure. Any session may still use one:
when a concrete choice turns on an engineering principle, read its one-line index
in `~/.local/share/dev-platform/current/agents/iztac/skills/iztac-engineering/SKILL.md`
and then only that principle's file. Reading a rule adopts neither Iztac's
identity nor his workflow.
