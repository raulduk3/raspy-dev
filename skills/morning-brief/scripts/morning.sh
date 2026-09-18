#!/usr/bin/env bash
# Morning delivery: the brief followed by today's loop plan. Read-only. Output is delivered to
# the owner by a scheduled command; nothing is posted to GitHub. The brief lands under
# LOOP_STATE_DIR/<date>/brief.md; the plan under the repository's ledger directory.
set -u
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"; . "$BRIEF_CONF"
state="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}"
today="$(TZ=America/Chicago date +%Y-%m-%d)"; mkdir -p "$state/$today"
"$here/brief.sh" 2>&1 | tee "$state/$today/brief.md"
echo
"$here/../../loop/scripts/loop.sh" plan "$CI_REPO" 2>&1
