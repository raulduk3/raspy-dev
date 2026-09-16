#!/usr/bin/env bash
# Daily loop, steps 1 to 3 (dev-platform skill `loop`, procedure): sense, plan, gate.
#
# Read-only. Reads open issues, open pull requests and their checks. Parses the two plain lines
# every implementable issue carries (`Scope: <path prefixes>` and `Depends on: #N, #M | none`),
# builds the dependency graph, selects `sprint-ready` issues whose dependencies are closed and
# whose scopes are pairwise prefix-disjoint, up to the caps, and prints the plan comment in the
# fixed format plus the exact `gh` command the owner runs to post it (nothing here posts).
# The gate is hard: dispatch waits for a `steer: go` comment on the loop issue.
#
# Usage: loop-sense.sh [--repo owner/name] [--local-cap 3] [--out plan.md]
set -u
REPO=""
LOCAL_CAP=3
OUT=""
LOOP_TITLE="Development loop"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --local-cap) LOCAL_CAP="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
[ -n "$REPO" ] || { echo "--repo owner/name is required" >&2; exit 2; }
today="$(TZ=America/Chicago date +%Y-%m-%d)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

gh issue list --repo "$REPO" --state open --limit 200 --json number,title,labels,body,milestone \
  > "$tmp/issues.json" || { echo "gh issue list failed" >&2; exit 1; }
gh issue list --repo "$REPO" --state closed --limit 300 --json number > "$tmp/closed.json" || exit 1
gh pr list --repo "$REPO" --state open --limit 60 --json number,title,isDraft,headRefName,statusCheckRollup,body \
  > "$tmp/prs.json" || exit 1

# Parse Scope / Depends on lines. An issue with neither line is not implementable by the loop.
jq -c '
  .[] | {
    number, title,
    labels: [.labels[].name],
    milestone: (.milestone.title // null),
    scope: ((.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // null),
    depends: ((.body // "") | capture("(?m)^Depends on: *(?<d>[^\n]+)")? .d // null)
  }' "$tmp/issues.json" > "$tmp/parsed.jsonl"

closed_set="$(jq -r '.[].number' "$tmp/closed.json" | tr '\n' ' ')"
is_closed() { case " $closed_set " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# Candidates: sprint-ready with both lines present.
selected=(); selected_scopes=(); skipped=()
while IFS= read -r row; do
  n="$(jq -r .number <<<"$row")"
  labels="$(jq -r '.labels | join(",")' <<<"$row")"
  case ",$labels," in *",sprint-ready,"*) ;; *) continue ;; esac
  scope="$(jq -r '.scope // ""' <<<"$row")"
  deps="$(jq -r '.depends // ""' <<<"$row")"
  if [ -z "$scope" ] || [ -z "$deps" ]; then skipped+=("#$n missing Scope/Depends line"); continue; fi
  # Dependencies satisfied: every #N closed, or the literal `none`.
  unmet=""
  if [ "$deps" != "none" ]; then
    for d in $(grep -oE '#[0-9]+' <<<"$deps" | tr -d '#'); do is_closed "$d" || unmet="$unmet #$d"; done
  fi
  if [ -n "$unmet" ]; then skipped+=("#$n waits on$unmet"); continue; fi
  # Scope disjointness against already selected issues (pairwise prefix check).
  conflict=""
  for p in $(tr ',' ' ' <<<"$scope"); do
    for q in "${selected_scopes[@]:-}"; do
      [ -z "$q" ] && continue
      case "$p" in "$q"*) conflict="$q" ;; esac
      case "$q" in "$p"*) conflict="$q" ;; esac
    done
  done
  if [ -n "$conflict" ]; then skipped+=("#$n scope overlaps $conflict"); continue; fi
  if [ "${#selected[@]}" -ge "$LOCAL_CAP" ]; then skipped+=("#$n over local cap $LOCAL_CAP"); continue; fi
  selected+=("$n")
  for p in $(tr ',' ' ' <<<"$scope"); do selected_scopes+=("$p"); done
done < "$tmp/parsed.jsonl"

# Open PRs and their check state (the owner's review queue).
pr_lines="$(jq -r '
  def checks:
    (.statusCheckRollup // []) as $c
    | if ($c | length) == 0 then "nochecks"
      elif ($c | map(select((.conclusion // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED"))) | length) > 0 then "failing"
      elif ($c | map(select(.status != "COMPLETED")) | length) > 0 then "pending"
      else "green" end;
  .[] | "#\(.number) \(if .isDraft then "draft" else "ready" end) \(checks) \(.headRefName)"' "$tmp/prs.json")"

plan="PLAN $today
repo: $REPO
select:"
if [ "${#selected[@]}" -eq 0 ]; then
  plan="$plan
  none (no sprint-ready issue with Scope and Depends lines whose dependencies are closed)"
else
  for n in "${selected[@]}"; do
    row="$(grep "\"number\":$n," "$tmp/parsed.jsonl" | head -1)"
    t="$(jq -r .title <<<"$row")"; s="$(jq -r .scope <<<"$row")"
    slug="$(tr '[:upper:]' '[:lower:]' <<<"$t" | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-40)"
    plan="$plan
  #$n lane=fleet tier=implementation branch=fix/$slug scope=$s"
  done
fi
plan="$plan
skipped:"
if [ "${#skipped[@]}" -eq 0 ]; then plan="$plan
  none"; else for s in "${skipped[@]}"; do plan="$plan
  $s"; done; fi
plan="$plan
review queue (owner):
$(sed 's/^/  /' <<<"$pr_lines")
caps: local $LOCAL_CAP workers, one ops session, stop on quota error
gate: hard. Reply \`steer: go\` on this issue to dispatch; \`steer: skip <n>\`, \`only <n>\`, \`pause\` also honored."

printf '%s\n' "$plan"
[ -n "$OUT" ] && printf '%s\n' "$plan" > "$OUT"

loop_num="$(gh issue list --repo "$REPO" --state open --search "\"$LOOP_TITLE\" in:title" --json number,title 2>/dev/null \
  | jq -r --arg t "$LOOP_TITLE" '.[] | select(.title == $t) | .number' | head -1)"
echo
if [ -z "$loop_num" ]; then
  echo "post: no '$LOOP_TITLE' issue exists yet; run loop.sh start."
else
  echo "post (owner runs; nothing here posts):"
  echo "  gh issue comment $loop_num --repo $REPO --body-file ${OUT:-plan.md}"
fi
