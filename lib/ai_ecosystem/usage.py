"""Unified usage readout across all four dev-platform accounts.

Codex accounts (`openai-apple`, `openai-gmail`) have a real live signal: the
native Codex app-server exposes `account/rateLimits/read` over stdio JSON-RPC,
and `accounts.py` already probes it. This module never reimplements that
probe; it reuses `environment_service.host_observations`, which already calls
`accounts.status(..., usage=True)` for every account.

Claude accounts (`anthropic-apple`, `anthropic-gmail`) have no such signal:
`claude auth status --json` does not expose quota (see `accounts.probe`). The
only real number comes from `integrations/claude/usage-collector.py`, a
Claude Code status line command that captures the `rate_limits` object Claude
Code hands its status line and caches it to
`~/.local/state/dev-platform/usage/<account>.json`. That cache only updates
while a session is actually running in that account's home, so a Claude
reading is a SNAPSHOT WITH AN AGE, never a live query. See docs/usage.md.

Hard rule carried through this whole module: unknown reads as unknown. A
missing or unparseable cache is never rendered as zero usage, and a cached
number is never labeled "live".
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from . import accounts
from .environment_service import host_observations
from .environments import ACCOUNTS

DEFAULT_CACHE_ROOT = Path.home() / '.local/state/dev-platform/usage'

# Past this age, a cache reading is labeled "stale" rather than just "N minutes
# old". Five-hour subscription windows make anything past half that span a
# reading nobody should treat as current.
STALE_AFTER_SECONDS = 30 * 60

CLAUDE_CLIENT = 'Claude Code'
CODEX_CLIENT = 'Codex'


def cache_path(account, root=None):
    return (root or DEFAULT_CACHE_ROOT) / f'{account}.json'


def _codex_windows(quota):
    """Project accounts.py's quota_fields() rows onto the core `codex` pool's
    primary/secondary windows -- the eligible routing signal per
    environment_service.remaining(). Other pools (e.g. a separate
    model-inference allowance) are real but are a different concern."""
    windows = []
    for pool in quota or []:
        if not isinstance(pool, dict) or pool.get('limit_id') != 'codex':
            continue
        for name in ('primary', 'secondary'):
            window = pool.get(name)
            if isinstance(window, dict) and isinstance(window.get('usedPercent'), (int, float)):
                windows.append({'window': name, 'used_percent': window['usedPercent'],
                                'reset_at': window.get('resetsAt'),
                                'window_minutes': window.get('windowDurationMins')})
    return windows


def _codex_row(observation):
    return {
        'account': observation['account'], 'client': CODEX_CLIENT, 'state': observation['state'],
        'windows': _codex_windows(observation.get('quota')) or None,
        'source': 'live native probe', 'freshness': 'live',
        'reason': observation.get('reason'),
    }


def _load_claude_cache(account, root):
    try:
        raw = cache_path(account, root).read_text()
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _parse_captured_at(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _cache_windows(cache, now):
    """Only windows with a still-future reset are shown. Once `resets_at`
    passes, the reading it described no longer describes the current window
    (usage resets to an unknown starting point) -- so it is dropped, not
    carried forward or zeroed."""
    raw = cache.get('windows') if isinstance(cache.get('windows'), dict) else {}
    windows = []
    for key in ('five_hour', 'seven_day'):
        window = raw.get(key)
        if not isinstance(window, dict):
            continue
        used, resets = window.get('used_percentage'), window.get('resets_at')
        if (not isinstance(used, (int, float)) or isinstance(used, bool)
                or not isinstance(resets, (int, float)) or isinstance(resets, bool)):
            continue
        if resets <= now.timestamp():
            continue
        windows.append({'window': key, 'used_percent': used, 'reset_at': resets})
    return windows


def _claude_row(observation, cache_root, now):
    account, reason = observation['account'], observation.get('reason')
    if observation['state'] != 'quota_unknown':
        # host_observations only reports 'unverified' or 'quota_unknown' for a
        # claude-runtime account (it never computes a claude remaining_percent).
        # An unverified/unbound account gets no cache reading attached: the
        # binding this reading was captured under may not be the one in force.
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'unverified',
                'windows': None, 'source': 'none', 'freshness': 'unknown: account not verified',
                'reason': reason}
    cache = _load_claude_cache(account, cache_root)
    if cache is None:
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                'windows': None, 'source': 'none', 'freshness': 'unknown: no reading yet',
                'reason': 'no status line reading yet; a session must run in this '
                          'account’s home with the collector installed'}
    captured_at = _parse_captured_at(cache.get('captured_at'))
    windows = _cache_windows(cache, now)
    if captured_at is None:
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                'windows': None, 'source': 'status line cache', 'freshness': 'unknown: cache unreadable',
                'reason': 'cached file present but had no valid capture timestamp'}
    age_seconds = max(0.0, (now - captured_at).total_seconds())
    age_minutes = int(age_seconds // 60)
    unit = 'minute' if age_minutes == 1 else 'minutes'
    stale = age_seconds >= STALE_AFTER_SECONDS
    if not windows:
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                'windows': None, 'source': 'status line cache',
                'freshness': f'unknown: last reading’s windows have since reset ({age_minutes} {unit} old)',
                'reason': reason}
    label = f'status line cache, {age_minutes} {unit} old'
    return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'stale' if stale else 'cached',
            'windows': windows, 'source': 'status line cache',
            'freshness': ('stale: ' + label) if stale else label, 'reason': reason}


def unified_view(data, observe=host_observations, cache_root=None, now=None):
    """One row per account in `environments.ACCOUNTS` order. `observe` and
    `now` are injectable so tests never launch a real native probe or depend
    on the wall clock."""
    now = now or datetime.now(timezone.utc)
    rows_by_account = {row['account']: row for row in observe(data)}
    rows = []
    for account in ACCOUNTS:
        observation = rows_by_account.get(account)
        if observation is None:
            rows.append({'account': account, 'client': (CODEX_CLIENT if accounts.runtime(account) == 'codex'
                                                          else CLAUDE_CLIENT), 'state': 'unavailable',
                         'windows': None, 'source': 'none', 'freshness': 'unknown: not observed',
                         'reason': 'account did not appear in the observed set'})
        elif observation['runtime'] == 'codex':
            rows.append(_codex_row(observation))
        else:
            rows.append(_claude_row(observation, cache_root, now))
    return {'observed_at': now.isoformat(), 'accounts': rows}


def _format_windows(windows):
    # Deliberately not merged into fixed "5h/week" columns: Codex and Claude
    # windows are provider-native and not an interchangeable percentage (see
    # docs/AI-ECOSYSTEM-SPEC.md, "Provider-specific windows are not
    # interchangeable percentages"). Each window keeps its own label.
    if not windows:
        return 'unknown'
    parts = []
    for window in windows:
        minutes = window.get('window_minutes')
        span = ' (week)' if minutes == 10080 else (f' ({minutes}m)' if minutes else '')
        reset = window.get('reset_at')
        try:
            reset_text = (datetime.fromtimestamp(reset, timezone.utc).strftime('%m-%d %H:%M UTC')
                          if isinstance(reset, (int, float)) and not isinstance(reset, bool) else 'unknown reset')
        except (ValueError, OverflowError, OSError):
            reset_text = 'unknown reset'
        parts.append(f"{window['window']}{span} {window['used_percent']:.0f}% -> {reset_text}")
    return '; '.join(parts)


def table(view):
    columns = (('ACCOUNT', 20), ('CLIENT', 13), ('STATE', 14), ('FRESHNESS', 40))
    header = ''.join(name.ljust(width) for name, width in columns) + 'WINDOWS'
    lines = [header, '-' * len(header)]
    for row in view['accounts']:
        values = (row['account'], row['client'], row['state'], row['freshness'])
        lines.append(''.join(str(value).ljust(width) for value, (_, width) in zip(values, columns))
                     + _format_windows(row['windows']))
    lines.append('Observed: ' + view['observed_at'])
    lines.append('Unknown is not zero. A cached Claude reading is a snapshot with an age, never a live query.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=Path.home() / '.config/dev-platform/accounts.json')
    parser.add_argument('--json', action='store_true', help='Emit the full structured view instead of the table')
    args = parser.parse_args(argv)
    try:
        data = accounts.load(args.registry)
        view = unified_view(data)
        print(json.dumps(view, indent=2) if args.json else table(view))
        return 0
    except (OSError, ValueError) as error:
        print('ai-usage: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
