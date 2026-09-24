"""ai-env doctor: read-only environment diagnostics. Never installs, restarts or edits config.

Each check reports one state: ok, missing, unavailable, unverified, unsupported or broken.
Output carries names and states only, never credentials or full configuration.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

COMMANDS = ('claude', 'codex', 'openclaw', 'code', 'gh', 'git', 'jq', 'python3', 'laya')
SKILL_DIRS = ('.claude/skills', '.codex/skills', '.agents/skills')
PLATFORM = Path(__file__).resolve().parents[2]


def check_commands():
    return {c: {'state': 'ok' if shutil.which(c) else 'missing'} for c in COMMANDS}


def check_skills(home, platform):
    platform_skills = (platform / 'skills').resolve()
    out = {}
    for rel in SKILL_DIRS:
        folder = home / rel
        if not folder.is_dir():
            out[rel] = {'state': 'missing'}
            continue
        broken, divergent = [], []
        for entry in sorted(folder.iterdir()):
            if not entry.is_symlink():
                continue
            if not entry.exists():
                broken.append(entry.name)
            elif (platform_skills / entry.name).is_dir() and entry.resolve() != (platform_skills / entry.name).resolve():
                divergent.append(entry.name)
        out[rel] = {'state': 'broken' if broken or divergent else 'ok', 'broken': broken, 'divergent': divergent}
    return out


def check_platform(platform):
    check = platform / 'bin/check'
    return {'state': 'ok' if check.is_file() and os.access(check, os.X_OK) else 'missing'}


def check_laya(home, probe):
    launch = sorted(p.name for p in (home / 'Library/LaunchAgents').glob('*laya*.plist'))
    out = {'launch_configs': launch}
    lsof = shutil.which('lsof')
    if not lsof:
        out['listener'] = {'state': 'unverified', 'reason': 'lsof unavailable'}
    else:
        run = subprocess.run([lsof, '-nP', '-iTCP', '-sTCP:LISTEN'], capture_output=True, text=True, timeout=10)
        rows = [line.split() for line in run.stdout.splitlines()[1:] if 'laya' in line.lower()]
        addrs = sorted({r[8] for r in rows if len(r) > 8})
        loopback = all(a.startswith(('127.0.0.1:', '[::1]:', 'localhost:')) for a in addrs)
        if not addrs:
            state = 'unavailable'
        elif len(addrs) == 1 and loopback:
            state = 'ok'
        else:
            state = 'broken'
        out['listener'] = {'state': state, 'count': len(addrs), 'loopback_only': loopback}
    if len(launch) > 1:
        out['listener']['state'] = 'broken'
    if not probe:
        out['probe'] = {'state': 'unverified', 'reason': 'pass --probe-laya to invoke the helper'}
    elif not shutil.which('laya'):
        out['probe'] = {'state': 'missing'}
    else:
        try:
            run = subprocess.run(['laya', '--help'], capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
            out['probe'] = {'state': 'ok' if run.returncode == 0 else 'unavailable', 'exit': run.returncode}
        except subprocess.TimeoutExpired:
            out['probe'] = {'state': 'unavailable', 'reason': 'timeout'}
    return out


def doctor(home, platform, probe=False):
    return {'commands': check_commands(), 'skills': check_skills(home, platform),
            'platform_check': check_platform(platform), 'laya': check_laya(home, probe)}


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-env')
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('doctor')
    d.add_argument('--json', action='store_true')
    d.add_argument('--probe-laya', action='store_true')
    d.add_argument('--home')
    a = p.parse_args(argv)
    report = doctor(Path(a.home or Path.home()), PLATFORM, a.probe_laya)
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for section, items in report.items():
            for name, value in items.items():
                state = value.get('state') if isinstance(value, dict) else value
                print(f'{section}\t{name}\t{state}')
    return 0
