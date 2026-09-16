#!/usr/bin/env bash
# Daily loop, steps 5 and 6 (dev-platform skill `loop`, procedure): collect and report.
#
# Read-only. For every open pull request on a `type/*` branch, reads the PR body (the template)
# and the check state, then prints the cycle comment in the fixed format with its one metrics
# line, plus the exact `gh` command the owner runs to post it. Transcripts are never read here;
# a failing check is reported by its URL for the owner or a worker to open.
#
# Usage: loop-collect.sh [--repo owner/name] [--planned N] [--dispatched N] [--tokens N] [--wall Nm] [--out cycle.md]
set -u
REPO=""
PLANNED=0; DISPATCHED=0; TOKENS="n/a"; WALL="n/a"; OUT=""
LOOP_TITLE="Development loop"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --planned) PLANNED="$2"; shift 2 ;;
    --dispatched) DISPATCHED="$2"; shift 2 ;;
    --tokens) TOKENS="$2"; shift 2 ;;
    --wall) WALL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
[ -n "$REPO" ] || { echo "--repo owner/name is required" >&2; exit 2; }
today="$(TZ=America/Chicago date +%Y-%m-%d)"

prs="$(gh pr list --repo "$REPO" --state open --limit 60 \
  --json number,title,isDraft,headRefName,statusCheckRollup,body,mergedAt \
  | jq -c '
    def checks:
      (.statusCheckRollup // []) as $c
      | if ($c | length) == 0 then "nochecks"
        elif ($c | map(select((.conclusion // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED"))) | length) > 0 then "failing"
        elif ($c | map(select(.status != "COMPLETED")) | length) > 0 then "pending"
        else "green" end;
    .[] | select(.headRefName | test("^(feat|fix|docs|test|refactor|perf|chore|ci)/"))
    | {number, isDraft, headRefName, checks: checks,
       issue: ((.body // "") | capture("(?i)(closes|fixes|resolves) #(?<n>[0-9]+)")? .n // null),
       failing_url: ((.statusCheckRollup // []) | map(select((.conclusion // "") | test("FAILURE|ERROR"))) | .[0].detailsUrl // null)}')"

merged_today="$(gh pr list --repo "$REPO" --state merged --limit 40 --json number,headRefName,mergedAt \
  | jq -r --arg d "$today" '.[] | select((.mergedAt // "") | startswith($d)) | "#\(.number) \(.headRefName)"')"

done_lines=""; waiting_lines=""; blocked_lines=""
green=0; total=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  total=$((total+1))
  n="$(jq -r .number <<<"$p")"; c="$(jq -r .checks <<<"$p")"; d="$(jq -r .isDraft <<<"$p")"
  i="$(jq -r '.issue // "-"' <<<"$p")"; u="$(jq -r '.failing_url // ""' <<<"$p")"
  case "$c" in
    green) green=$((green+1)); done_lines="$done_lines
  issue #$i pr#$n checks green $( [ "$d" = true ] && echo draft || echo ready-for-merge)";;
    pending) waiting_lines="$waiting_lines
  issue #$i pr#$n checks pending";;
    failing) blocked_lines="$blocked_lines
  issue #$i pr#$n checks failing $u";;
    *) waiting_lines="$waiting_lines
  issue #$i pr#$n no checks reported";;
  esac
done <<<"$prs"

decisions="$(gh issue list --repo "$REPO" --label decision --state open --limit 40 --json number,title,createdAt \
  | jq -r --arg d "$today" '.[] | select(.createdAt | startswith($d)) | "  #\(.number) \(.title)"')"

if [ -n "$merged_today" ]; then merged_block="$(sed 's/^/  /' <<<"$merged_today")"; else merged_block="  none"; fi
ndec="$(grep -c '#' <<<"$decisions" || true)"
cycle="CYCLE $today
plan: $PLANNED issue(s) selected, $DISPATCHED dispatched
done:${done_lines:-
  none}
merged today:
$merged_block
waiting:${waiting_lines:-
  none}
blocked:${blocked_lines:-
  none}
decisions:${decisions:-
  none new today}
lessons: 0 appended
metrics: planned $PLANNED dispatched $DISPATCHED prs $total green $green decisions $ndec tokens $TOKENS wall $WALL"

printf '%s\n' "$cycle"
[ -n "$OUT" ] && printf '%s\n' "$cycle" > "$OUT"

loop_num="$(gh issue list --repo "$REPO" --state open --search "\"$LOOP_TITLE\" in:title" --json number,title 2>/dev/null \
  | jq -r --arg t "$LOOP_TITLE" '.[] | select(.title == $t) | .number' | head -1)"
echo
if [ -z "$loop_num" ]; then
  echo "post: no '$LOOP_TITLE' issue exists yet."
else
  echo "post (owner runs; nothing here posts):"
  echo "  gh issue comment $loop_num --repo $REPO --body-file ${OUT:-cycle.md}"
fi
