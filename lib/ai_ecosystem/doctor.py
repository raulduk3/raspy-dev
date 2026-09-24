"""ai-env doctor: read-only environment diagnostics. Never installs, restarts or edits config.

Each check reports one state: ok, missing, unavailable, unverified, unsupported or broken.
Output carries names and states only, never credentials or full configuration.
"""
import argparse
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys

COMMANDS = ('claude', 'codex', 'openclaw', 'code', 'gh', 'git', 'jq', 'python3', 'laya-decide')
SKILL_DIRS = ('.claude/skills', '.codex/skills', '.agents/skills')
LAYA_LABEL = 'dev.raspy.laya'
LAYA_PROBE = {
    'state': 'Read-only diagnostic: choose which small local documentation task to inspect first.',
    'options': {'read_summary': 'Read a short summary.', 'read_details': 'Read the detailed notes.'},
}


def check_commands():
    return {c: {'state': 'ok' if shutil.which(c) else 'missing'} for c in COMMANDS}


def check_skills(home, platform):
    platform_skills = (platform / 'skills').resolve()
    expected = {p.parent.name for p in platform_skills.glob('*/SKILL.md') if p.is_file()}
    # The repository declares required names; shared discovery declares the active
    # source. Workshop-published overrides need not live in the repository.
    canonical = home / '.agents/skills'
    canonical_missing = sorted(name for name in expected
                               if not (canonical / name / 'SKILL.md').is_file())
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
        if folder != canonical:
            for name in sorted(expected):
                source = canonical / name / 'SKILL.md'
                client = folder / name / 'SKILL.md'
                if source.is_file() and client.is_file() and source.resolve() != client.resolve():
                    divergent.append(name)
        missing = sorted(name for name in expected if not (folder / name / 'SKILL.md').is_file())
        out[rel] = {'state': 'broken' if broken or divergent else
                           'missing' if missing or canonical_missing else 'ok',
                    'broken': broken, 'divergent': divergent, 'missing': missing,
                    'canonical_missing': canonical_missing}
    return out


def check_platform(platform):
    check = platform / 'bin/check'
    return {'state': 'ok' if check.is_file() and os.access(check, os.X_OK) else 'missing'}


def check_laya_config(home):
    folder = home / 'Library/LaunchAgents'
    paths = sorted(folder.glob('*laya*.plist'))
    primary = folder / f'{LAYA_LABEL}.plist'
    out = {'state': 'missing' if not primary.exists() else 'broken', 'count': len(paths)}
    if not primary.exists():
        return out
    try:
        with primary.open('rb') as handle:
            config = plistlib.load(handle)
        env = config.get('EnvironmentVariables', {})
        args = config.get('ProgramArguments', [])
        # The installed laya-serve entrypoint takes these settings from its environment.
        # Never report environment values or arbitrary launch arguments.
        checks = {
            'label_matches': config.get('Label') == LAYA_LABEL,
            'entrypoint_matches': len(args) == 1 and Path(args[0]).name == 'laya-serve',
            'loopback_host': env.get('LAYA_HOST') == '127.0.0.1',
            'port_matches': str(env.get('LAYA_PORT')) == '18791',
            'preload_enabled': env.get('LAYA_PRELOAD') == '1',
            'singleton_config': len(paths) == 1,
        }
        out.update(checks, state='ok' if all(checks.values()) else 'broken')
    except (OSError, ValueError, TypeError, AttributeError, plistlib.InvalidFileException):
        out['reason'] = 'launch configuration unreadable or unsupported'
    return out


def check_laya(home, probe):
    out = {'launch_config': check_laya_config(home)}
    lsof = shutil.which('lsof')
    if not lsof:
        out['listener'] = {'state': 'unverified', 'reason': 'lsof unavailable'}
    else:
        try:
            run = subprocess.run([lsof, '-nP', '-iTCP:18791', '-sTCP:LISTEN'],
                                 capture_output=True, text=True, timeout=10)
            rows = [line.split() for line in run.stdout.splitlines()[1:] if line.strip()]
            valid = all(len(row) > 8 and row[1].isdigit() for row in rows)
            pids = {row[1] for row in rows if len(row) > 8}
            addrs = {row[8] for row in rows if len(row) > 8}
            loopback = bool(addrs) and all(a in ('127.0.0.1:18791', '[::1]:18791') for a in addrs)
            if run.returncode not in (0, 1) or not valid or (run.returncode == 1 and rows):
                out['listener'] = {'state': 'unverified', 'reason': 'listener inspection failed'}
            else:
                out['listener'] = {'state': 'unavailable' if not rows else
                                   'ok' if len(pids) == 1 and loopback else 'broken',
                                   'count': len(pids), 'loopback_only': loopback}
        except (OSError, subprocess.TimeoutExpired):
            out['listener'] = {'state': 'unverified', 'reason': 'listener inspection unavailable'}
    if not probe:
        out['probe'] = {'state': 'unverified', 'reason': 'pass --probe-laya to invoke the helper'}
        return out
    helper = shutil.which('laya-decide')
    if not helper:
        out['probe'] = {'state': 'missing'}
        return out
    try:
        run = subprocess.run([helper], input=json.dumps(LAYA_PROBE), capture_output=True,
                             text=True, timeout=20)
        result = json.loads(run.stdout)
        shadow = (isinstance(result, dict) and result.get('mode') == 'shadow' and
                  result.get('automatically_applied', False) is False)
        if shadow and result.get('status') == 'unavailable' and result.get('recommendation') is None:
            out['probe'] = {'state': 'unavailable', 'reason': 'helper reported no valid inference'}
        elif (shadow and run.returncode == 0 and result.get('status') == 'recommended' and
              result.get('automatically_applied') is False and
              result.get('recommendation') in LAYA_PROBE['options'] and
              isinstance(result.get('route'), str) and bool(result['route']) and
              isinstance(result.get('checkpoint'), str) and bool(result['checkpoint'])):
            out['probe'] = {'state': 'ok', 'mode': 'shadow', 'inference': 'verified',
                            'recommendation_quality': 'unverified'}
        else:
            out['probe'] = {'state': 'broken', 'reason': 'invalid shadow inference response'}
    except subprocess.TimeoutExpired:
        out['probe'] = {'state': 'unavailable', 'reason': 'timeout'}
    except OSError:
        out['probe'] = {'state': 'unavailable', 'reason': 'helper unavailable'}
    except (ValueError, TypeError):
        out['probe'] = {'state': 'broken', 'reason': 'invalid shadow inference response'}
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
    d.add_argument('--platform-root', help='canonical platform checkout (default ~/Dev/dev-platform)')
    a = p.parse_args(argv)
    home = Path(a.home or Path.home())
    platform = Path(a.platform_root).expanduser() if a.platform_root else home / 'Dev/dev-platform'
    report = doctor(home, platform, a.probe_laya)
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for section, items in report.items():
            for name, value in items.items():
                state = value.get('state') if isinstance(value, dict) else value
                print(f'{section}\t{name}\t{state}')
    return 0
