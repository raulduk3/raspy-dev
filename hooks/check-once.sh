#!/usr/bin/env bash
# check-once: run the repository's check (bin/check, else `bun run check`) once per tree. On success it records the hash
# of the checked tree under the worktree's own git directory (dev-platform/check-pass) and returns
# at once when the tree has not changed since. The Stop hook, a headless worker's final step and
# the loop's close all call it, so one passing run serves all three instead of each running the
# full suite again. It never edits anything.
#
# Usage: check-once.sh            run the check unless this exact tree already passed
#        check-once.sh --status   exit 0 when this exact tree has a recorded pass, else 1; runs nothing
set -uo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] || { echo "check-once: not inside a repository" >&2; exit 2; }
cd "$root"
# The check command: the repository's bin/check when it has one, else `bun run check`.
if [ -x "$root/bin/check" ]; then
  check_cmd=("$root/bin/check")
elif [ -f "$root/package.json" ] && grep -q '"check"' "$root/package.json"; then
  bun="${BUN_PATH:-$HOME/.bun/bin/bun}"; [ -x "$bun" ] || bun="bun"
  check_cmd=("$bun" run check)
else
  echo "check-once: no bin/check and no check script in package.json; nothing to run"; exit 0
fi
# Per-repository environment (toolchain on PATH, test database DSN), keyed by the main checkout's
# name so every worktree of the repository shares it: ~/.config/dev-platform/env.d/<repo>.sh
repo_name="$(basename "$(dirname "$(git rev-parse --git-common-dir)")")"
env_file="$HOME/.config/dev-platform/env.d/$repo_name.sh"
[ -f "$env_file" ] && . "$env_file"
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
  echo "check-once: check already passed on this tree ($h); log $mark/check.log"
  exit 0
fi
if [ "${1:-}" = "--status" ]; then echo "check-once: no recorded pass for this tree"; exit 1; fi

rm -f "$mark/check-pass"
if "${check_cmd[@]}" > "$mark/check.log" 2>&1; then
  tree_hash > "$mark/check-pass"
  tail -n 5 "$mark/check.log"
  echo "check-once: check passed on $(cat "$mark/check-pass"); log $mark/check.log"
  exit 0
fi
tail -n 30 "$mark/check.log" >&2
echo "check-once: check FAILED; log $mark/check.log" >&2
exit 1
