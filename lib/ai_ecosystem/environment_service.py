#!/usr/bin/env python3
"""One-shot account readiness for callers; never replays work or swaps credentials."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from .accounts import save
from .environments import ACCOUNTS

# Reuse the native account probe inside the selected container, where its own
# credentials and binaries live. No provider tokens travel back to the caller.
PROBE = '''
import hashlib
try:
    value = probe(ACCOUNT, Path('/home/node/.codex' if ACCOUNT.startswith('openai-') else '/home/node/.claude'), usage=True)
    email = value.pop('email', None)
    value['identity'] = hashlib.sha256(email.casefold().encode()).hexdigest() if email else None
    print(json.dumps(value))
except Exception:
    print(json.dumps({'error': 'native_probe_unavailable'}))
'''


def container(name):
    return 'iztac-account-environments-' + name + '-1'


def registry(root):
    path = root / 'readiness.json'
    return json.loads(path.read_text()) if path.exists() else {'identities': {}}


def remaining(quota):
    # The core Codex pool is the only eligible routing signal. Separate model
    # pools must not be mistaken for an interchangeable core allowance.
    pools = [p for p in quota or [] if p.get('limit_id') == 'codex']
    windows = [p[w] for p in pools for w in ('primary', 'secondary') if w in p]
    values = [w['usedPercent'] for w in windows if isinstance(w.get('usedPercent'), (int, float))]
    return max(0, min(100, 100 - max(values))) if values else None


def observe(name, expected=None, root=None):
    row = {'account': name, 'runtime': 'codex' if name.startswith('openai-') else 'claude',
           'state': 'unavailable', 'observed_at': time.time(), 'remaining_percent': None,
           'capabilities': {'codex': 'unverified', 'claude': 'unverified', 'pi': 'unverified'}}
    try:
        inspected = subprocess.run(['docker', 'inspect', container(name)], capture_output=True, text=True, timeout=8)
        if inspected.returncode:
            return dict(row, reason='Docker or container unavailable; retry after Docker starts')
        inspection = json.loads(inspected.stdout)[0]
        if root is not None:
            mounts = {m['Destination']: m['Source'] for m in inspection['Mounts']}
            if mounts.get('/home/node') != str(root / name / 'home'):
                return dict(row, state='storage_mismatch', reason='running home does not match declared environment root')
        state = inspection['State']
        if not state['Running']:
            return dict(row, reason='container stopped; history retained; no automatic work replay')
        port = 17433 + ACCOUNTS.index(name)
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
            if response.status != 200:
                return dict(row, reason='OpenRig daemon unavailable')
        command = ['codex', 'login', 'status'] if row['runtime'] == 'codex' else ['claude', 'auth', 'status', '--json']
        login = subprocess.run(['docker', 'exec', container(name), *command], capture_output=True, text=True, timeout=15)
        if row['runtime'] == 'claude':
            authenticated = bool(json.loads(login.stdout).get('loggedIn'))
        else:
            authenticated = login.returncode == 0
        if not authenticated:
            return dict(row, state='login_required', reason='complete native login in this environment')
        source = (Path(__file__).with_name('accounts.py')).read_text()
        script = source + '\nACCOUNT = ' + repr(name) + '\n' + PROBE
        probe = subprocess.run(['docker', 'exec', '-i', container(name), 'python3', '-'], input=script,
                               capture_output=True, text=True, timeout=45)
        native = json.loads(probe.stdout)
        if native.get('error') or not native.get('identity'):
            return dict(row, state='probe_unavailable', reason='native identity or provider status unavailable; do not infer logout')
        identity = native.pop('identity')
        row.update(identity_fingerprint=identity, plan=native.get('plan'), quota=native.get('quota'),
                   container=container(name), image=inspection['Config']['Image'])
        if expected is None:
            return dict(row, state='unenrolled', reason='explicit enrollment required')
        if identity != expected:
            return dict(row, state='identity_mismatch', reason='login differs from enrolled account; new work refused')
        row['capabilities'][row['runtime']] = 'authenticated'
        left = remaining(native.get('quota'))
        row['remaining_percent'] = left
        if left is None:
            return dict(row, state='quota_unknown', reason=native.get('quota_reason') or 'usage unavailable')
        return dict(row, state='ready' if left > 0 else 'exhausted', reason='native quota observation')
    except (OSError, ValueError, subprocess.SubprocessError):
        return dict(row, reason='health probe unavailable; retry later; saved sessions unchanged')


def choose(rows, runtime):
    eligible = [r for r in rows if r['runtime'] == runtime and r['state'] == 'ready']
    return max(eligible, key=lambda r: r['remaining_percent']) if eligible else None


def launch_plan(rows, root, client, provider, preferred=None, allow_unknown=False):
    if client == 'pi':
        return {'version': 1, 'client': client, 'provider': provider, 'execution_kind': 'host',
                'selected': None, 'launch_allowed': False, 'observed_at': time.time(),
                'reason': 'host-native Pi profile and authentication integration pending; container fallback refused'}
    runtime = 'codex' if provider == 'openai' else 'claude'
    candidates = [r for r in rows if r['runtime'] == runtime]
    if preferred:
        candidates = [r for r in candidates if r['account'] == preferred]
    selected = choose(candidates, runtime)
    if selected is None and allow_unknown and preferred:
        selected = next((r for r in candidates if r['state'] == 'quota_unknown'), None)
    capability = runtime if client == 'openrig' else client
    allowed = bool(selected and selected['capabilities'].get(capability) == 'authenticated')
    result = {'version': 1, 'client': client, 'provider': provider,
              'selected': selected['account'] if selected else None, 'execution_kind': 'container',
              'launch_allowed': allowed, 'observed_at': time.time(),
              'reason': 'account preflight passed' if allowed else 'no eligible environment or client authentication unverified',
              'scope': 'new or explicitly resumed execution only; never replay interrupted turns'}
    if selected:
        account = selected['account']
        result.update(container=selected['container'], image=selected['image'],
                      readiness=selected['state'], capabilities=selected['capabilities'],
                      quota=selected['quota'], quota_observed_at=selected['observed_at'],
                      mounts=[{'host': str(root / account / name), 'container': target}
                              for name, target in [('home', '/home/node'), ('workspace', '/workspace')]])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('enroll')
    plan = sub.add_parser('plan')
    plan.add_argument('--client', required=True, choices=('pi', 'openrig', 'codex', 'claude'))
    plan.add_argument('--provider', required=True, choices=('openai', 'anthropic'))
    plan.add_argument('--preferred-account', choices=ACCOUNTS)
    plan.add_argument('--allow-unknown-quota', action='store_true')
    select = sub.add_parser('choose')
    select.add_argument('runtime', choices=('codex', 'claude'))
    args = p.parse_args()
    root = args.root.expanduser().resolve()
    if args.command == 'plan' and args.client == 'pi':
        print(json.dumps(launch_plan([], root, 'pi', args.provider), indent=2))
        return 2
    data = registry(root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda n: observe(n, data['identities'].get(n), root), ACCOUNTS))
    if args.command == 'enroll':
        identities = {r['account']: r.get('identity_fingerprint') for r in rows}
        if not all(identities.values()):
            raise SystemExit('Enrollment refused: all four native identity probes must succeed')
        for provider in ('openai', 'anthropic'):
            if identities[provider+'-apple'] == identities[provider+'-gmail']:
                raise SystemExit('Enrollment refused: duplicate provider identities')
        if data['identities'] and data['identities'] != identities:
            raise SystemExit('Enrollment refused: existing identities differ; review native logins')
        save(root / 'readiness.json', {'identities': identities})
        print('Four distinct provider bindings enrolled; credentials remain native.')
    elif args.command == 'plan':
        result = launch_plan(rows, root, args.client, args.provider, args.preferred_account, args.allow_unknown_quota)
        print(json.dumps(result, indent=2))
        return 0 if result['launch_allowed'] else 2
    elif args.command == 'choose':
        selected = choose(rows, args.runtime)
        print(json.dumps({'selected': selected['account'] if selected else None,
                          'reason': 'greatest observed core quota' if selected else 'no verified account with known available quota',
                          'scope': 'new work only; no running session migration'}, indent=2))
        return 0 if selected else 2
    else:
        for row in rows:
            row.pop('identity_fingerprint', None)
        print(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
