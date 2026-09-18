#!/usr/bin/env bash
# check-once: run the repository's `bun run check` once per tree. On success it records the hash
# of the checked tree under the worktree's own git directory (dev-platform/check-pass) and returns
# at once when the tree has not changed since. The Stop hook, a headless worker's final step and
# the loop's close all call it, so one passing run serves all three instead of each running the
# full suite again. It never edits anything.
#
# Usage: check-once.sh            run the check unless this exact tree already passed
#        check-once.sh --status   exit 0 when this exact tree has a recorded pass, else 1; runs nothing
set -uo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] && [ -f "$root/package.json" ] || { echo "check-once: not inside a repository with a package.json" >&2; exit 2; }
grep -q '"check"' "$root/package.json" || { echo "check-once: no check script in package.json; nothing to run"; exit 0; }
cd "$root"
mark="$(git rev-parse --path-format=absolute --git-path dev-platform)"; mkdir -p "$mark"

tree_hash() {  # HEAD plus every tracked change plus the content of untracked, unignored files
  {
    git rev-parse HEAD 2>/dev/null
    git diff HEAD --binary 2>/dev/null
    git ls-files --others --exclude-standard -z | xargs -0 shasum 2>/dev/null
  } | shasum | cut -d' ' -f1
}

h="$(tree_hash)"
if [ -f "$mark/check-pass" ] && [ "$(cat "$mark/check-pass")" = "$h" ]; then
  echo "check-once: bun run check already passed on this tree ($h); log $mark/check.log"
  exit 0
fi
if [ "${1:-}" = "--status" ]; then echo "check-once: no recorded pass for this tree"; exit 1; fi

bun="${BUN_PATH:-$HOME/.bun/bin/bun}"
[ -x "$bun" ] || bun="bun"
rm -f "$mark/check-pass"
if "$bun" run check > "$mark/check.log" 2>&1; then
  tree_hash > "$mark/check-pass"
  tail -n 5 "$mark/check.log"
  echo "check-once: bun run check passed on $(cat "$mark/check-pass"); log $mark/check.log"
  exit 0
fi
tail -n 30 "$mark/check.log" >&2
echo "check-once: bun run check FAILED; log $mark/check.log" >&2
exit 1
