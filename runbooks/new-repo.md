# Runbook: a new repository

One command initializes a repository to the standard; the rest is GitHub configuration you do once.

## 1. Initialize

```
bin/new-repo <directory> [--owner <github-login>] [--github <owner>/<name>] [--private|--public]
```

- Copies `templates/` into the directory: `AGENTS.md`, `CONTRIBUTING.md`, `CLAUDE.md`, the pull request template, `CODEOWNERS` (with your login), Dependabot, the `checks` and `release` workflows, `scripts/checks/hygiene.ts`, `scripts/version.ts`, `docs/decisions/0000-template.md`.
- Writes a minimal `package.json` with the check scripts, a `.gitignore`, a `README.md` stub, `tsconfig.json`, `.prettierrc.json` and `eslint.config.js`.
- Creates the repository on `main`, tags `v0.1.0` on the first commit so the version derives, and creates `develop`.
- With `--github`, creates the GitHub repository with `gh`, pushes both branches and applies `github/rulesets/develop.json` and `github/rulesets/main.json`.

If the repository is the owner's own, add its path to `~/.config/dev-platform/personal.conf`.

## 2. GitHub, by hand

1. Settings, General: default branch `develop`; allow merge commits only; delete head branches on merge.
2. Settings, Code security: enable Dependabot alerts and security updates.
3. If the plan allows automatic code review, turn it on for every pull request.
4. Create the milestone for the first minor version.

## 3. First pull request

Cut `docs/readme` from `develop`, write the README (what the software is, how to run it, where the contracts are), open the pull request with the template, run `bun run check`, merge it. The rulesets are now proven on a real change.
