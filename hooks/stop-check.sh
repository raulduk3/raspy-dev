#!/usr/bin/env bash
# Claude Code Stop hook: when the session ends inside a repository whose package.json has a
# `check` script and the tree has changes, run `bun run check` and report the result. It blocks
# the stop (exit 2) only when the check fails, so the agent reports the failure instead of
# stopping over a red tree. It never edits anything.
set -uo pipefail
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] && [ -f "$root/package.json" ] || exit 0
grep -q '"check"' "$root/package.json" || exit 0
if [ -z "$(cd "$root" && git status --porcelain --untracked-files=no)" ] && [ -z "$(cd "$root" && git log --oneline @{upstream}..HEAD 2>/dev/null)" ]; then
  exit 0
fi
bun="${BUN_PATH:-$HOME/.bun/bin/bun}"
[ -x "$bun" ] || bun="bun"
log="$(mktemp -t dev-platform-check.XXXXXX)"
if (cd "$root" && "$bun" run check >"$log" 2>&1); then
  printf 'dev-platform: bun run check passed in %s\n' "$root"
  rm -f "$log"
  exit 0
fi
printf 'dev-platform: bun run check FAILED in %s; last lines:\n' "$root" >&2
tail -n 30 "$log" >&2
rm -f "$log"
exit 2
