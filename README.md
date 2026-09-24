# dev-platform

Personal development platform. It holds the conventions every repository under this account is
initialized to, and the tools that keep them in place.

- `docs/how-it-connects.md`: the map of the whole setup, accounts, homes, seats, rigs and
  OpenRig, for the person using it. Start there.
- `docs/rig-working-branches.md`: the control rig, one worker seat per loop worktree and
  a Codex overseer; how to start it and fold its work.
- `templates/`: files copied into every new repository (agent instructions, contributing
  policy, pull request template, code owners, dependency updates, check and release workflows,
  the hygiene check, the version script, the decision record template, the empty specification
  skeleton and amendment ledger).
- `github/rulesets/`: branch rulesets applied to every repository, as JSON for the GitHub API.
- `hooks/`: editor and agent guardrails installed on the local machine. The machine's
  `~/.config/dev-platform/personal.conf` lists the owner's own repositories; every other
  repository is professional, and the guard treats the two differently.
- `skills/`: reusable procedures for the tools that work in these repositories.
- `runbooks/`: procedures performed by hand, once or rarely.
- `bin/new-repo`: initializes a repository from the templates and applies the rulesets.
- `bin/ai-account`: [verified native-account selection and quota snapshots](docs/accounts.md)
  for new CLI launches, with explicit cross-surface limitations.
- `MODELS.md`: which class of model does which class of work.
- `ROLES.md`: which surface holds which class of work, what each refuses, and where it hands off.
- `vscode/`: the editor surface: user-level chat instructions and the terminal approval list.

Repositories copy from this one. They never link to it.
