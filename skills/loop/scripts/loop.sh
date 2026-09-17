#!/usr/bin/env bash
# loop: the development loop as verbs. Continuous mode: the `sprint-ready` label is the go,
# `steer: pause` on the loop issue is the brake.
#
#   loop.sh tick <owner/repo>                   every 15 min by automation: dispatch a worker for
#                                               each sprint-ready issue with Scope and Depends lines,
#                                               dependencies closed, not yet dispatched, up to 3
#                                               running; prints NO_REPLY when nothing changed
#   loop.sh start <owner/repo>                  create+pin the loop issue if missing, post the PLAN
#   loop.sh go <owner/repo> [only N|skip N ...] post a steer and dispatch now (manual cycle)
#   loop.sh collect <owner/repo>                post the CYCLE comment
#   loop.sh plan <owner/repo>                   read-only: print the plan, post nothing
#   loop.sh status <owner/repo>                 read-only: running workers, their issues, draft PRs
#
# GitHub writes go through ghx (identity per repository from repos.conf) and happen only in the
# assistant's session on the owner's word; tick posts nothing. Workers push their own type/*
# branch and open a draft pull request under the owner's login. Never merges, never
# marks ready, never pushes to a protected branch, never deploys.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
skill="$(cd "$here/.." && pwd)"
CONF="${DEV_PLATFORM_REPOS:-$HOME/.config/dev-platform/repos.conf}"
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"
[ -f "$BRIEF_CONF" ] && . "$BRIEF_CONF"
state="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}"
verb="${1:?tick|start|go|collect|plan|status}"; repo="${2:?owner/repo}"; shift 2
LOOP_TITLE="Development loop"
CAP=3
today="$(TZ=America/Chicago date +%Y-%m-%d)"
out="$state/$today"; mkdir -p "$out"
GHX="$here/ghx"

repo_dir() {
  local d; d="$(awk -v r="$repo" '$1==r {print $2}' "$CONF" 2>/dev/null | head -1)"
  [ -n "$d" ] && [ -d "$d/.git" ] || { echo "loop: $repo is not mapped to a checkout in $CONF" >&2; exit 2; }
  echo "$d"
}
loop_issue() {
  gh issue list --repo "$repo" --state open --search "\"$LOOP_TITLE\" in:title" --json number,title \
    | jq -r --arg t "$LOOP_TITLE" '.[] | select(.title == $t) | .number' | head -1
}
ensure_loop_issue() {
  local n; n="$(loop_issue)"
  if [ -z "$n" ]; then
    local url; url="$("$GHX" "$repo" issue create --title "$LOOP_TITLE" --body-file "$skill/loop-issue-body.md")"
    n="${url##*/}"; "$GHX" "$repo" issue pin "$n" >/dev/null
    echo "created and pinned loop issue #$n" >&2
  fi
  echo "$n"
}
tier_model() {  # issue labels -> Claude Code model (MODELS.md tiers)
  case ",$1," in
    *",spec,"*|*",decision,"*|*",privacy,"*|*",security,"*) echo "opus" ;;
    *",documentation,"*) echo "haiku" ;;
    *) echo "sonnet" ;;
  esac
}
running_workers() {  # prints "pid issue" for live workers across all days
  local pf pid i
  for pf in "$state"/*/worker-*.pid; do
    [ -f "$pf" ] || continue
    pid="$(cat "$pf")"; i="$(basename "$pf" .pid)"; i="${i#worker-}"
    ps -p "$pid" >/dev/null 2>&1 && echo "$pid $i"
  done
}
dispatch() {
  local dir base i j title labels scope slug kind branch wt model
  dir="$(repo_dir)"
  git -C "$dir" fetch -q origin develop
  base="$(git -C "$dir" rev-parse --short=8 origin/develop)"
  for i in "$@"; do
    j="$(gh issue view "$i" --repo "$repo" --json title,body,labels)"
    title="$(jq -r .title <<<"$j")"; labels="$(jq -r '[.labels[].name]|join(",")' <<<"$j")"
    scope="$(jq -r '(.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // "unspecified"' <<<"$j")"
    slug="$(tr '[:upper:]' '[:lower:]' <<<"$title" | sed -E 's/^[a-z]+-[a-z]+[-:]? *//; s/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-36 | sed -E 's/-$//')"
    kind=fix; case ",$labels," in *",enhancement,"*|*",spec,"*) kind=feat ;; *",documentation,"*) kind=docs ;; esac
    branch="$kind/$slug-$i"; wt="$dir/.claude/worktrees/loop-$i-$slug"; model="$(tier_model "$labels")"
    if [ -e "$wt" ]; then echo "#$i: worktree exists, not relaunched"; continue; fi
    git -C "$dir" worktree add -q -b "$branch" "$wt" origin/develop
    cat > "$wt/.worker-brief.md" <<EOF
# Worker brief: issue #$i
Repository $repo. Branch \`$branch\` from origin/develop $base. This directory is your worktree.
Read AGENTS.md and CONTRIBUTING.md here first; the repository's rules win over this brief.
Issue #$i: $title
Scope (only these path prefixes may change): $scope
The documentation lines the repository's rules require in the same pull request are always in
scope as well: the specification text a behavior change affects, its status marker that cites
this issue, and any lock digest that guards it.
1. Read the issue and the spec sections it cites; read the code and its tests before editing.
2. If the fix needs code or test files outside the scope, write one comment on the issue with
   \`gh issue comment $i --repo $repo --body ...\` saying exactly what you found and stop. Do not push.
   If the code already matches the contract on this base and only the specification's status
   marker is stale, the change is that marker and its lock digest: make it and continue.
3. Otherwise: smallest coherent change with tests and affected spec lines; commits
   \`type(scope): summary\`; no names of people, tools, models or sessions in commits or code.
4. Delete this file (\`rm .worker-brief.md\`), run \`bun run check\` on the final head, paste the result in the
   pull request body.
5. \`git push -u origin $branch\`, then open a DRAFT pull request with the repository template,
   body citing \`Closes #$i\`. Stop.
Never push to develop or main, merge, mark ready, approve, deploy, restart, rebase or amend
pushed commits, or touch another worktree.
EOF
    # Headless workers get no interactive prompt and no repository-local allowlist (the worktree has
    # no .claude/settings.local.json), so every Bash call they need is allowed here explicitly.
    # The pre-tool-use guard hook still refuses pushes to protected branches, merges, ready, deploys.
    # The worker starts from a clean environment: only HOME, PATH, USER, LANG and TERM pass through.
    # A scheduler's process carries its own endpoint, proxy and credential variables, and a worker
    # that inherits them can be refused once the scheduled run ends. The coding agent's own
    # configuration decides its endpoint and credentials.
    ( cd "$wt" && env -i HOME="$HOME" PATH="$PATH" USER="${USER:-}" LANG="${LANG:-en_US.UTF-8}" TERM=dumb \
        nohup claude --model "$model" -p "$(cat .worker-brief.md)" --permission-mode acceptEdits \
        --allowedTools "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" \
          "Bash(git add *)" "Bash(git commit *)" "Bash(git push -u origin $branch)" \
          "Bash(gh issue view *)" "Bash(gh issue comment $i *)" "Bash(gh pr create *)" "Bash(gh pr view *)" \
          "Bash(bun run check)" "Bash(bun run *)" "Bash(bun test *)" "Bash(npx vitest *)" "Bash(rm .worker-brief.md)" \
        < /dev/null > "$out/worker-$i.log" 2>&1 & echo $! > "$out/worker-$i.pid" )
    echo "#$i -> $branch ($model) pid $(cat "$out/worker-$i.pid")"
  done
}

case "$verb" in
  plan)
    "$here/loop-sense.sh" --repo "$repo" --out "$out/plan.md" | sed '/^post/,$d'
    ;;
  status)
    echo "STATUS $(TZ=America/Chicago date '+%Y-%m-%d %H:%M') $repo"
    echo "running:"; running_workers | sed 's/^\([0-9]*\) \(.*\)$/  issue #\2 pid \1/' ; [ -z "$(running_workers)" ] && echo "  none"
    echo "draft prs:"
    gh pr list --repo "$repo" --state open --draft --json number,headRefName,statusCheckRollup --jq '.[] | select(.headRefName|test("^(feat|fix|docs|refactor|chore|test|perf|ci)/")) | "  #\(.number) \(.headRefName) checks=\(.statusCheckRollup|length)"'
    n="$(loop_issue)"; [ -n "$n" ] && echo "loop issue: #$n, last steer: $(gh issue view "$n" --repo "$repo" --json comments --jq '[.comments[].body | select(startswith("steer:"))] | last // "none"')"
    ;;
  start)
    n="$(ensure_loop_issue)"
    "$here/loop-sense.sh" --repo "$repo" --out "$out/plan.md" >/dev/null
    "$GHX" "$repo" issue comment "$n" --body-file "$out/plan.md" >/dev/null
    echo "loop issue #$n: plan posted for $today"; echo; cat "$out/plan.md"
    ;;
  go)
    n="$(loop_issue)"; [ -n "$n" ] || { echo "loop: no loop issue on $repo; run start first" >&2; exit 3; }
    "$here/loop-sense.sh" --repo "$repo" --out "$out/plan.md" >/dev/null
    steer="steer: go${*:+ $*}"
    "$GHX" "$repo" issue comment "$n" --body "$steer" >/dev/null
    echo "posted '$steer' on #$n"
    sel="$(grep -oE '^  #[0-9]+ lane=' "$out/plan.md" | grep -oE '[0-9]+' || true)"
    only=""; skip=""; mode=""
    for a in "$@"; do case "$a" in only) mode=only ;; skip) mode=skip ;; [0-9]*) [ "$mode" = only ] && only="$only $a"; [ "$mode" = skip ] && skip="$skip $a" ;; esac; done
    [ -n "$only" ] && sel="$(tr ' ' '\n' <<<"$only" | grep -v '^$')"
    for s in $skip; do sel="$(grep -vx "$s" <<<"$sel" || true)"; done
    [ -n "$sel" ] || { echo "nothing selected after steer; no worker launched"; exit 0; }
    # shellcheck disable=SC2086
    dispatch $sel
    ;;
  collect)
    n="$(loop_issue)"; [ -n "$n" ] || { echo "loop: no loop issue" >&2; exit 3; }
    planned="$(grep -cE '^  #[0-9]+ lane=' "$out/plan.md" 2>/dev/null || echo 0)"
    dispatched="$(ls "$out"/worker-*.pid 2>/dev/null | wc -l | tr -d ' ')"
    "$here/loop-collect.sh" --repo "$repo" --planned "$planned" --dispatched "$dispatched" --out "$out/cycle.md" | sed '/^post/,$d'
    "$GHX" "$repo" issue comment "$n" --body-file "$out/cycle.md" >/dev/null
    echo; echo "cycle posted on #$n"
    ;;
  tick)
    n="$(loop_issue)"
    if [ -n "$n" ]; then
      last_steer="$(gh issue view "$n" --repo "$repo" --json comments --jq '[.comments[].body | select(startswith("steer:"))] | last // ""')"
      case "$last_steer" in "steer: pause"*) echo NO_REPLY; exit 0 ;; esac
    fi
    running="$(running_workers | wc -l | tr -d ' ')"
    cap=$((CAP - running)); [ "$cap" -gt 0 ] || { echo NO_REPLY; exit 0; }
    "$here/loop-sense.sh" --repo "$repo" --local-cap "$CAP" --out "$out/plan.md" >/dev/null
    cand="$(grep -oE '^  #[0-9]+ lane=' "$out/plan.md" | grep -oE '[0-9]+' || true)"
    dir="$(repo_dir)"; sel=""
    heads="$(git -C "$dir" ls-remote --heads origin 2>/dev/null || true)"
    for i in $cand; do
      [ "$cap" -gt 0 ] || break
      ls -d "$dir"/.claude/worktrees/loop-"$i"-* >/dev/null 2>&1 && continue
      grep -qE "refs/heads/[a-z]+/.*-$i\$" <<<"$heads" && continue
      sel="$sel $i"; cap=$((cap-1))
    done
    [ -n "${sel// /}" ] || { echo NO_REPLY; exit 0; }
    echo "TICK $(TZ=America/Chicago date '+%Y-%m-%d %H:%M') $repo"
    # shellcheck disable=SC2086
    dispatch $sel
    ;;
  *) echo "unknown verb $verb" >&2; exit 2 ;;
esac
