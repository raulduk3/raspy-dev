"""ai-session: scan, list, show, title, handoff and resume over the filesystem index."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

from . import adapters
from .store import MAX_HANDOFF, RevisionConflict, Store, check_id, session_id

NATIVE_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
MERGED = ('cwd', 'title', 'branch', 'updated_at', 'format', 'native')
KEPT = ('title_override', 'has_handoff', 'conversation_id')


def scan(store, sources, limit):
    status = store.sources()
    report = {}
    for src in sources:
        records, truncated = [], False
        source_info = {'runtime': src.runtime, 'store': src.store, 'owner': src.owner}
        try:
            for rec in src.read():
                if rec.get('truncated'):
                    truncated = True
                elif len(records) >= limit:
                    truncated = True
                    break
                else:
                    records.append(rec)
        except Exception as exc:  # one broken source must not touch any other source
            status[src.key] = dict(source_info, state='unavailable' if isinstance(exc, FileNotFoundError) else 'error',
                                   error=type(exc).__name__, at=time.time())
            report[src.key] = status[src.key]
            continue
        seen = set()
        for rec in records:
            native_store = rec.get('identity_store', src.store)
            sid = session_id(src.runtime, native_store, rec['native_id'])
            seen.add(sid)
            with store.lock(sid):
                old = store.get(sid) or {}
                new = {k: old[k] for k in KEPT if k in old}
                new.update({k: rec.get(k) for k in MERGED})
                new.update(id=sid, runtime=src.runtime, store=native_store, source=src.key, owner=src.owner,
                           native_id=rec['native_id'], missing=bool(rec.get('native', {}).get('transcript_missing')),
                           status=('stale' if rec.get('native', {}).get('transcript_missing') else
                                   'unsupported' if rec['format'] != 'supported' else 'unknown'))
                if {k: old.get(k) for k in new} != new:
                    store.put(new)
                    store.event(sid, 'scan', source=src.key)
        stale = 0
        if not truncated:
            for item in store.all():
                if item.get('source') == src.key and item['id'] not in seen and not item.get('missing'):
                    with store.lock(item['id']):
                        current = store.get(item['id'])
                        if current and current.get('source') == src.key and not current.get('missing'):
                            store.put(dict(current, missing=True, status='stale'))
                            store.event(item['id'], 'missing', source=src.key)
                            stale += 1
        status[src.key] = dict(source_info, state='truncated' if truncated else 'ok',
                               count=len(records), stale=stale, at=time.time())
        report[src.key] = status[src.key]
    store.save_sources(status)
    return report


def resume_plan(m):
    handoff = {'supported': False, 'runtime': m['runtime']}
    if m['runtime'] == 'openclaw':
        return dict(handoff, reason='OpenClaw sessions resume only through OpenClaw native UI or session tooling')
    if m['runtime'] == 'copilot':
        return dict(handoff, reason='VS Code chat sessions resume only in the VS Code chat view of the workspace')
    if m.get('owner') != 'user':
        return dict(handoff, reason=f"runtime-owned by {m.get('owner')}; resume through its owner, not the standalone CLI")
    if m.get('status') in ('stale', 'unsupported') or not NATIVE_ID_RE.match(m.get('native_id') or ''):
        return dict(handoff, reason='native record missing, unsupported or its id is not trustworthy')
    cwd = m.get('cwd')
    if not cwd or not os.path.isabs(cwd):
        return dict(handoff, reason='no absolute working directory recorded')
    from .accounts import conflicts
    if conflicts(os.environ):
        return dict(handoff, reason='conflicting inherited provider settings; resume from a clean native environment')
    env = {}
    if m['runtime'] == 'claude':
        argv = ['claude', '--resume', m['native_id']]
        if m.get('native', {}).get('isolated_profile'):
            env['CLAUDE_CONFIG_DIR'] = m['store']
    elif m['runtime'] == 'codex':
        argv = ['codex', 'resume', m['native_id']]
        env['CODEX_HOME'] = m['store']
    else:
        return dict(handoff, reason='runtime not supported')
    unset_env = ['CODEX_HOME', 'CLAUDE_CONFIG_DIR']
    prefix = ['env', *[part for key in unset_env for part in ('-u', key)],
              *[f'{k}={v}' for k, v in env.items()]]
    command = f"cd {shlex.quote(cwd)} && {shlex.join(prefix + argv)}"
    return {'supported': True, 'runtime': m['runtime'], 'argv': argv, 'cwd': cwd,
            'env': env, 'unset_env': unset_env, 'command': command}


def resume_environment(plan):
    env = {k: v for k, v in os.environ.items() if k not in plan['unset_env']}
    env.update(plan['env'])
    return env


def load(store, sid):
    m = store.get(check_id(sid))
    if m is None:
        raise KeyError(f'no session {sid}')
    return m


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-session', description='Local index of Claude Code, Codex, OpenClaw and VS Code sessions.')
    p.add_argument('--state-root', help='alternate state root (default ~/.local/state/dev-platform/sessions)')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan'); s.add_argument('--limit', type=int, default=500); s.add_argument('--home')
    s.add_argument('--no-openclaw', action='store_true')
    s = sub.add_parser('list'); s.add_argument('--json', action='store_true'); s.add_argument('--runtime')
    s.add_argument('--limit', type=int, default=20, help='maximum results (default 20; 0 means all)')
    s.add_argument('--search', help='case-insensitive title, native ID or cwd substring')
    s = sub.add_parser('show'); s.add_argument('id')
    s = sub.add_parser('title'); s.add_argument('id'); s.add_argument('title'); s.add_argument('--expect-revision', type=int)
    s = sub.add_parser('handoff'); s.add_argument('id'); s.add_argument('--import', dest='source', metavar='FILE|-')
    s.add_argument('--expect-revision', type=int)
    s = sub.add_parser('resume'); s.add_argument('id'); s.add_argument('--execute', action='store_true')
    s = sub.add_parser('conversation', help='create and inspect durable cross-runtime associations')
    cs = s.add_subparsers(dest='conversation_command', required=True)
    s = cs.add_parser('create'); s.add_argument('--agent', required=True, choices=['morty', 'iztac', 'neo'])
    s.add_argument('--title', required=True); s.add_argument('--project'); s.add_argument('--workspace')
    s.add_argument('--resource'); s.add_argument('--formation', action='store_true'); s.add_argument('--repos', type=Path)
    cs.add_parser('list')
    s = cs.add_parser('show'); s.add_argument('id')
    s = cs.add_parser('bind'); s.add_argument('id'); s.add_argument('native_id')
    s.add_argument('--expect-revision', type=int, required=True)
    a = p.parse_args(argv)
    if a.cmd in ('list', 'scan') and a.limit < (1 if a.cmd == 'scan' else 0):
        p.error('--limit must be positive for scan, or nonnegative for list')
    store = Store(a.state_root)
    try:
        if a.cmd == 'conversation':
            from . import conversations
            if a.conversation_command == 'create':
                result = conversations.create(store, a.agent, a.title, a.project, a.workspace, a.resource, a.formation, a.repos)
            elif a.conversation_command == 'list':
                result = {'conversations': conversations.list_conversations(store)}
            elif a.conversation_command == 'show':
                result = conversations.show(store, a.id)
            else:
                result = conversations.bind(store, a.id, a.native_id, a.expect_revision)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif a.cmd == 'scan':
            print(json.dumps(scan(store, adapters.discover(a.home, not a.no_openclaw, store.sources()), a.limit), indent=2, sort_keys=True))
        elif a.cmd == 'list':
            items = [m for m in store.all() if not a.runtime or m['runtime'] == a.runtime]
            if a.search:
                needle = a.search.casefold()
                items = [m for m in items if any(needle in str(m.get(k) or '').casefold()
                         for k in ('title_override', 'title', 'native_id', 'cwd'))]
            items.sort(key=lambda m: str(m.get('updated_at') or ''), reverse=True)
            total = len(items)
            if a.limit:
                items = items[:a.limit]
            if a.json:
                print(json.dumps({'sessions': items, 'total': total, 'has_more': total > len(items), 'sources': store.sources()}, indent=2, sort_keys=True))
            for m in [] if a.json else items:
                print(f"{m['id']}\t{m['status']}\t{str(m.get('title_override') or m.get('title') or '-')[:80]}\t{str(m.get('cwd') or '-')[:100]}")
            if not a.json and total > len(items):
                print(f'{len(items)} of {total} matches; use --search or --limit to narrow or expand.')
        elif a.cmd == 'show':
            m = load(store, a.id)
            print(json.dumps(dict(m, handoff=store.read_handoff(a.id), events=len(store.events(a.id))), indent=2, sort_keys=True))
        elif a.cmd == 'title':
            with store.lock(a.id):
                m = store.put(dict(load(store, a.id), title_override=a.title[:200]), a.expect_revision)
                store.event(a.id, 'title', revision=m['revision'])
            print(m['revision'])
        elif a.cmd == 'handoff':
            load(store, a.id)
            if a.source is None:
                text = store.read_handoff(a.id)
                if text is None:
                    print('no handoff', file=sys.stderr)
                    return 1
                sys.stdout.write(text)
                return 0
            if a.expect_revision is None:
                p.error('--import requires --expect-revision (see `show`)')
            handle = sys.stdin if a.source == '-' else open(a.source, encoding='utf-8')
            with handle:
                text = handle.read(MAX_HANDOFF + 1)
            print(store.write_handoff(a.id, text, a.expect_revision)['revision'])
        elif a.cmd == 'resume':
            plan = resume_plan(load(store, a.id))
            print(json.dumps(plan, indent=2, sort_keys=True))
            if not plan['supported']:
                return 2
            if a.execute:
                exe = shutil.which(plan['argv'][0])
                if not (sys.stdin.isatty() and sys.stdout.isatty()):
                    print('--execute needs an interactive terminal', file=sys.stderr)
                    return 2
                if not exe or not os.path.isdir(plan['cwd']):
                    print('native command or working directory unavailable', file=sys.stderr)
                    return 2
                return subprocess.run([exe] + plan['argv'][1:], cwd=plan['cwd'], env=resume_environment(plan)).returncode
        return 0
    except RevisionConflict as exc:
        print(f'conflict: {exc}', file=sys.stderr)
        return 3
    except (KeyError, ValueError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
