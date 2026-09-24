"""Daily paths and explicit journal writes, adapted from Morty's existing helper."""
from contextlib import contextmanager
from datetime import date, datetime
import fcntl
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo


# One canonical shape for an agent work entry, so what a role writes is exactly what
# another role parses. Dataview inline fields carry the structure; the em-dash
# attribution is the vault's existing convention and is preserved byte for byte.
ROLES = ('Morty', 'Iztac', 'Neo')
WORK = re.compile(
    r'^- (?P<summary>.+?)'
    r'(?: \[project:: (?P<project>[^\]]+)\])?'
    r'(?: \[time:: (?P<time>[^\]]+)\])?'
    r' \u2014 (?P<role>[A-Za-z]+)\s*$')
SPAN = re.compile(r'^(?:(\d+)h)?(?:(\d+)m)?$')
PRIORITY = {'highest': '\U0001F53A', 'high': '\u23EB', 'medium': '\U0001F53C', 'low': '\U0001F53D'}


def span(minutes):
    """Minutes as the compact form the vault reads: 90 -> 1h30m, 45 -> 45m."""
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f'{hours}h{rest}m'
    return f'{hours}h' if hours else f'{rest}m'


def minutes(text):
    found = SPAN.fullmatch((text or '').strip())
    if not found or not any(found.groups()):
        return None
    return int(found.group(1) or 0) * 60 + int(found.group(2) or 0)


def work_line(role, summary, project=None, spent=None):
    """The one place that knows how a work entry is written."""
    if role not in ROLES:
        raise ValueError('unknown role for a work entry')
    summary = ' '.join((summary or '').split())
    if not summary:
        raise ValueError('a work entry needs a summary')
    if project is not None:
        project = project.strip()
        if not project or ']' in project or '\n' in project:
            raise ValueError('project label must be a simple one-line name')
    line = '- ' + summary
    if project:
        line += f' [project:: {project}]'
    if spent is not None:
        line += f' [time:: {span(spent)}]'
    return line + ' \u2014 ' + role


def task_line(text, tag=None, due=None, scheduled=None, priority=None):
    """A task in the vault's existing Tasks-plugin format, and nothing else."""
    text = ' '.join((text or '').split())
    if not text:
        raise ValueError('a task needs a description')
    line = '- [ ] ' + text
    if tag:
        clean = tag.lstrip('#').strip()
        if not clean or any(c.isspace() for c in clean):
            raise ValueError('a tag is a single word')
        line += ' #' + clean
    if priority:
        if priority not in PRIORITY:
            raise ValueError('priority must be one of ' + ', '.join(PRIORITY))
        line += ' ' + PRIORITY[priority]
    if scheduled:
        line += ' \u23F3 ' + date.fromisoformat(scheduled).isoformat()
    if due:
        line += ' \U0001F4C5 ' + date.fromisoformat(due).isoformat()
    return line


def entries(root, date_text=None):
    """Every structured work entry in a day's note. This is how one role reads another's."""
    current = day(date_text)
    path = location(root, current, personal=True)
    safe_path(root, path)
    found = []
    if path.is_file() and not path.is_symlink():
        for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            match = WORK.match(raw.rstrip())
            if not match or match.group('role') not in ROLES:
                continue
            found.append({'date': current.isoformat(), 'line': number,
                          'role': match.group('role'), 'project': match.group('project'),
                          'minutes': minutes(match.group('time')) if match.group('time') else None,
                          'summary': match.group('summary').strip()})
    return {'path': str(path), 'date': current.isoformat(), 'entries': found,
            'unattributed': [e for e in found if not e['project']],
            'note': 'An entry without a project cannot be reconciled to billable work.'}


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


def written_date(current):
    """The vault writes its daily titles out in words: September 24th 2026."""
    tens = current.day % 100
    suffix = 'th' if 11 <= tens <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(current.day % 10, 'th')
    return f'{current:%B} {current.day}{suffix} {current.year}'


def insert_under_notes(text, line):
    """Append one line to the Notes section, creating it only if the note lacks one."""
    notes = re.search(r'^# Notes[ \t]*\r?$', text, re.M)
    if not notes:
        return text.rstrip('\n') + '\n\n# Notes\n' + line + '\n'
    next_heading = re.search(r'^# ', text[notes.end():], re.M)
    end = notes.end() + next_heading.start() if next_heading else len(text)
    return text[:end].rstrip('\n') + '\n' + line + '\n\n' + text[end:]


def update(root, command, date_text=None, title=None, body=None, line=None):
    current = day(date_text)
    personal = command.startswith('journal-') or command in ('work', 'task')
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
        text = old if old is not None else (f'---\ntitle: {written_date(current)}\n---\n\n# Notes\n' if personal else f'# {current.isoformat()}\n')
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
        elif command in ('work', 'task'):
            if line not in text.splitlines():
                text = insert_under_notes(text, line)
        elif command == 'journal-line':
            line = (line or '').strip()
            if not line or '\n' in line or '\r' in line:
                raise ValueError('journal entry must be a nonempty single line')
            link = f'[[0. morty/{current:%Y/%m/%Y-%m-%d}|Morty log]]'
            if '0. morty/' not in line:
                line += ' ('+link+')'
            if line not in text.splitlines():
                text = insert_under_notes(text, line)
        replace(path,old,text)
        return {'path':str(path),'changed':text!=old}
