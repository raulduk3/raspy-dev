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
import sqlite3
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


def _parse_iso(value):
    """ISO 8601 with a trailing Z, with or without fractional seconds (OpenRig writes ms)."""
    if not isinstance(value, str) or not value.endswith('Z'):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        return None


def openrig_seat_readings(openrig_home):
    """OpenRig's own status line cache: one `{seatSession, asOf, rateLimits}` file per seat under
    `state/provider-usage/`. The daemon database maps a seat to its node's `config_home`, so a
    reading can be attributed to the account whose home that seat actually ran in. Read-only:
    the database is opened in read-only mode and nothing is written. A seat whose runtime is
    not Claude, or whose file carries no windows, contributes nothing."""
    usage_dir = Path(openrig_home) / 'state' / 'provider-usage'
    db = Path(openrig_home) / 'openrig.sqlite'
    if not usage_dir.is_dir() or not db.is_file():
        return []
    try:
        conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        try:
            rows = conn.execute('SELECT s.session_name, n.runtime, n.config_home FROM sessions s '
                                'JOIN nodes n ON n.id = s.node_id').fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    seats = {name: (runtime, home) for name, runtime, home in rows}
    readings = []
    for path in sorted(usage_dir.glob('*.json')):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        seat = data.get('seatSession') if isinstance(data, dict) else None
        if seat not in seats or seats[seat][0] != 'claude-code':
            continue
        limits = data.get('rateLimits')
        windows = {}
        if isinstance(limits, dict):
            for key in ('five_hour', 'seven_day'):
                window = limits.get(key)
                if not isinstance(window, dict):
                    continue
                used, reset = window.get('usedPercent'), _parse_iso(window.get('resetsAt'))
                if isinstance(used, (int, float)) and not isinstance(used, bool) and reset is not None:
                    windows[key] = {'used_percentage': used, 'resets_at': reset.timestamp()}
        captured_at = _parse_iso(data.get('asOf'))
        if captured_at is None or not windows:
            continue
        readings.append({'seat': seat, 'config_home': seats[seat][1], 'captured_at': captured_at,
                         'windows': windows})
    return readings


def _seat_readings_for(account, data, readings):
    """Attribute seat readings to one Claude account by home: a pinned `config_home` matches
    that account's registered home; an unpinned seat ran in the daemon's default home, which
    is the account bound with `native_default`."""
    if not readings:
        return []
    binding = data['bindings'].get(account) or {}
    home = str(accounts.home_for(data, account))
    matches = []
    for reading in readings:
        pinned = reading['config_home']
        if pinned is None:
            if binding.get('native_default'):
                matches.append(reading)
        elif str(Path(pinned).expanduser().resolve()) == home:
            matches.append(reading)
    return matches


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


def _claude_row(observation, cache_root, now, seat_readings=None):
    account, reason = observation['account'], observation.get('reason')
    if observation['state'] != 'quota_unknown':
        # host_observations only reports 'unverified' or 'quota_unknown' for a
        # claude-runtime account (it never computes a claude remaining_percent).
        # An unverified/unbound account gets no cache reading attached: the
        # binding this reading was captured under may not be the one in force.
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'unverified',
                'windows': None, 'source': 'none', 'freshness': 'unknown: account not verified',
                'reason': reason}
    # Two sources, same shape once normalized: the platform's own collector cache, and
    # OpenRig's seat-keyed cache for seats that ran in this account's home. The freshest
    # reading that still has a live window wins; the source is named in the row.
    candidates = []
    cache = _load_claude_cache(account, cache_root)
    if cache is not None:
        captured_at = _parse_captured_at(cache.get('captured_at'))
        if captured_at is None:
            return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                    'windows': None, 'source': 'status line cache', 'freshness': 'unknown: cache unreadable',
                    'reason': 'cached file present but had no valid capture timestamp'}
        candidates.append((captured_at, _cache_windows(cache, now), 'status line cache'))
    for reading in seat_readings or []:
        candidates.append((reading['captured_at'], _cache_windows(reading, now),
                           'OpenRig seat ' + reading['seat']))
    if not candidates:
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                'windows': None, 'source': 'none', 'freshness': 'unknown: no reading yet',
                'reason': 'no status line reading yet; a session must run in this '
                          'account’s home with the collector installed'}
    live = [c for c in candidates if c[1]]
    captured_at, windows, source = max(live or candidates, key=lambda c: c[0])
    age_seconds = max(0.0, (now - captured_at).total_seconds())
    age_minutes = int(age_seconds // 60)
    unit = 'minute' if age_minutes == 1 else 'minutes'
    stale = age_seconds >= STALE_AFTER_SECONDS
    if not windows:
        return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'quota_unknown',
                'windows': None, 'source': source,
                'freshness': f'unknown: last reading’s windows have since reset ({age_minutes} {unit} old)',
                'reason': reason}
    label = f'{source}, {age_minutes} {unit} old'
    return {'account': account, 'client': CLAUDE_CLIENT, 'state': 'stale' if stale else 'cached',
            'windows': windows, 'source': source,
            'freshness': ('stale: ' + label) if stale else label, 'reason': reason}


def unified_view(data, observe=host_observations, cache_root=None, now=None, openrig_home=None):
    """One row per account in `environments.ACCOUNTS` order. `observe`, `now`
    and `openrig_home` are injectable so tests never launch a real native
    probe, depend on the wall clock, or read the real OpenRig state. With
    `openrig_home` unset the OpenRig source is simply absent."""
    now = now or datetime.now(timezone.utc)
    readings = openrig_seat_readings(openrig_home) if openrig_home else []
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
            rows.append(_claude_row(observation, cache_root, now, _seat_readings_for(account, data, readings)))
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
        parts.append(f"{window['window']}{span} {window['used_percent']:.0f}% used -> {reset_text}")
    return '; '.join(parts)


def table(view):
    columns = (('ACCOUNT', 20), ('CLIENT', 13), ('STATE', 14), ('FRESHNESS', 40))
    header = ''.join(name.ljust(width) for name, width in columns) + 'WINDOWS (PERCENT USED)'
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
        view = unified_view(data, openrig_home=Path.home() / '.openrig')
        print(json.dumps(view, indent=2) if args.json else table(view))
        return 0
    except (OSError, ValueError) as error:
        print('ai-usage: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
