#!/usr/bin/env bash
# Morning delivery: the brief followed by today's loop plan. Read-only. Output is delivered to
# the owner by a scheduled command; nothing is posted to GitHub.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"; . "$BRIEF_CONF"
state="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}"
today="$(TZ=America/Chicago date +%Y-%m-%d)"; mkdir -p "$state/$today"
"$here/brief.sh" 2>&1 | tee "$state/$today/brief.md"
echo
"$here/../../loop/scripts/loop-sense.sh" --repo "$CI_REPO" --out "$state/$today/plan.md" 2>&1 | sed '/^post/,$d'
