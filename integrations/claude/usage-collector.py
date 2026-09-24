#!/usr/bin/env python3
"""Claude Code status line command: captures subscription usage, nothing else.

Installed as the `statusLine` command for one account's native home by the
account-provisioning tool (a separate task owns that wiring). Claude Code
invokes this on every render of that status line and pipes it the documented
JSON payload on stdin (see the schema comment embedded in the installed
`claude` binary, keys `rate_limits.five_hour` / `rate_limits.seven_day`, each
`{used_percentage, resets_at}` with `resets_at` as Unix epoch seconds).

Contract with the provisioning tool: invoked as
    python3 <platform-root>/integrations/claude/usage-collector.py --account <account-id>
writing its cache to ~/.local/state/dev-platform/usage/<account-id>.json.

Hard rules, because this runs inline in a live Claude Code render loop:
  - Never crash the session. Any malformed input, missing flag, or write
    failure prints one harmless line and exits 0. Never a non-zero exit.
  - Never write a token, credential, or transcript-shaped value to the cache.
    Only the account id, a capture timestamp, and the two rate-limit windows
    are written. cwd/session_id/transcript_path/etc. from the payload are
    never touched.
  - Unknown stays unknown: if the payload has no valid rate-limit window, the
    cache is left as-is (an old real reading is not clobbered by a blank one
    that just means "no subscription data yet").
"""
import json
import os
import re
import sys
import tempfile
import time

MAX_INPUT_BYTES = 2_000_000
ACCOUNT_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
FALLBACK_LINE = 'claude usage: unavailable'
NO_READING_LINE = 'claude usage: no reading yet'
CACHE_ROOT = os.path.join(os.path.expanduser('~'), '.local', 'state', 'dev-platform', 'usage')


def parse_account(argv):
    for index, arg in enumerate(argv):
        if arg == '--account' and index + 1 < len(argv):
            candidate = argv[index + 1]
        elif arg.startswith('--account='):
            candidate = arg.split('=', 1)[1]
        else:
            continue
        if isinstance(candidate, str) and ACCOUNT_PATTERN.match(candidate):
            return candidate
        return None
    return None


def read_payload():
    data = sys.stdin.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        return None
    try:
        payload = json.loads(data)
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def extract_windows(payload):
    """Only two numeric fields per window ever leave this function: no other payload content."""
    rate_limits = payload.get('rate_limits')
    if not isinstance(rate_limits, dict):
        return {}
    windows = {}
    for key in ('five_hour', 'seven_day'):
        window = rate_limits.get(key)
        if not isinstance(window, dict):
            continue
        used = window.get('used_percentage')
        resets = window.get('resets_at')
        if (isinstance(used, (int, float)) and not isinstance(used, bool)
                and isinstance(resets, (int, float)) and not isinstance(resets, bool)):
            windows[key] = {'used_percentage': float(used), 'resets_at': int(resets)}
    return windows


def safe_version(payload):
    version = payload.get('version')
    if isinstance(version, str) and 0 < len(version) <= 32 and re.fullmatch(r'[\w.+-]+', version):
        return version
    return None


def write_cache_atomic(account, windows, claude_version):
    os.makedirs(CACHE_ROOT, exist_ok=True, mode=0o700)
    os.chmod(CACHE_ROOT, 0o700)  # mkdir's mode is subject to umask; enforce it explicitly.
    cache = {
        'account': account,
        'captured_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source': 'claude-code-statusline',
        'windows': windows,
    }
    if claude_version:
        cache['claude_version'] = claude_version
    target = os.path.join(CACHE_ROOT, account + '.json')
    descriptor, temporary = tempfile.mkstemp(prefix='.usage-', dir=CACHE_ROOT)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(cache, stream)
            stream.write('\n')
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    os.chmod(target, 0o600)


def format_line(windows):
    parts = []
    if 'five_hour' in windows:
        parts.append('5h %d%%' % round(windows['five_hour']['used_percentage']))
    if 'seven_day' in windows:
        parts.append('7d %d%%' % round(windows['seven_day']['used_percentage']))
    return 'claude usage: ' + ' | '.join(parts) if parts else NO_READING_LINE


def collect(argv):
    account = parse_account(argv)
    payload = read_payload()
    if payload is None:
        return FALLBACK_LINE
    windows = extract_windows(payload)
    if not windows:
        # A session before its first API response, or a non-subscriber, carries
        # no rate_limits window. That is not an error; leave any existing cache
        # (a real prior reading) untouched rather than overwrite it with nothing.
        return NO_READING_LINE
    if account is not None:
        write_cache_atomic(account, windows, safe_version(payload))
    return format_line(windows)


def main(argv):
    try:
        line = collect(argv)
    except BaseException:
        line = FALLBACK_LINE
    try:
        print(line)
    except BaseException:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
