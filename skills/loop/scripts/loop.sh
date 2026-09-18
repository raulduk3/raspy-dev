#!/usr/bin/env bash
# loop: the development loop as verbs. One local day branch per repository and day, a file
# ledger on this machine, one pull request to develop when the day closes.
#
# The repository sees only what its policy asks for: one branch cut from develop, one pull
# request to develop with the template body and the check output, merged by the owner. The
# batching is local. Workers branch from the local day branch and never push; the owner reviews
# each worker branch on this machine and folds it into the day branch; at close the day branch
# is pushed once under an ordinary type/slug name. No comment is ever posted on an issue, no
# loop/* ref reaches the remote, and CI runs once, on the day pull request.
#
# Ledger: LOOP_STATE_DIR/<owner__repo>/   (LOOP_STATE_DIR from brief.conf; default
#                                          ~/.local/state/dev-platform/loop)
#   steer                     first word go|pause, the rest are steer args (only N, skip N).
#                             A MISSING FILE MEANS PAUSE.
#   day-branch                the open day's local branch, loop/<date>; absent when no day is open
#   <date>/plan.md            PLAN (loop-sense.sh)
#   <date>/cycle.md           CYCLE (loop-collect.sh)
#   <date>/folded.tsv         issue <tab> branch <tab> merge sha <tab> folded-at
#   <date>/folded-<issue>.md  the worker's pull request body, kept at fold
#   <date>/pr.md, pr-url, pushed-as, pr-merged   the day pull request
#   <date>/workers/<issue>.{pid,log}
#
# Verbs. assistant = on the owner's word in that session; owner = the owner in a terminal
# (refused without one); automation = the scheduled tick.
#   status <repo>                        read-only summary                              anyone
#   plan <repo>                          write and print the PLAN                       anyone
#   start <repo>                         cut loop/<date> from origin/develop into a day
#                                        worktree, record it, write the plan            assistant
#   go <repo> [only N ..|skip N ..]      write steer go, plan, dispatch now              assistant
#   pause <repo>                         write steer pause                              assistant
#   tick <repo>                          dispatch when steer says go, up to CAP running automation
#   collect <repo>                       write and print the CYCLE                      assistant
#   fold <repo> <issue|branch> ..        merge a reviewed worker branch into the day
#                                        branch, keep its body, remove branch+worktree  owner
#   close <repo> [--as type/slug] [--title t] [--push [--ready]]
#                                        check the day head, write pr.md and print the
#                                        commands; --push pushes the day branch as
#                                        type/slug and opens the one pull request       owner for --push
#   finish <repo> <pr>                   after the owner merged it: close the folded
#                                        issues, delete the pushed branch, remove the
#                                        day worktree and branch, steer pause           owner
#   tidy <repo> [--apply]                classify merged and stale branches and
#                                        worktrees; --apply bundles, then deletes       owner for --apply
#
# Nothing here pushes to develop or main, merges into them, marks ready, approves or deploys.
set -eu
# $0 may be a symlink (the assistant workspace and ~/.claude/skills link here): resolve it.
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
HOOKS="$(cd "$here/../../../hooks" && pwd)"
CONF="${DEV_PLATFORM_REPOS:-$HOME/.config/dev-platform/repos.conf}"
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"
[ -f "$BRIEF_CONF" ] && . "$BRIEF_CONF"
state="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}"
verb="${1:?status|plan|start|go|pause|tick|collect|fold|close|finish|tidy}"; repo="${2:?owner/repo}"; shift 2
CAP=3
today="$(TZ=America/Chicago date +%Y-%m-%d)"
ctl="$state/${repo//\//__}"; mkdir -p "$ctl"
GHX="$here/ghx"

repo_dir() {
  local d; d="$(awk -v r="$repo" '$1==r {print $2}' "$CONF" 2>/dev/null | head -1)"
  [ -n "$d" ] && [ -d "$d/.git" ] || { echo "loop: $repo is not mapped to a checkout in $CONF" >&2; exit 2; }
  echo "$d"
}
steer_word() { if [ -f "$ctl/steer" ]; then head -1 "$ctl/steer" | awk '{print $1}'; else echo pause; fi; }
steer_args() { if [ -f "$ctl/steer" ]; then head -1 "$ctl/steer" | cut -s -d' ' -f2-; fi; }
day_branch() { if [ -f "$ctl/day-branch" ]; then head -1 "$ctl/day-branch"; fi; }
need_day() {
  local d; d="$(day_branch)"
  [ -n "$d" ] || { echo "loop: no day is open for $repo; run: loop.sh start $repo" >&2; exit 3; }
  echo "$d"
}
day_wt() { echo "$(repo_dir)/.claude/worktrees/day-${1#loop/}"; }
owner_terminal() {
  [ -t 0 ] && [ -t 1 ] || { echo "loop: '$verb' is the owner's own act and runs in a terminal, never from an agent" >&2; exit 4; }
}
# The open day's date decides the ledger directory; without an open day, today's.
day="$(day_branch)"; dayd="${day#loop/}"; [ -n "$day" ] || dayd="$today"
out="$ctl/$dayd"; mkdir -p "$out/workers"

tier_model() {  # issue labels -> Claude Code model (MODELS.md tiers)
  case ",$1," in
    *",spec,"*|*",decision,"*|*",privacy,"*|*",security,"*) echo "opus" ;;
    *",documentation,"*) echo "haiku" ;;
    *) echo "sonnet" ;;
  esac
}
running_workers() {  # "pid issue" for live workers: this ledger and the pre-ledger layout
  local pf pid i
  for pf in "$ctl"/*/workers/*.pid "$state"/*/worker-*.pid; do
    [ -f "$pf" ] || continue
    pid="$(cat "$pf")"; i="$(basename "$pf")"; i="${i%.pid}"; i="${i#worker-}"
    ps -p "$pid" >/dev/null 2>&1 && echo "$pid $i"
  done
  return 0
}
worker_running() { running_workers | grep -qE " $1\$"; }
live_worktrees() {  # cwd of every running claude process
  local pid
  for pid in $(pgrep -x claude 2>/dev/null); do lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'; done
  return 0
}
worker_wt_of() { ls -d "$(repo_dir)"/.claude/worktrees/loop-"$1"-* 2>/dev/null | head -1; return 0; }
worker_branch_of() {  # issue -> local type/slug-<issue> branch
  git -C "$(repo_dir)" for-each-ref --format='%(refname:short)' 'refs/heads/*/*' | grep -E -- "-$1\$" | head -1; return 0
}
folded_issues() { if [ -f "$out/folded.tsv" ]; then cut -f1 "$out/folded.tsv" | sort -un; fi; }
exclusions() {  # "N reason" lines for loop-sense: folded issues and issues with a local worker
  local i wt
  for i in $(folded_issues); do echo "$i folded, waits for the day pull request"; done
  for wt in "$(repo_dir)"/.claude/worktrees/loop-*; do
    [ -d "$wt" ] || continue
    i="$(basename "$wt" | sed -nE 's/^loop-([0-9]+)-.*/\1/p')"
    [ -n "$i" ] && echo "$i has a local worker branch"
  done
  return 0
}
sense() {  # write and print the PLAN
  local ex; ex="$(mktemp)"; exclusions > "$ex"
  "$here/loop-sense.sh" --repo "$repo" --local-cap "$CAP" --exclude-file "$ex" --out "$out/plan.md"
  rm -f "$ex"
}
select_from_plan() {  # [only N ..|skip N ..] -> selected issue numbers, one per line
  local sel only="" skip="" mode="" a s
  sel="$(grep -oE '^  #[0-9]+ lane=' "$out/plan.md" 2>/dev/null | grep -oE '[0-9]+' || true)"
  for a in "$@"; do
    case "$a" in only) mode=only ;; skip) mode=skip ;; [0-9]*) [ "$mode" = only ] && only="$only $a"; [ "$mode" = skip ] && skip="$skip $a" ;; esac
  done
  [ -n "$only" ] && sel="$(tr ' ' '\n' <<<"$only" | grep -v '^$')"
  for s in $skip; do sel="$(grep -vx "$s" <<<"$sel" || true)"; done
  printf '%s\n' "$sel"
}
section() {  # <file> <header text> -> the section body, without its header
  awk -v h="## $2" '$0==h {f=1; next} /^## / {f=0} f' "$1" | sed '/^Closes #[0-9]*$/d'
}
dispatch() {  # <issue>...
  local dir base i j title labels scope slug kind branch wt model exclude
  dir="$(repo_dir)"
  base="$(git -C "$dir" rev-parse --short=8 "$day")"
  # The worker's untracked files are excluded repository-wide (local only, never committed).
  exclude="$(git -C "$dir" rev-parse --path-format=absolute --git-path info/exclude)"; mkdir -p "$(dirname "$exclude")"
  grep -qxF '.worker-*' "$exclude" 2>/dev/null || echo '.worker-*' >> "$exclude"
  for i in "$@"; do
    j="$(gh issue view "$i" --repo "$repo" --json title,body,labels)"
    title="$(jq -r .title <<<"$j")"; labels="$(jq -r '[.labels[].name]|join(",")' <<<"$j")"
    scope="$(jq -r '(.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // "unspecified"' <<<"$j")"
    slug="$(tr '[:upper:]' '[:lower:]' <<<"$title" | sed -E 's/^[a-z]+-[a-z]+[-:]? *//; s/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-36 | sed -E 's/-$//')"
    kind=fix; case ",$labels," in *",enhancement,"*|*",spec,"*) kind=feat ;; *",documentation,"*) kind=docs ;; esac
    branch="$kind/$slug-$i"; wt="$dir/.claude/worktrees/loop-$i-$slug"; model="$(tier_model "$labels")"
    if [ -e "$wt" ]; then echo "#$i: worktree exists, not relaunched"; continue; fi
    git -C "$dir" worktree add -q -b "$branch" "$wt" "$day"
    cat > "$wt/.worker-brief.md" <<EOF
# Worker brief: issue #$i
Repository $repo. Branch \`$branch\` from \`$day\` at $base. This directory is your worktree.
Read AGENTS.md and CONTRIBUTING.md here first; the repository's rules win over this brief.
Issue #$i: $title
Scope (only these path prefixes may change): $scope
The documentation lines the repository's rules require in the same pull request are always in
scope as well: the specification text a behavior change affects, its status marker that cites
this issue, and any lock digest that guards it.
1. Read the issue with its comments (\`gh issue view $i --repo $repo --comments\`): the owner refines
   the request in comments, and a comment posted after the body wins. Read the spec sections the
   issue cites; read the code and its tests before editing.
2. If the fix needs code or test files outside the scope, write what you found (the paths you
   would need and why) to \`.worker-blocked.md\` in this directory and stop. Do not comment on the
   issue. If the code already matches the contract on this base and only the specification's
   status marker is stale, the change is that marker and its lock digest: make it and continue.
3. Otherwise: smallest coherent change with tests and affected spec lines; commits
   \`type(scope): summary\`, body says why; no names of people, tools, models or sessions in
   commits or code. Stage only the files of the change. Never stage a \`.worker-*\` file.
4. Delete this file (\`rm .worker-brief.md\`), then run the full check on the final head with
   \`bash $HOOKS/check-once.sh\` (it runs \`bun run check\` and records the passing tree so the
   check is not repeated at exit). Keep its final lines for the next step.
5. Write \`.worker-pr.md\` in this directory with the four sections of the repository's pull
   request template as \`## \` headings: What changed and why, Verification (the check's final
   lines), Deploy and provider impact, Review notes. End it with the line \`Closes #$i\`. Then stop.
Never push, open a pull request, comment on GitHub, merge, mark ready, approve, deploy, restart,
rebase or amend, or touch another worktree. The owner reviews this branch on this machine.
EOF
    # Headless workers get no interactive prompt and no repository-local allowlist (the worktree has
    # no .claude/settings.local.json), so every Bash call they need is allowed here explicitly. No
    # push, no pull request, no comment: the worker only reads GitHub. The pre-tool-use guard hook
    # still refuses everything it always refuses. The worker starts from a clean environment: only
    # HOME, PATH, USER, LANG and TERM pass through, so a scheduler's endpoint, proxy and credential
    # variables never reach it; the coding agent's own configuration decides its endpoint.
    ( cd "$wt" && env -i HOME="$HOME" PATH="$PATH" USER="${USER:-}" LANG="${LANG:-en_US.UTF-8}" TERM=dumb \
        nohup claude --model "$model" -p "$(cat .worker-brief.md)" --permission-mode acceptEdits \
        --allowedTools "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" \
          "Bash(git add *)" "Bash(git commit *)" "Bash(gh issue view *)" \
          "Bash(bun install --frozen-lockfile)" "Bash(bun run check)" "Bash(bun run *)" "Bash(bun test *)" "Bash(bun install*)" \
          "Bash(~/.bun/bin/bun run *)" "Bash(~/.bun/bin/bun test *)" "Bash(~/.bun/bin/bun install*)" \
          "Bash($HOME/.bun/bin/bun *)" "Bash(npx vitest *)" "Bash(rm .worker-brief.md)" \
          "Bash(bash $HOOKS/check-once.sh*)" \
        < /dev/null > "$out/workers/$i.log" 2>&1 & echo $! > "$out/workers/$i.pid" )
    echo "#$i -> $branch ($model) pid $(cat "$out/workers/$i.pid")"
  done
}

case "$verb" in
  status)
    dir="$(repo_dir)"
    echo "STATUS $(TZ=America/Chicago date '+%Y-%m-%d %H:%M') $repo"
    if [ -f "$ctl/steer" ]; then echo "steer: $(head -1 "$ctl/steer")"; else echo "steer: pause (no steer file)"; fi
    if [ -n "$day" ]; then
      echo "day: $day, $(git -C "$dir" rev-list --count origin/develop.."$day" 2>/dev/null || echo '?') commits ahead of origin/develop, worktree $(day_wt "$day")"
    else
      echo "day: none open (loop.sh start)"
    fi
    echo "running:"; r="$(running_workers)"; if [ -n "$r" ]; then sed 's/^\([0-9]*\) \(.*\)$/  issue #\2 pid \1/' <<<"$r"; else echo "  none"; fi
    echo "worker branches:"; found=0
    for wt in "$dir"/.claude/worktrees/loop-*; do
      [ -d "$wt" ] || continue; found=1
      i="$(basename "$wt" | sed -nE 's/^loop-([0-9]+)-.*/\1/p')"; b="$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
      ahead="$(git -C "$dir" rev-list --count "${day:-origin/develop}".."$b" 2>/dev/null || echo '?')"
      st=working
      if [ -f "$wt/.worker-blocked.md" ]; then st=blocked
      elif worker_running "$i"; then st=running
      elif [ -f "$wt/.worker-pr.md" ]; then st="ready for review"
      elif [ "$ahead" = 0 ]; then st="no commits"
      fi
      echo "  #$i $b ahead $ahead: $st"
    done
    [ "$found" = 1 ] || echo "  none"
    echo "folded:"; if [ -s "$out/folded.tsv" ]; then awk -F'\t' '{print "  #" $1 " " $2 " " $3 " " $4}' "$out/folded.tsv"; else echo "  none"; fi
    if [ -f "$out/pr-url" ]; then echo "day pull request: $(cat "$out/pr-url") as $(cat "$out/pushed-as" 2>/dev/null)"; else echo "day pull request: not opened (loop.sh close)"; fi
    ;;
  plan)
    sense
    ;;
  start)
    [ -z "$day" ] || { echo "loop: a day is already open ($day). After its pull request merged: loop.sh finish $repo <pr>. To abandon it: remove $ctl/day-branch and the branch by hand." >&2; exit 3; }
    dir="$(repo_dir)"; git -C "$dir" fetch -q origin develop
    day="loop/$today"; dayd="$today"; out="$ctl/$dayd"; mkdir -p "$out/workers"; wt="$(day_wt "$day")"
    if git -C "$dir" show-ref -q --verify "refs/heads/$day"; then echo "loop: local branch $day already exists; delete or rename it first" >&2; exit 3; fi
    git -C "$dir" worktree add -q -b "$day" "$wt" origin/develop
    echo "$day" > "$ctl/day-branch"
    [ -f "$ctl/steer" ] || echo pause > "$ctl/steer"
    echo "day $day cut from origin/develop $(git -C "$dir" rev-parse --short=8 origin/develop) at $wt"; echo
    sense
    echo; echo "steer: $(steer_word). Dispatch with: loop.sh go $repo [only N|skip N]"
    ;;
  go)
    [ -n "$day" ] || need_day >/dev/null
    printf 'go%s\n' "${*:+ $*}" > "$ctl/steer"
    sense >/dev/null
    sel="$(select_from_plan "$@")"
    dir="$(repo_dir)"; keep=""
    for i in $sel; do ls -d "$dir"/.claude/worktrees/loop-"$i"-* >/dev/null 2>&1 && continue; keep="$keep $i"; done
    [ -n "${keep// /}" ] || { echo "steer: go written; nothing to dispatch (see $out/plan.md)"; exit 0; }
    echo "GO $(TZ=America/Chicago date '+%Y-%m-%d %H:%M') $repo on $day"
    # shellcheck disable=SC2086
    dispatch $keep
    ;;
  pause)
    echo pause > "$ctl/steer"; echo "steer: pause written for $repo; the tick dispatches nothing until loop.sh go"
    ;;
  tick)
    [ "$(steer_word)" = go ] || { echo NO_REPLY; exit 0; }
    [ -n "$day" ] || { echo NO_REPLY; exit 0; }
    running="$(running_workers | wc -l | tr -d ' ')"
    cap=$((CAP - running)); [ "$cap" -gt 0 ] || { echo NO_REPLY; exit 0; }
    sense >/dev/null
    # shellcheck disable=SC2046
    cand="$(select_from_plan $(steer_args))"
    dir="$(repo_dir)"; sel=""
    for i in $cand; do
      [ "$cap" -gt 0 ] || break
      ls -d "$dir"/.claude/worktrees/loop-"$i"-* >/dev/null 2>&1 && continue
      sel="$sel $i"; cap=$((cap-1))
    done
    [ -n "${sel// /}" ] || { echo NO_REPLY; exit 0; }
    echo "TICK $(TZ=America/Chicago date '+%Y-%m-%d %H:%M') $repo on $day"
    # shellcheck disable=SC2086
    dispatch $sel
    ;;
  collect)
    planned="$(grep -cE '^  #[0-9]+ lane=' "$out/plan.md" 2>/dev/null || echo 0)"
    dispatched="$(ls "$out"/workers/*.pid 2>/dev/null | wc -l | tr -d ' ')"
    "$here/loop-collect.sh" --repo "$repo" --dir "$(repo_dir)" --day "$day" --state "$out" --hooks "$HOOKS" \
      --planned "$planned" --dispatched "$dispatched" --out "$out/cycle.md"
    ;;
  fold)
    owner_terminal; need_day >/dev/null; dir="$(repo_dir)"; dwt="$(day_wt "$day")"
    [ -d "$dwt" ] || { echo "loop: day worktree $dwt is missing" >&2; exit 3; }
    [ -z "$(git -C "$dwt" status --porcelain --untracked-files=no)" ] || { echo "loop: the day worktree has uncommitted changes; commit or stash in $dwt first" >&2; exit 3; }
    [ $# -gt 0 ] || { echo "loop: fold needs issue numbers or branch names" >&2; exit 2; }
    for a in "$@"; do
      case "$a" in [0-9]*) i="$a"; b="$(worker_branch_of "$i")" ;; *) b="$a"; i="${b##*-}" ;; esac
      if [ -z "$b" ] || ! git -C "$dir" show-ref -q --verify "refs/heads/$b"; then echo "  #$i: no local worker branch"; continue; fi
      if worker_running "$i"; then echo "  #$i: worker still running; wait for it or stop it first"; continue; fi
      wt="$(worker_wt_of "$i")"
      if [ -n "$wt" ] && [ -f "$wt/.worker-blocked.md" ]; then echo "  #$i: blocked, not folded:"; sed 's/^/    /' "$wt/.worker-blocked.md"; continue; fi
      if [ -n "$wt" ] && [ -n "$(git -C "$wt" status --porcelain --untracked-files=no)" ]; then echo "  #$i: $wt has uncommitted changes; commit or discard them first"; continue; fi
      ahead="$(git -C "$dir" rev-list --count "$day".."$b")"
      [ "$ahead" -gt 0 ] || { echo "  #$i: $b has no commits beyond $day"; continue; }
      if git -C "$dir" diff --name-only --diff-filter=A "$day"..."$b" | grep -qE '(^|/)\.worker-'; then echo "  #$i: $b commits a .worker-* file; fix the branch first"; continue; fi
      if [ -n "$wt" ] && [ -f "$wt/.worker-pr.md" ]; then
        cp "$wt/.worker-pr.md" "$out/folded-$i.md"
      else
        echo "  #$i: no .worker-pr.md; the commit messages become its body"
        { echo "## What changed and why"; echo; git -C "$dir" log --format='%B' "$day".."$b"; echo; echo "Closes #$i"; } > "$out/folded-$i.md"
      fi
      if ! git -C "$dwt" merge --no-ff -q -m "Merge branch '$b'" "$b" 2>/dev/null; then
        git -C "$dwt" merge --abort 2>/dev/null || true; rm -f "$out/folded-$i.md"
        echo "  #$i: $b conflicts with $day; merge it by hand in $dwt (git merge --no-ff $b), resolve, commit, then rerun fold $i"
        continue
      fi
      sha="$(git -C "$dwt" rev-parse --short=10 HEAD)"
      printf '%s\t%s\t%s\t%s\n' "$i" "$b" "$sha" "$(date -u +%FT%TZ)" >> "$out/folded.tsv"
      [ -n "$wt" ] && git -C "$dir" worktree remove --force "$wt"
      git -C "$dir" branch -D "$b" >/dev/null
      echo "  #$i: folded $b into $day at $sha ($ahead commit(s)); branch and worktree removed"
    done
    ;;
  close)
    need_day >/dev/null; dir="$(repo_dir)"; dwt="$(day_wt "$day")"
    as="fix/$dayd"; title=""; push=0; ready=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --as) as="$2"; shift 2 ;; --title) title="$2"; shift 2 ;; --push) push=1; shift ;; --ready) ready=1; shift ;;
        *) echo "loop: unknown close option $1" >&2; exit 2 ;;
      esac
    done
    [ -f "$out/pushed-as" ] && as="$(cat "$out/pushed-as")"
    [ -s "$out/folded.tsv" ] || { echo "loop: nothing folded into $day yet" >&2; exit 3; }
    [ -d "$dwt" ] || { echo "loop: day worktree $dwt is missing" >&2; exit 3; }
    [ -z "$(git -C "$dwt" status --porcelain --untracked-files=no)" ] || { echo "loop: the day worktree has uncommitted changes" >&2; exit 3; }
    issues="$(folded_issues)"; n="$(wc -l <<<"$issues" | tr -d ' ')"
    list="$(sed 's/^/#/' <<<"$issues" | paste -sd, - | sed 's/,/, /g')"
    [ -n "$title" ] || title="fix: $n changes ($list)"
    head_sha="$(git -C "$dwt" rev-parse --short=10 HEAD)"
    echo "checking $day at $head_sha (bun run check, once per tree) ..."
    if ! chk="$(cd "$dwt" && bash "$HOOKS/check-once.sh" 2>&1)"; then
      printf '%s\n' "$chk" | tail -30 >&2; echo "loop: the check failed on $day; fix it in $dwt, then rerun close" >&2; exit 1
    fi
    {
      echo "## What changed and why"; echo
      for i in $issues; do echo "### #$i"; echo; section "$out/folded-$i.md" "What changed and why"; echo; done
      echo "## Verification"; echo
      echo "\`bun run check\` on the pull request head $head_sha:"; echo; echo '```'; printf '%s\n' "$chk" | tail -12; echo '```'; echo
      echo "Each change above passed \`bun run check\` on its own head before it was merged into this branch."; echo
      echo "## Deploy and provider impact"; echo
      dep=0
      for i in $issues; do
        s="$(section "$out/folded-$i.md" "Deploy and provider impact" | sed '/^[[:space:]]*$/d')"
        if [ -n "$s" ] && ! grep -qiE '^(none|no |n/a)' <<<"$s"; then dep=1; echo "- #$i: $(head -1 <<<"$s")"; sed '1d; s/^/  /' <<<"$s"; fi
      done
      [ "$dep" = 1 ] || echo "None beyond the Testing deploy that every merge to \`develop\` performs. No provider effect."
      echo; echo "## Review notes"; echo
      for i in $issues; do
        s="$(section "$out/folded-$i.md" "Review notes" | sed '/^[[:space:]]*$/d')"
        [ -n "$s" ] && { echo "- #$i: $(head -1 <<<"$s")"; sed '1d; s/^/  /' <<<"$s"; }
      done
      echo
      for i in $issues; do echo "Closes #$i"; done
    } > "$out/pr.md"
    echo "wrote $out/pr.md ($n issue(s): $list)"; echo "title: $title"
    if [ "$push" = 0 ]; then
      cat <<EOF

Next, the owner, in a terminal:
  loop.sh close $repo --as $as --push$( [ "$ready" = 1 ] && echo ' --ready')
which runs exactly:
  git -C $dwt push -u origin $day:$as
  gh pr create --repo $repo --base develop --head $as$( [ "$ready" = 1 ] || echo ' --draft') --title "$title" --body-file $out/pr.md
Running close --push again after more folds pushes the update to the same pull request.
EOF
      exit 0
    fi
    owner_terminal
    git -C "$dwt" push -u origin "$day:$as"
    if [ -f "$out/pr-url" ]; then
      echo "pushed $as; pull request $(cat "$out/pr-url") updated (CI runs once more)"
    else
      url="$(cd "$dwt" && "$GHX" "$repo" pr create --base develop --head "$as" $( [ "$ready" = 1 ] || echo --draft ) --title "$title" --body-file "$out/pr.md")"
      echo "$url" > "$out/pr-url"; echo "$as" > "$out/pushed-as"
      echo "opened $url from $as"
    fi
    ;;
  finish)
    owner_terminal; need_day >/dev/null; dir="$(repo_dir)"; dwt="$(day_wt "$day")"
    pr="${1:?pull request number}"
    st="$(gh pr view "$pr" --repo "$repo" --json state,headRefName,baseRefName)"
    [ "$(jq -r .state <<<"$st")" = MERGED ] || { echo "loop: #$pr is not merged (state $(jq -r .state <<<"$st"))" >&2; exit 3; }
    [ "$(jq -r .baseRefName <<<"$st")" = develop ] || echo "loop: warning, #$pr did not target develop" >&2
    head_ref="$(jq -r .headRefName <<<"$st")"
    closed=0
    for i in $(folded_issues); do
      s="$(gh issue view "$i" --repo "$repo" --json state --jq .state 2>/dev/null || echo '?')"
      if [ "$s" = OPEN ]; then "$GHX" "$repo" issue close "$i" --comment "Merged in #$pr." >/dev/null && { echo "  closed #$i"; closed=$((closed+1)); }
      else echo "  #$i already $s"; fi
    done
    if git -C "$dir" push origin --delete "$head_ref" >/dev/null 2>&1; then echo "  deleted origin/$head_ref"; else echo "  origin/$head_ref already gone"; fi
    [ -d "$dwt" ] && git -C "$dir" worktree remove --force "$dwt"
    git -C "$dir" branch -D "$day" >/dev/null 2>&1 || true
    git -C "$dir" fetch -q --prune origin
    mv "$ctl/day-branch" "$out/day-branch.closed"; echo "$pr" > "$out/pr-merged"; echo pause > "$ctl/steer"
    echo "day $day closed: #$pr merged, $closed issue(s) closed, $head_ref and the day worktree removed, steer pause"
    ;;
  tidy)
    apply=0; [ "${1:-}" = --apply ] && apply=1
    dir="$(repo_dir)"; git -C "$dir" fetch -q --prune origin
    live="$(live_worktrees)"
    open_heads="$(gh pr list --repo "$repo" --state open --limit 100 --json headRefName --jq '.[].headRefName')"
    main_sha="$(git -C "$dir" rev-parse origin/main)"
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    protected() { case "$1" in develop|main|HEAD|"$day") return 0 ;; esac; grep -qx "$1" <<<"$open_heads"; }
    merged_or_pointer() { git -C "$dir" merge-base --is-ancestor "$1" origin/develop 2>/dev/null || [ "$(git -C "$dir" rev-parse "$1" 2>/dev/null)" = "$main_sha" ]; }
    echo "TIDY $today $repo"
    echo "remote branches merged into origin/develop:"
    for b in $(git -C "$dir" for-each-ref --format='%(refname:short)' refs/remotes/origin | sed 's#^origin/##'); do
      protected "$b" && continue
      git -C "$dir" merge-base --is-ancestor "origin/$b" origin/develop && { echo "  $b"; echo "$b" >> "$tmp/remote"; }
    done; [ -f "$tmp/remote" ] || echo "  none"
    echo "worktrees that are clean, have no live session, and whose branch is merged or a pointer to main:"
    git -C "$dir" worktree list --porcelain | awk '/^worktree /{p=$2} /^branch /{sub("refs/heads/","",$2); print p, $2} /^detached$/{print p, "(detached)"}' > "$tmp/wts"
    while read -r p b; do
      [ "$p" = "$dir" ] && continue
      case "$p" in */day-*) continue ;; esac
      grep -qx "$p" <<<"$live" && continue
      [ -z "$(git -C "$p" status --porcelain 2>/dev/null)" ] || continue
      if [ "$b" = "(detached)" ] || merged_or_pointer "$b"; then echo "  $p ($b)"; echo "$p" >> "$tmp/wt"; fi
    done < "$tmp/wts"; [ -f "$tmp/wt" ] || echo "  none"
    echo "local branches merged into origin/develop or pointing at main (not checked out elsewhere):"
    for b in $(git -C "$dir" for-each-ref --format='%(refname:short)' refs/heads); do
      protected "$b" && continue
      p="$(awk -v b="$b" '$2==b {print $1}' "$tmp/wts")"
      if [ -n "$p" ] && ! grep -qx "$p" "$tmp/wt" 2>/dev/null; then continue; fi
      merged_or_pointer "$b" && { echo "  $b"; echo "$b" >> "$tmp/local"; }
    done; [ -f "$tmp/local" ] || echo "  none"
    [ "$apply" = 1 ] || { echo; echo "read-only. Apply in a terminal with: loop.sh tidy $repo --apply (bundles first)"; exit 0; }
    owner_terminal
    arch="$ctl/tidy-$today"; mkdir -p "$arch"
    refs="$( { cat "$tmp/local" 2>/dev/null; sed 's#^#origin/#' "$tmp/remote" 2>/dev/null; } | tr '\n' ' ')"
    if [ -n "${refs// /}" ]; then
      # shellcheck disable=SC2086
      git -C "$dir" bundle create "$arch/deleted-branches.bundle" $refs >/dev/null 2>&1
      git -C "$dir" bundle verify "$arch/deleted-branches.bundle" >/dev/null 2>&1 || { echo "loop: bundle verification failed; nothing deleted" >&2; exit 1; }
      { cat "$tmp/local" 2>/dev/null; sed 's#^#origin/#' "$tmp/remote" 2>/dev/null; } > "$arch/deleted-branches.txt"
      echo "bundled $(wc -l < "$arch/deleted-branches.txt" | tr -d ' ') ref(s) to $arch/deleted-branches.bundle (restore: git fetch <bundle> <branch>:<branch>)"
    fi
    for b in $(cat "$tmp/remote" 2>/dev/null); do git -C "$dir" push origin --delete "$b" >/dev/null 2>&1 && echo "  deleted origin/$b" || echo "  FAILED origin/$b"; done
    for p in $(cat "$tmp/wt" 2>/dev/null); do git -C "$dir" worktree remove "$p" >/dev/null 2>&1 && echo "  removed $p" || echo "  FAILED $p"; done
    git -C "$dir" worktree prune
    for b in $(cat "$tmp/local" 2>/dev/null); do git -C "$dir" branch -D "$b" >/dev/null 2>&1 && echo "  deleted $b" || echo "  FAILED $b"; done
    git -C "$dir" fetch -q --prune origin
    echo "result: local $(git -C "$dir" for-each-ref refs/heads | wc -l | tr -d ' '), remote $(git -C "$dir" for-each-ref refs/remotes/origin | grep -vc 'origin/HEAD'), worktrees $(git -C "$dir" worktree list | wc -l | tr -d ' ')"
    ;;
  *) echo "unknown verb $verb" >&2; exit 2 ;;
esac
