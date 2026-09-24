# Shared session entry

`skills/session-entry/SKILL.md` is the short common orientation for native
Claude/Codex sessions. It separates purpose from runtime and account. It does not
start a loop, select an account, create a conversation or impose Iztac's complete
engineering workflow on other uses.

Deliver it through native user instructions and native skill discovery. Codex's
effective `CODEX_HOME/AGENTS.md` should tell the agent to read and apply the skill
at session start/resume and task changes. Check for `AGENTS.override.md`, which
takes precedence. Claude's effective user `CLAUDE.md` can import the skill with
`@` so its contents load directly. Keep existing policy intact.

Account-isolated homes need their own instruction/skill projection, using paths
valid inside that environment. Host installation does not prove container
installation. Do not mount a credential-bearing host home just to share skills.
Pi's explicit role loader is a separate integration; merely installing a global
skill does not add it to that loader.

Native instructions guide the model; they are not a security boundary or proof
that a model followed the skill. Acceptance requires a fresh native session in
each supported environment, showing the loaded context and correct behavior for
personal work, independent project work, assigned engineering work and resume.
Do not claim universal startup enforcement from a frontmatter validator or a
filesystem link check. Existing live sessions may need a fresh session to pick
up instruction changes.

Sources: [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [Claude user instructions and imports](https://code.claude.com/docs/en/memory).
