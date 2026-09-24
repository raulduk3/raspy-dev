"""Durable conversation associations over the existing native session index."""
import json
from pathlib import Path
from . import workspace as projects
import re
import time
import uuid

CONVERSATION = re.compile(r'^conversation-[0-9a-f]{20}$')
REFERENCE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$')


def path_for(store, identifier):
    if not CONVERSATION.fullmatch(identifier):
        raise ValueError('invalid conversation identifier')
    root = store.root / 'conversations'
    if root.is_symlink():
        raise ValueError('conversation root cannot be a symlink')
    folder = root / identifier
    if folder.is_symlink():
        raise ValueError('conversation home cannot be a symlink')
    return folder


def read(store, identifier):
    folder = path_for(store, identifier)
    path = folder / 'session.json'
    if path.is_symlink():
        raise ValueError('conversation manifest cannot be a symlink')
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError('conversation not found') from None
    if not isinstance(data, dict):
        raise ValueError('invalid conversation manifest')
    if data.get('version') != 1 or data.get('id') != identifier:
        raise ValueError('unsupported conversation manifest')
    return data


def create(store, agent, title, project=None, workspace=None, resource=None, formation=False, repos=None):
    if agent not in ('morty', 'iztac', 'neo'):
        raise ValueError('unknown agent')
    if not title.strip() or len(title) > 200:
        raise ValueError('title must contain 1 to 200 characters')
    if formation and project:
        raise ValueError('choose an existing project or project formation')
    if bool(project or formation) != bool(workspace):
        raise ValueError('project scope requires a project or formation and workspace')
    if (project or formation) and resource:
        raise ValueError('choose project or system scope, not both')
    if agent == 'morty' and (project or workspace or resource or formation):
        raise ValueError('Morty conversations have personal scope')
    if agent == 'iztac' and not (project or formation):
        raise ValueError('Iztac requires a project identity and real workspace')
    if agent == 'neo' and not (project or formation or resource):
        raise ValueError('Neo requires an explicit system resource or project')
    if project or formation:
        cwd = Path(workspace).expanduser().resolve(strict=True)
        if not cwd.is_dir():
            raise ValueError('workspace must be a directory')
        if formation:
            scope = {'kind': 'formation'}
        else:
            catalog, _ = projects.catalog(Path(repos) if repos else Path.home() / '.config/dev-platform/repos.conf')
            selected = projects.find_project(catalog, project)
            if not selected['available'] or projects.identity(cwd) != selected['common_dir']:
                raise ValueError('workspace does not belong to the selected catalog project')
            scope = {'kind': 'project', 'project_id': selected['id']}
        binding = {'workspace': str(cwd)}
    elif resource:
        if not REFERENCE.fullmatch(resource):
            raise ValueError('invalid system resource reference')
        scope, binding = {'kind': 'system', 'resource': resource}, {}
    else:
        scope, binding = {'kind': 'personal'}, {}
    identifier = 'conversation-' + uuid.uuid4().hex[:20]
    folder = path_for(store, identifier)
    folder.mkdir(parents=True, mode=0o700)
    data = dict(version=1, id=identifier, agent=agent, title=title,
                scope=scope, binding=binding, created_at=time.time())
    # session.json is the creation commit marker; partial directories are not conversations.
    store._write_atomic(folder / 'handoff.md', '# Checkpoint\n\nNo work recorded yet.\n')
    (folder / 'native').mkdir(mode=0o700)
    (folder / 'native/pi').mkdir(mode=0o700)
    store._write_atomic(folder / 'session.json', json.dumps(data, indent=2) + '\n')
    return data


def bind(store, identifier, native_id, expected_revision):
    conversation = read(store, identifier)
    with store.lock(native_id):
        native = store.get(native_id)
        if native is None:
            raise ValueError('native session is not indexed')
        if conversation['scope']['kind'] in ('project', 'formation'):
            observed = native.get('cwd')
            expected = Path(conversation['binding']['workspace'])
            if not observed:
                raise ValueError('native session has no observed workspace')
            actual = Path(observed).expanduser().resolve()
            if conversation['scope']['kind'] == 'project':
                common = projects.identity(expected)
                matches = common is not None and projects.identity(actual) == common
            else:
                matches = actual == expected or expected in actual.parents
            if not matches:
                raise ValueError('native session workspace does not match conversation scope')
        previous = native.get('conversation_id')
        if previous and previous != identifier:
            raise ValueError('native session already belongs to another conversation')
        result = store.put(dict(native, conversation_id=identifier), expected_revision)
        store.event(native_id, 'conversation-bound', conversation_id=identifier,
                    revision=result['revision'])
    return result


def show(store, identifier):
    data = read(store, identifier)
    natives = [m for m in store.all() if m.get('conversation_id') == identifier]
    return dict(data, home=str(path_for(store, identifier)), native_sessions=natives)


def list_conversations(store):
    root = store.root / 'conversations'
    if root.is_symlink():
        raise ValueError('conversation root cannot be a symlink')
    return [read(store, folder.name) for folder in sorted(root.glob('conversation-*'))
            if CONVERSATION.fullmatch(folder.name) and (folder / 'session.json').exists()]
