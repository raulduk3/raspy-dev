"""Daily paths and explicit journal writes, adapted from Morty's existing helper."""
from contextlib import contextmanager
from datetime import date, datetime
import fcntl
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo


def day(value=None):
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo('America/Chicago')).date()


def location(root, current, personal=False):
    folder = '1. journal' if personal else '0. morty'
    name = current.strftime('%d-%m-%Y' if personal else '%Y-%m-%d') + '.md'
    return root / folder / current.strftime('%Y/%m') / name


def safe_path(root, path):
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('daily writer refuses symlink paths')


@contextmanager
def locked(root):
    # All callers of this tool share one journal write boundary. Editors do not.
    path = root / '.journal-write.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def replace(path, old, new):
    if old == new:
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.journal-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        current = path.read_text(encoding='utf-8') if path.exists() else None
        if current != old:
            raise ValueError('note changed during edit; reread before retrying')
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def update(root, command, date_text=None, title=None, body=None, line=None):
    current = day(date_text)
    personal = command.startswith('journal-')
    path = location(root, current, personal)
    safe_path(root, path)
    if command == 'log-path':
        return {'path': str(path), 'changed': False}
    with locked(root):
        if not personal:
            legacy = [p for p in (root/'0. morty').rglob(current.isoformat()+'.md')
                      if p != path and p.is_file() and not p.is_symlink()]
            if legacy:
                raise ValueError('legacy daily log exists; reconcile it before writing')
        old = path.read_text(encoding='utf-8') if path.exists() else None
        text = old if old is not None else (f'---\ntitle: {current.isoformat()}\n---\n\n# Notes\n' if personal else f'# {current.isoformat()}\n')
        if command == 'log-append':
            title = (title or '').strip()
            if not title or '\n' in title or '\r' in title:
                raise ValueError('log title must be a nonempty single line')
            heading = '## '+title
            content = (body or '').rstrip('\n')
            section = heading+'\n'+ ('\n'+content+'\n' if content else '')
            existing = re.search(r'^'+re.escape(heading)+r'[ \t]*\r?\n(.*?)(?=^## |\Z)',text,re.M|re.S)
            if existing:
                if existing.group(1).strip() != content.strip():
                    raise ValueError('log title already exists with different content; choose a distinct title')
            else:
                text = text.rstrip('\n')+'\n\n'+section
        elif command == 'journal-line':
            line = (line or '').strip()
            if not line or '\n' in line or '\r' in line:
                raise ValueError('journal entry must be a nonempty single line')
            link = f'[[0. morty/{current:%Y/%m/%Y-%m-%d}|Morty log]]'
            if '0. morty/' not in line:
                line += ' ('+link+')'
            if line not in text.splitlines():
                notes = re.search(r'^# Notes[ \t]*\r?$',text,re.M)
                if not notes:
                    text = text.rstrip('\n')+'\n\n# Notes\n'+line+'\n'
                else:
                    next_heading = re.search(r'^# ',text[notes.end():],re.M)
                    end = notes.end()+next_heading.start() if next_heading else len(text)
                    text = text[:end].rstrip('\n')+'\n'+line+'\n\n'+text[end:]
        replace(path,old,text)
        return {'path':str(path),'changed':text!=old}
