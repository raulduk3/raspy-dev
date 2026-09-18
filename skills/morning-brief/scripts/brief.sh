#!/usr/bin/env bash
# Morning brief (dev-platform skill `morning-brief`, procedure). Read-only. Fixed format.
#
# Sections, in order: pull requests awaiting the owner, open decisions, CI and Testing health,
# the last deploy-log row, new intake since yesterday, the last loop cycle. Reads GitHub through
# the owner's `gh` login (read-only calls only), the VPS through one fixed read-only ssh command,
# and the vault by file modification time. Writes nothing anywhere. Never posts to GitHub.
#
# Usage: brief.sh            (prints the brief on stdout)
#        brief.sh --no-vps   (skip the ssh probe)
set -u
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"
[ -f "$BRIEF_CONF" ] || { echo "brief: missing $BRIEF_CONF" >&2; exit 2; }
. "$BRIEF_CONF"
NO_VPS=0
[ "${1:-}" = "--no-vps" ] && NO_VPS=1

today="$(TZ=America/Chicago date +%Y-%m-%d)"
echo "BRIEF $today"

# 1. Pull requests awaiting the owner, both repositories.
echo "prs:"
for repo in $BRIEF_REPOS; do
  gh pr list --repo "$repo" --state open --limit 40 \
    --json number,title,isDraft,headRefName,statusCheckRollup,reviewDecision 2>/dev/null \
  | jq -r --arg repo "$repo" '
      def checks:
        (.statusCheckRollup // []) as $c
        | if ($c | length) == 0 then "nochecks"
          elif ($c | map(select((.conclusion // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED"))) | length) > 0 then "failing"
          elif ($c | map(select(.status != "COMPLETED")) | length) > 0 then "pending"
          else "green" end;
      .[] | "  \($repo | split("/")[1]) #\(.number) \(if .isDraft then "draft" else "ready" end) \(checks) \(.headRefName) :: \(.title)"
    ' || echo "  $repo: gh read failed"
done

# 2. Open decisions.
echo "decisions:"
gh issue list --repo "$DECISION_REPO" --label decision --state open --limit 40 --json number,title 2>/dev/null \
  | jq -r '.[] | "  #\(.number) \(.title)"' || echo "  gh read failed"

# 3. CI on develop, Testing container, production health.
echo "health:"
gh run list --repo "$CI_REPO" --branch "$CI_BRANCH" --limit 1 --json name,status,conclusion,createdAt,headSha 2>/dev/null \
  | jq -r '.[0] | "  ci develop: \(.name) \(.status)/\(.conclusion // "-") \(.headSha[0:8]) \(.createdAt)"' || echo "  ci develop: gh read failed"
if [ "$NO_VPS" = 1 ]; then
  echo "  testing: skipped (--no-vps)"
else
  vps_out="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$TESTING_SSH" \
    "docker ps --filter 'label=com.docker.compose.project=$TESTING_COMPOSE_PROJECT' --format '{{.Names}} {{.Status}} {{.Image}}'; echo \"::deploy \$(ls -t $TESTING_DEPLOYS_DIR 2>/dev/null | head -1)\"; docker ps --filter 'name=^$PRODUCTION_CONTAINER\$' --format '{{.Status}}'" 2>/dev/null)"
  if [ -z "$vps_out" ]; then
    echo "  testing: vps unreachable"
  else
    printf '%s\n' "$vps_out" | awk '
      /^::deploy/ { print "  testing last deploy: " $2; next }
      NR==1 { print "  testing: " $0; next }
      { print "  production container: " $0 }'
  fi
fi
prod_code="$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$PRODUCTION_HEALTH_URL" 2>/dev/null || echo 000)"
echo "  production /health: $prod_code"

# 4. Last deploy-log row on develop (date, environment, commit, status).
echo "deploy log:"
gh api "repos/$CI_REPO/contents/$DEPLOY_LOG_PATH?ref=$CI_BRANCH" --jq '.content' 2>/dev/null \
  | base64 -d 2>/dev/null | grep -E '^\| 20' | tail -1 \
  | awk -F'|' '{ gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$3); gsub(/^ +| +$/,"",$4); gsub(/^ +| +$/,"",$7); print "  " $2 " " $3 " " $4 " " $7 }' \
  || echo "  unreadable"

# 5. New intake since yesterday: note files under INTAKE_DIRS touched in the last 24h.
echo "intake (24h):"
found=0; IFS=: ; for d in $INTAKE_DIRS; do
  for f in $(find "$d" -type f -name '*.md' -mtime -1 2>/dev/null | head -12); do echo "  ${f##*/Documents/}"; found=1; done
done; unset IFS
[ "$found" = 0 ] && echo "  none"

# 6. The loop's local ledger: open day and steer, then the newest CYCLE report.
echo "loop:"
ctl="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}/${CI_REPO//\//__}"
if [ -f "$ctl/day-branch" ]; then
  echo "  open day: $(head -1 "$ctl/day-branch"), steer: $(head -1 "$ctl/steer" 2>/dev/null || echo 'pause (no file)')"
else
  echo "  no open day (loop.sh start); steer: $(head -1 "$ctl/steer" 2>/dev/null || echo 'pause (no file)')"
fi
last="$(ls -t "$ctl"/*/cycle.md 2>/dev/null | head -1)"
if [ -n "$last" ]; then
  # Everything but the blocks other brief sections already cover (merges, decisions).
  awk '/^(merged today|decisions|lessons):/ {skip=1; next} /^[a-zA-Z]/ {skip=0} !skip' "$last" | sed 's/^/  /'
else
  echo "  no cycle report yet (loop.sh collect)"
fi
