# Skills audit, 2026-09-24

Branch `feat/skills-consolidation`, cut from `feat/local-first-loop` (68ecbde, the installed
release). The question: which skills cover Ricky's real use cases, fire at the right moment and
reach the runtime that needs them, now that repositories are local-first.

## Result

Nine skills cover every use case once three are rewritten. Two more are deprecated (marked, not
removed). The main gap, starting a local repository from a goal, is closed by making `intake`
local-aware rather than adding a parallel skill.

| Skill | Verdict | One-line reason |
| --- | --- | --- |
| `/develop` | keep | The router for every context; already injected where discovery is off. |
| `development-workspace` | keep, small rewrite | The engineering entry; now also covers reviewing and merging a branch outside the loop. |
| `new-repo` | rewrite | Description was cut off mid-word and broke strict YAML; body was a placeholder contract. |
| `intake` | rewrite | GitHub-only (`ghx` decision issues); failed on local repositories; description cut off. |
| `distill` | keep | Already file-based and backend-neutral. |
| `loop` | keep, trigger rewrite | Covers local and GitHub days; description did not mention reviewing or folding workers. |
| `spec-lint` | rewrite | Cut-off description, broke strict YAML, assumed GitHub issues. Merge into `intake` is proposed. |
| `bounded-decisions` | keep | Cross-cutting, small, already well triggered. |
| `deploy-verify` | deprecate | Unexercised contract for one project's Testing host and deploy log. |
| `staging-census` | deprecate | Same: one project's Testing host; never exercised; broke strict YAML. |
| `iztac-engineering` | keep | Pi Iztac only; its Frame and Program routes name `intake` and `loop`, which Pi cannot load. |
| `openrig-skills` | keep (vendored) | OpenRig's own; not ours to edit. |
| Client-native skills | out of scope | Claude desktop's synced skills and Codex's `.system`; serve Morty-style everyday work. |

## Findings that apply to several skills

1. **Five descriptions were truncated at authoring.** `deploy-verify`, `intake`, `new-repo`,
   `spec-lint` and `staging-census` ended in `tha…`, `d…` or `t…`. The description is the only
   text a client reads when deciding to load a skill, so these could not trigger reliably.
2. **Three frontmatters were not strict YAML.** `new-repo`, `spec-lint` and `staging-census` had
   a plain scalar containing `: `, which Pi's YAML parser rejects. `fix/skill-frontmatter-yaml`
   (d385034) fixed this on an older base; it does not merge cleanly here (it touches the removed
   `morning-brief` and a diverged `bin/check`). Its test is ported to this branch and extended to
   refuse a description that ends in an ellipsis. That branch is superseded by this one.
3. **Four skills were contracts, not procedures.** `deploy-verify`, `new-repo`, `spec-lint`,
   `staging-census` said "the procedure is filled in when the skill is first exercised". Only
   `new-repo` has since been exercised (`bin/new-repo`, `tests/test_new_repo.py`).
4. **The planning path assumed GitHub.** `intake` filed `decision` issues through `ghx`,
   `spec-lint` checked that cited issues exist, and the spec templates said an undecided proposal
   "is a GitHub issue". A `local` repository has no issues; its numbers are task numbers.
5. **Reach is uneven.** See the reach table below. The isolated homes and Pi roles see almost
   none of the platform's procedures, including the ones their instructions tell them to use.

## Each skill

### session-entry (now `/develop`)

- **For:** choosing the working context (personal, system, independent project, Iztac, assigned
  worker) at the start of a session or on a change of scope.
- **Sees it:** default homes as a skill; every Claude/Codex session through `~/.claude/CLAUDE.md`
  `@`-import; Pi roles as injected instructions (`integrations/pi/role-resources.mjs`).
- **Triggers:** every new or resumed session and on scope change. It is loaded by instruction, so
  the description matters less than elsewhere.
- **GitHub/local:** neutral.
- **Overlap:** `development-workspace` is the expanded "independent project work" row.
- **Verdict: keep.** No change.

### development-workspace

- **For:** locating a project, joining or resuming existing work, reconciling ownership before
  shared edits.
- **Sees it:** default homes. Referenced by `ROLES.md`, `bin/ai-work`, OpenRig's control role
  guidance and `docs/session-context-contract.md`, so renaming it is costly.
- **Triggers:** "open/resume project X", "continue that branch", "join the loop".
- **GitHub/local:** neutral, but did not say that a local repository's ledger is `docs/tasks/`.
- **Overlap:** with `/develop` (routing) and `iztac-engineering` (Continue route). Merging
  into `/develop` would load project procedure into personal sessions; keep separate.
- **Gap it now covers:** reviewing and merging a worker or offshoot branch that is not a loop
  worker (for example a Codex worktree branch). There was no procedure for that.
- **Verdict: keep, small rewrite** (task ledger, branch review section).

### new-repo

- **For:** starting a project from zero with `bin/new-repo`.
- **Sees it:** default homes. `bin/new-repo` is on `PATH` everywhere the release is installed.
- **Triggers:** "start a new project/repo", "set up a repository".
- **GitHub/local:** the script is local by default since `f101775`; the skill still described
  rulesets and GitHub first, and did not mention `--register`/`--personal` or what comes next.
- **Verdict: rewrite** as a real procedure that ends by handing to `intake`.
  `runbooks/new-repo.md` was also stale ("add to personal.conf by hand"); fixed.

### intake

- **For:** turning a goal, notes, a transcript or a `distill` candidate into decisions, then
  specification changes, then implementable tasks.
- **Sees it:** default homes. Named by `ROLES.md`, `development-workspace`, `iztac-engineering`.
- **Triggers:** "here are notes from the call", "turn this into tasks", "spec this out", and
  now "I want to build X" in a repository with an empty specification.
- **GitHub/local:** GitHub only. On a `local` repository step 3 (`ghx` issue create) fails.
- **Overlap:** `distill` feeds it; `spec-lint` checks its output.
- **Verdict: rewrite.** One procedure, two backends chosen from `repos.conf`: local decisions are
  `docs/decisions/NNNN-*.md` with `Status: proposed`, tasks are `docs/tasks/<N>-*.md` written
  with `dev-loop tasks <repo> new` and checked with `dev-loop tasks <repo> check`; GitHub-backed
  repositories keep the `ghx` path unchanged. A goal stated in one sentence is a valid source.

### distill

- **For:** a raw record into ranked candidate statements in `docs/incoming.html`.
- **Sees it:** default homes.
- **Triggers:** a long transcript or thread with many possible requirements.
- **GitHub/local:** neutral; writes one file, files nothing.
- **Overlap:** it is `intake`'s optional first stage. Could merge later; kept because its output
  is a human-edited artifact with its own template and life cycle.
- **Verdict: keep.**

### loop

- **For:** running a repository's day: start, plan, dispatch headless workers or OpenRig seats,
  collect, fold reviewed worker branches, close (local merge or one pull request), finish, tidy.
- **Sees it:** default homes; `dev-loop` on `PATH`.
- **Triggers:** "run the loop", "dispatch workers", "start the team", "fold #3", "close the day".
- **GitHub/local:** both, explicitly (`Local repositories` section, `loop-tasks.py`).
- **Verdict: keep.** Description rewritten to name review, fold, seats and local close. The skill
  now also documents `dev-loop tasks`.

### spec-lint

- **For:** checking a specification tree against the repository standard.
- **Sees it:** default homes. Referenced nowhere except `docs/how-it-connects.md`.
- **Triggers:** before a specification change merges; on review of a spec branch.
- **GitHub/local:** "every issue cited exists and is open or closed" assumed GitHub.
- **Verdict: rewrite** (quoted description; a cited number resolves to a task file, a decision
  record or an issue depending on the backend). **Proposed:** merge its contract into `intake`'s
  check step, since that is the only moment it is run. Needs Ricky's decision.

### bounded-decisions

- **For:** asking the local Laya service for a shadow recommendation before costly route
  choices. Needs the shared service installed.
- **Sees it:** default homes. `ai-env doctor` probes Laya.
- **Verdict: keep.** No change.

### deploy-verify and staging-census

- **For:** after a deploy, confirming the running version, schema and deploy-log row; enumerating
  what runs on "the Testing host" and comparing with `develop`.
- **Sees it:** default homes, so they are offered in every repository, including local ones that
  have no host, no deploy log and no `/health`.
- **Evidence:** both are single-paragraph contracts, never exercised, referenced only by
  `docs/how-it-connects.md`. The vocabulary (Testing host, deploy log, store schema, active
  interactions) is one professional project's operations model, matching `runbooks/release.md`.
- **Verdict: deprecate.** Marked in the description so they stop triggering; folders kept so
  installed links and `ai-env doctor` stay intact. If that project still wants them, they belong
  in its own repository as project skills (`.claude/skills/`), written against its real host.
  Removal waits for Ricky.

### iztac-engineering

- **For:** Iztac's engineering routes in Pi.
- **Sees it:** only Iztac's Pi sessions (`additionalSkillPaths`).
- **Gap:** its Frame, Build and Program routes send Iztac to `distill`, `intake` and `loop`, but
  Pi runs with skill discovery off, so Iztac cannot load them as skills. See proposals.
- **Verdict: keep.** Its Frame route now names the local path; the Pi loading question goes to
  Ricky.

## Use cases against the target set

| Use case | Skills that carry it |
| --- | --- |
| Personal and everyday (Morty) | `/develop` routes; client-native skills do the work. No platform skill needed. |
| System operations (Neo) | `/develop` routes; `ai-env doctor` and runbooks. No skill gap found. |
| Independent engineering in Claude Code or Codex | `/develop`, then `development-workspace`, then the task skill. |
| Iztac project conversation | `/develop` (injected), `iztac-engineering`. |
| Start a project from zero | `new-repo`, then `intake` (goal to decision to spec to tasks), then `loop`. |
| Notes, calls, email into work | `distill` (optional), then `intake`. |
| Run the loop and an OpenRig team | `loop` (`LOOP_SEAT_RIG` seats), `openrig-skills` for fleet mechanics. |
| Review and merge worker branches | `loop` (fold, close) for loop workers; `development-workspace` for any other branch. |
| Local-first and GitHub-backed repos | `intake` and `loop` branch on the `repos.conf` posture; the rest are neutral. |

## Target skill set and triggers

The descriptions below are the ones now on the branch. They name the situation first, then the
action, so a client matches on what the user said rather than on the skill's name.

| Skill | Description (trigger) |
| --- | --- |
| `/develop` | Orient every new or resumed native agent session to its actual purpose, scope and existing assignment before working. Reuse on a change of task; do not automatically enroll ordinary conversations in an engineering sprint. |
| `development-workspace` | Locate and enter a project, resume or join existing development work, or review and merge a branch outside the loop, from a native coding session. Resolve workspace and ownership before shared edits; do not automatically start a sprint or adopt an agent identity. |
| `new-repo` | Start a new project from zero: create a repository to the platform standard with `new-repo`, local by default or GitHub-backed on request, register it for the loop, then hand the goal to `intake`. |
| `intake` | Turn a goal, meeting notes, a transcript, an email or a `distill` candidate into decision records, specification changes and implementable tasks. Works in local repositories (decision and task files) and GitHub-backed ones (decision and task issues). Use when asked to spec something out, plan work, or turn a request into tasks. |
| `distill` | (unchanged) |
| `loop` | Run a repository's development loop: start a day, dispatch headless workers or OpenRig worker seats on ready tasks, review and fold worker branches, and close the day with a local merge or one pull request. Also lists and writes local task files. Use for "run the loop", "start the team", "fold", "close the day". |
| `spec-lint` | Check a repository's specification (`docs/spec/`) against its conventions before a specification change merges: trace comments, status markers that cite an existing task, decision or issue, lock markers where used, no people or tools named. Reports findings; edits nothing. |
| `bounded-decisions` | (unchanged) |
| `deploy-verify` | Deprecated: project-specific to one Testing host and its deploy log. Do not load unless that project names this skill. |
| `staging-census` | Deprecated: project-specific to one Testing host and its deploy log. Do not load unless that project names this skill. |

## How each skill reaches each runtime

| Runtime | Today | Proposed |
| --- | --- | --- |
| Default homes (`~/.claude`, `~/.codex` through `~/.agents/skills`) | All platform skills, linked to `current/skills/<name>`. On 2026-09-24 every link points at `current`; the "links are not uniform" note in `how-it-connects.md` is out of date for these three folders. | No change. Deprecated skills stay linked until removal. |
| Isolated homes (`anthropic-apple`, `openai-gmail`) | No platform skills. `/develop` arrives only because the home's instructions point at the default copy. | Link the same set into each isolated home's `skills/`. Isolation exists for credentials, not procedures. Needs a small `ai-env` or account-preparation step and Ricky's decision (it writes into those homes). |
| OpenRig seats | The seat's account home. Platform agents install no skills (`skills: []`). Worker seats need none: the loop's brief is self-contained. | Control seats get the default set through their home; seats on isolated accounts follow the row above. |
| Pi roles (Morty, Neo, Iztac) | Discovery off. `/develop` injected; Iztac also gets `iztac-engineering`. | Give Iztac `intake`, `loop`, `new-repo` and `distill` through `additionalSkillPaths` so the routes it names are loadable. Morty and Neo need none. Changes `check-role-skills.mjs`' expected list; needs Ricky's decision on Iztac's context budget. |

## What changed on this branch

- Every platform SKILL.md frontmatter parses as strict YAML and no description is truncated;
  `tests/test_skill_frontmatter.py` enforces both, and `bin/check` requires PyYAML.
- `intake` rewritten local-aware; accepts a plain goal as the source.
- `dev-loop tasks <repo> list|next|new|check` (`loop-tasks.py` verbs `next`, `new`, `check`)
  with tests, so writing and validating task files is a command, not hand formatting.
- `new-repo` rewritten as a procedure; `runbooks/new-repo.md` brought up to date.
- `loop`, `spec-lint`, `development-workspace` descriptions and small body updates.
- `deploy-verify`, `staging-census` marked deprecated.
- Verified end to end in a sandbox: `new-repo --register --personal`, then `dev-loop tasks new`
  twice on a planning branch, `tasks check`, a local merge, `tasks` and `plan` (selects #1, holds
  #2 on its dependency).
- Small follow-up, not done: `loop-sense.sh` still prints "review queue (owner, on GitHub)" in a
  local repository's PLAN.
- Spec and decision templates no longer say an undecided proposal "is a GitHub issue".
- `docs/how-it-connects.md` skills table updated.

## Needs Ricky's decision

1. Remove `deploy-verify` and `staging-census` from the platform (and, if wanted, recreate them
   in the owning project's repository).
2. Merge `spec-lint` into `intake`'s check step, or keep it as its own skill.
3. Link the platform skills into the isolated homes.
4. Give Iztac's Pi sessions `intake`, `loop`, `new-repo` and `distill`.
5. Activate a release that contains this branch. Nothing here was activated or pushed.

## Addendum, same day: pstack becomes the engineering method

Ricky chose pstack (Lauren Tan's Cursor skills, MIT) as the engineering method, preferring her
design to the platform's where they differ. On branch `feat/pstack-skills`:

- `vendor/pstack/` holds her tree unmodified; `bin/pstack-port` builds 46 of her skills into
  `skills/` (all but `make-bot-ui` and the `automations/benny` skills, which need Cursor
  Automations). `docs/pstack-platform.md` maps her Cursor names to this machine and lists the steps
  the guard hook leaves to the owner.
- The target set above changes shape. Her `/dev-plat` is the engineering front door, with her
  playbooks and principles; `/develop` routes engineering to it and keeps the personal and
  system contexts she has no concept of. The platform's own skills stay for what pstack lacks:
  `new-repo`, `distill`, `intake` and `loop` (the local-first task ledger and workers),
  `development-workspace`, `bounded-decisions`.
- Iztac's condensed copies of her principles are removed; its index links her principle skills.
- `/setup-pstack` writes `~/.config/dev-platform/pstack-models.md`, which the loop reads for its
  workers' model and effort.
- The day-branch model is replaced in design by her branch-per-unit model (see the map);
  `loop.sh` is not yet changed.

## Addendum, evening of 2026-09-24: rig branches

This audit records the morning's view; the tables above predate pstack and the loop change. On
branch `feat/rig-branches`: the loop works on a goal's `type/slug` rig branch instead of a
`loop/<date>` day branch; `fold` is a control-seat verb that checks the branch, releases the
worker's seat and merges it up; landing the rig branch on the base stays the owner's. pstack's
front door is `/dev-plat` and session entry is `/develop`.
