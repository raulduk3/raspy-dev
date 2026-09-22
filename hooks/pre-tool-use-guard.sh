#!/usr/bin/env bash
# Claude Code PreToolUse hook for the Bash tool: refuse the commands an agent must never run.
#
# Reads the hook input on stdin (JSON with tool_name and tool_input.command), exits 2 with the
# reason on stderr to block, exits 0 to allow. Blocked, regardless of repository:
#   - git push to develop or main (any spelling: `git push origin develop`, `git push -f origin
#     HEAD:main`, refspecs, `--force` to any protected ref);
#   - force pushes, and history rewrites of anything shared: push --force*, rebase, reset --hard,
#     commit --amend, filter-branch;
#   - merges into develop or main and gh pr merge;
#   - docker compose up/restart/down/stop, docker restart/stop/kill, systemctl restart/stop;
#   - ssh as root, and any ssh command that restarts, deploys or stops something.
# An operator who needs one of these runs it in a terminal, not through the agent. Set
# DEV_PLATFORM_ALLOW_MUTATIONS=1 in the agent's environment to lift the ssh and docker rules for a
# session the owner is driving.
#
# A repository whose own policy lets its author merge is listed, one absolute path per line, in
# ~/.config/dev-platform/merge-allowed.conf. Inside such a repository the develop rules lift: push
# to develop, merge into develop and gh pr merge are allowed. Everything about main, force pushes
# and history rewrites still applies everywhere, and so do the docker and ssh rules.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
[ -n "$command" ] || exit 0
cwd="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cwd",""))' 2>/dev/null || true)"

# Repositories whose own policy lets the author merge to develop.
allow_merge=0
allowlist="$HOME/.config/dev-platform/merge-allowed.conf"
if [ -n "$cwd" ] && [ -f "$allowlist" ]; then
  repo_root="$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  repo_root="${repo_root%/.git}"
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue ;; esac
    entry="${line/#\~/$HOME}"
    case "$repo_root/" in "$entry"/*) allow_merge=1 ;; esac
    case "$cwd/" in "$entry"/*) allow_merge=1 ;; esac
  done < "$allowlist"
fi

refuse() {
  printf 'dev-platform guard: %s\n' "$1" >&2
  exit 2
}

# Normalize whitespace for matching; keep the original for messages.
flat="$(printf '%s' "$command" | tr '\n' ' ' | tr -s ' ')"

# git push to a protected branch, in any form.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +push\b'; then
  if printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(\bmain\b|:refs/heads/main\b|:main\b)'; then
    refuse "git push to main is refused; main carries releases and is the owner's"
  fi
  if [ "$allow_merge" != "1" ] && printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(\bdevelop\b|:refs/heads/develop\b|:develop\b)'; then
    refuse "git push to develop is refused; open a pull request from a type/short-description branch"
  fi
  if printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(--force|-f\b|--force-with-lease|\+[a-zA-Z0-9_./-]+:)'; then
    refuse "force push is refused; nothing pushed for review is rewritten"
  fi
  if [ "$allow_merge" != "1" ] && ! printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(-u |--set-upstream|origin +[a-zA-Z]+/|origin +HEAD|origin +refs/heads/[a-z]+/|refs/heads/[a-z]+/)'; then
    # A bare `git push` follows the branch's upstream, which may be develop or main.
    refuse "bare git push is refused; name the branch: git push -u origin <type/short-description>"
  fi
fi

# History rewrites of shared commits.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(rebase|filter-branch|reset +--hard|commit +--amend|commit +[^;&|]*--amend)\b'; then
  refuse "history rewrite is refused (rebase, reset --hard, commit --amend, filter-branch)"
fi

# Merges into protected branches and merging pull requests.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(checkout|switch) +main\b *[;&|] *git +merge\b'; then
  refuse "merging into main is refused; the owner merges main"
fi
if [ "$allow_merge" != "1" ]; then
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(checkout|switch) +develop\b *[;&|] *git +merge\b'; then
    refuse "merging into develop is refused; the owner merges"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)gh +pr +(merge|ready|review +[^;&|]*--approve)\b'; then
    refuse "gh pr merge, ready and approve are refused; the owner reviews, marks ready and merges"
  fi
fi

if [ "${DEV_PLATFORM_ALLOW_MUTATIONS:-0}" != "1" ]; then
  # Container and service mutations.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)(docker +compose|docker-compose)[^;&|]*\b(up|restart|down|stop|kill|rm)\b'; then
    refuse "docker compose up/restart/down/stop is refused; deploys and restarts are the owner's, in a terminal"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)docker +(restart|stop|kill|rm|run +[^;&|]*--restart)\b'; then
    refuse "docker restart/stop/kill/rm is refused"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)(sudo +)?systemctl +(restart|stop|start|reload|disable|enable)\b'; then
    refuse "systemctl mutations are refused"
  fi
  # Remote mutations.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)ssh +[^;&|]*\broot@'; then
    refuse "ssh as root is refused"
  fi
  # The remote command is what follows the host (`user@host cmd …`); a user named deploy is fine.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)ssh +[^;&|]*@[^ ]+ +[^;&|]*\b(docker|systemctl|restart|deploy|reboot|shutdown|rm +-rf|compose)\b'; then
    refuse "an ssh command that restarts, deploys or removes something is refused; read-only diagnostics only"
  fi
fi

exit 0
