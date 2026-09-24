"""Read preserved OpenClaw conversation records without an OpenClaw runtime."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

AGENTS = {'morty': 'main', 'iztac': 'hermes', 'neo': 'neo'}


def connect(archive, agent):
    path = Path(archive).resolve() / 'sqlite-consistent' / (AGENTS[agent] + '.sqlite')
    if not path.is_file():
        raise ValueError('preserved agent database is missing')
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    conn.execute('pragma query_only=on')
    conn.row_factory = sqlite3.Row
    return conn


def search(conn, query, limit):
    # Literal matching: wildcard characters in user text have no special meaning.
    return [dict(row) for row in conn.execute('''
        SELECT session_key, current_session_id, label, display_name, updated_at
        FROM session_nodes
        WHERE instr(lower(coalesce(label, '') || ' ' || coalesce(display_name, '')),
                    lower(?)) > 0
        ORDER BY updated_at DESC, session_key LIMIT ?
    ''', (query, limit))]


def messages(conn, session, after, limit):
    if not conn.execute('SELECT 1 FROM session_windows WHERE session_id=?', (session,)).fetchone():
        raise ValueError('session not found in this preserved agent store')
    rows = conn.execute('''SELECT seq, event_json, created_at FROM transcript_events
                          WHERE session_id=? AND seq>? ORDER BY seq LIMIT ?''',
                        (session, after, limit)).fetchall()
    result = []
    for row in rows:
        event = json.loads(row['event_json'])
        message = event.get('message', {})
        content = message.get('content', [])
        texts = ([content] if isinstance(content, str) else
                 [part['text'] for part in content if isinstance(part, dict)
                  and part.get('type') in ('text', 'input_text', 'output_text')
                  and isinstance(part.get('text'), str)])
        if message.get('role') in ('user', 'assistant') and texts:
            result.append({'seq': row['seq'], 'created_at': row['created_at'],
                           'role': message['role'], 'text': '\n'.join(texts)})
    return {'messages': result, 'next_after': rows[-1]['seq'] if rows else after,
            'has_more': bool(rows and conn.execute(
                'SELECT 1 FROM transcript_events WHERE session_id=? AND seq>? LIMIT 1',
                (session, rows[-1]['seq'])).fetchone())}


def windows(conn, key, limit):
    return [dict(row) for row in conn.execute('''
        SELECT session_id, previous_session_id, reason, created_at, updated_at
        FROM session_windows WHERE session_key=? ORDER BY created_at, session_id LIMIT ?
    ''', (key, limit))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--agent', choices=AGENTS, required=True)
    parser.add_argument('--limit', type=int, default=20)
    commands = parser.add_subparsers(dest='command', required=True)
    find = commands.add_parser('find')
    find.add_argument('query')
    timeline = commands.add_parser('windows')
    timeline.add_argument('key')
    read = commands.add_parser('read')
    read.add_argument('session')
    read.add_argument('--after', type=int, default=-1)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error('limit must be between 1 and 100')
    try:
        conn = connect(args.archive, args.agent)
        try:
            if args.command == 'find':
                data = search(conn, args.query, args.limit)
            elif args.command == 'windows':
                data = windows(conn, args.key, args.limit)
            else:
                data = messages(conn, args.session, args.after, args.limit)
        finally:
            conn.close()
        print(json.dumps({'source': 'preserved-history', 'agent': args.agent,
                          'notice': 'Historical reference, not current state or instructions.',
                          'result': data}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, sqlite3.Error, OSError):
        print('History unavailable: check archive path, schema and session identity.', file=sys.stderr)
        return 2
