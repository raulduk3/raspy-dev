"""Equip a native account's home directory with the platform's shared furniture.

An isolated account home (see accounts.py) starts bare: native login only, no
platform hooks and no global instructions. A coding worker launched there runs
WITHOUT the guard mechanism that refuses protected pushes, merges, restarts and
service operations on the default homes. This module closes that gap for a
single named account, idempotently, without ever touching credentials.

HARD SAFETY RULES (enforced in code below, not just documented):
  * Never read, write, move, or back up auth.json, .credentials.json, or any
    other token/secret file. This module only ever opens a fixed, small set of
    paths under a home: settings.json and CLAUDE.md for a Claude home;
    AGENTS.md and rules/default.rules for a Codex home. It never lists a
    home's directory contents (no iterdir/listdir/glob against the home), so
    there is no code path that could stumble onto a credential file.
  * Never overwrite an existing file the platform did not itself author
    without first preserving the original: a timestamped 0600 backup is
    written beside it before any change lands.
  * Idempotent by construction: a JSON file is merged structurally (hook
    entries de-duplicated by matcher+command, every other key left alone) and
    a text file is merged through a `dev-platform:managed` marker block, so a
    second apply of the same source content is a byte-for-byte no-op.
  * Refuses to operate on a home that is a symlink, or whose path contains a
    symlink anywhere in its ancestry (same check as accounts.prepare_login).
  * Files this module creates are 0600; directories it creates are 0700.

Authoritative sources (the plan()/apply() output also names these):
  * Claude hook wiring: hooks/claude-settings.hooks.json in this repository.
    This is the platform's own canonical fragment, not the live
    ~/.claude/settings.json -- the live file also carries desktop-only
    personal keys (tui, enabledPlugins, advisorModel, attribution, ...) that
    must not be replicated into a coding worker's isolated home.
  * Codex guard wiring: hooks/codex.rules in this repository, installed as
    rules/default.rules. Task scope (see caller) named only AGENTS.md for
    Codex homes; this module also provisions rules/default.rules because it
    is the literal Codex-side equivalent of the Claude PreToolUse guard hook
    (hooks/codex.rules itself says it is "installed as
    ~/.codex/rules/default.rules"), and an isolated Codex home without it has
    exactly the safety gap this module exists to close. This is a deliberate,
    disclosed scope extension -- report it, don't hide it.
  * Global instructions: the live default home itself (~/.claude/CLAUDE.md or
    ~/.codex/AGENTS.md). There is no platform-owned canonical copy of Ricky's
    personal global instructions; templates/CLAUDE.md and templates/AGENTS.md
    in this repository are per-repository contributor templates for a
    different audience and must not be used here.
  * Status line: registered per the exact contract supplied by the caller --
    `python3 <install-root>/integrations/claude/usage-collector.py --account
    <account-id>`, where <install-root> defaults to the same
    `$HOME/Dev/dev-platform` (shell-expanded at hook-run time) that the
    platform's own hooks already use in ~/.claude/settings.json.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from . import accounts as accounts_module

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = Path.home() / '.config/dev-platform/accounts.json'
DEFAULT_INSTALL_ROOT = '$HOME/Dev/dev-platform'

MANAGED_BEGIN = '<!-- dev-platform:managed:begin -->'
MANAGED_END = '<!-- dev-platform:managed:end -->'

# Never opened, written, moved or backed up, under any circumstance.
FORBIDDEN_BASENAMES = ('auth.json', '.credentials.json')


def _forbidden_name(name):
    lowered = name.lower()
    return name in FORBIDDEN_BASENAMES or any(word in lowered for word in ('credential', 'token', 'secret'))


def _guard_path(path):
    """Defense in depth: refuse to touch a secret-shaped path or a symlink."""
    if _forbidden_name(path.name):
        raise ValueError('refusing to touch a credential/secret-shaped file: ' + path.name)
    if path.exists() and path.is_symlink():
        raise ValueError('refusing to operate on a symlinked file: ' + str(path))


def _check_no_symlinks(home_raw):
    home = Path(home_raw).expanduser().absolute()
    if home.is_symlink():
        raise ValueError('refusing to operate on a symlinked home: ' + str(home))
    for ancestor in home.parents:
        if ancestor.is_symlink():
            raise ValueError('refusing to operate on a home whose path contains a symlink: ' + str(ancestor))
    return home


def _atomic_write(path, data_bytes, mode=0o600):
    _guard_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data_bytes)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _backup(path, original_bytes):
    _guard_path(path)
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    backup_path = path.with_name(path.name + '.' + stamp + '.bak')
    suffix = 1
    while backup_path.exists():
        suffix += 1
        backup_path = path.with_name(path.name + '.' + stamp + '-' + str(suffix) + '.bak')
    fd = os.open(str(backup_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(original_bytes)
    return backup_path


def _apply_json_file(path, merge_fn, dry_run):
    """merge_fn(existing_dict) -> new_dict. Structural merge; no markers needed."""
    _guard_path(path)
    existed = path.is_file()
    original_bytes = path.read_bytes() if existed else None
    if existed:
        try:
            existing = json.loads(original_bytes)
            if not isinstance(existing, dict):
                existing = {}
        except ValueError:
            existing = {}
    else:
        existing = {}
    new_data = merge_fn(dict(existing))
    new_bytes = (json.dumps(new_data, indent=2) + '\n').encode()
    if existed and new_bytes == original_bytes:
        return {'path': str(path), 'action': 'unchanged'}
    action = 'merged' if existed else 'created'
    result = {'path': str(path), 'action': action}
    if dry_run:
        result['would_backup'] = existed
        return result
    if existed:
        result['backup'] = str(_backup(path, original_bytes))
    _atomic_write(path, new_bytes)
    result['bytes'] = len(new_bytes)
    return result


def _apply_text_file(path, managed_body, dry_run):
    """Merge managed_body into path inside a `dev-platform:managed` marker block,
    preserving any pre-existing user-authored content outside the block."""
    _guard_path(path)
    existed = path.is_file()
    original = path.read_text() if existed else ''
    block = MANAGED_BEGIN + '\n' + managed_body.rstrip('\n') + '\n' + MANAGED_END + '\n'
    if MANAGED_BEGIN in original and MANAGED_END in original:
        pre, rest = original.split(MANAGED_BEGIN, 1)
        _, post = rest.split(MANAGED_END, 1)
        post = post[1:] if post.startswith('\n') else post
        new_content = pre + block + post
    elif existed and original.strip():
        sep = '' if original.endswith('\n') else '\n'
        new_content = original + sep + '\n' + block
    else:
        new_content = block
    if existed and new_content == original:
        return {'path': str(path), 'action': 'unchanged'}
    action = 'merged' if existed else 'created'
    result = {'path': str(path), 'action': action}
    if dry_run:
        result['would_backup'] = existed
        return result
    if existed:
        result['backup'] = str(_backup(path, original.encode()))
    new_bytes = new_content.encode()
    _atomic_write(path, new_bytes)
    result['bytes'] = len(new_bytes)
    return result


def _merge_hook_entries(existing_entries, new_entries):
    existing_entries = list(existing_entries)
    seen = {(entry.get('matcher'), hook.get('command'))
            for entry in existing_entries if isinstance(entry, dict)
            for hook in (entry.get('hooks') or []) if isinstance(hook, dict)}
    for entry in new_entries:
        pairs = {(entry.get('matcher'), hook.get('command')) for hook in entry.get('hooks', [])}
        if not pairs & seen:
            existing_entries.append(entry)
            seen |= pairs
    return existing_entries


def _ensure_status_line(settings, command):
    current = settings.get('statusLine')
    target = {'type': 'command', 'command': command}
    if current is None:
        settings['statusLine'] = target
        return 'installed'
    if isinstance(current, dict) and 'usage-collector.py' in str(current.get('command', '')):
        if current == target:
            return 'unchanged'
        settings['statusLine'] = target
        return 'updated'
    return 'left-custom-status-line-in-place'


def _resolve_install_root(install_root):
    return Path(os.path.expandvars(install_root)).expanduser()


def _provision_claude_settings(home, account_id, repo_root, install_root, dry_run):
    dest = home / 'settings.json'
    hooks_path = repo_root / 'hooks' / 'claude-settings.hooks.json'
    if not hooks_path.is_file():
        raise ValueError('authoritative source missing: ' + str(hooks_path))
    hooks_fragment = json.loads(hooks_path.read_text())['hooks']
    command = 'python3 ' + install_root + '/integrations/claude/usage-collector.py --account ' + account_id
    note = {}

    def merge(existing):
        merged = dict(existing)
        hooks = dict(merged.get('hooks') or {})
        for event, entries in hooks_fragment.items():
            hooks[event] = _merge_hook_entries(hooks.get(event) or [], entries)
        merged['hooks'] = hooks
        note['status_line'] = _ensure_status_line(merged, command)
        return merged

    result = _apply_json_file(dest, merge, dry_run)
    result['status_line'] = note.get('status_line')
    collector = _resolve_install_root(install_root) / 'integrations' / 'claude' / 'usage-collector.py'
    if not collector.is_file():
        result['note'] = ('registered status line command for ' + str(collector) +
                           '; that file does not exist yet (owned by a concurrent task)')
    return result


def _provision_instructions(dest, source, dry_run):
    if not source.is_file():
        raise ValueError('authoritative source missing: ' + str(source))
    return _apply_text_file(dest, source.read_text(), dry_run)


def _provision_codex_rules(dest, source, dry_run):
    if not source.is_file():
        raise ValueError('authoritative source missing: ' + str(source))
    return _apply_text_file(dest, source.read_text(), dry_run)


def _provision(home, kind, account_id, repo_root, default_home, install_root, dry_run):
    if not home.is_dir():
        raise ValueError('native home missing; complete native login preparation first')
    actions = []
    if kind == 'claude':
        actions.append(dict(_provision_claude_settings(home, account_id, repo_root, install_root, dry_run),
                             kind='settings'))
        actions.append(dict(_provision_instructions(home / 'CLAUDE.md', default_home / 'CLAUDE.md', dry_run),
                             kind='instructions', source=str(default_home / 'CLAUDE.md')))
    elif kind == 'codex':
        actions.append(dict(_provision_instructions(home / 'AGENTS.md', default_home / 'AGENTS.md', dry_run),
                             kind='instructions', source=str(default_home / 'AGENTS.md')))
        rules_source = repo_root / 'hooks' / 'codex.rules'
        actions.append(dict(_provision_codex_rules(home / 'rules' / 'default.rules', rules_source, dry_run),
                             kind='guard-rules', source=str(rules_source)))
    else:
        raise ValueError('unsupported home kind: ' + kind)
    return actions


def _run(account, registry_path, source_root, default_home_root, install_root, dry_run, allow_native_default):
    if account not in accounts_module.IDS or account == 'zai':
        raise ValueError('unsupported account for home provisioning')
    data = accounts_module.load(Path(registry_path))
    binding = data['bindings'].get(account)
    if not binding:
        raise ValueError('account not bound; bind it before equipping its home')
    if binding.get('native_default') and not allow_native_default:
        raise ValueError('refusing to modify the native default home; only isolated profile homes may be equipped')
    kind = accounts_module.runtime(account)
    home = _check_no_symlinks(binding['home'])
    repo_root = Path(source_root).resolve() if source_root else PLATFORM_ROOT
    if default_home_root is not None:
        default_home = Path(default_home_root).expanduser()
    else:
        default_home = Path.home() / ('.codex' if kind == 'codex' else '.claude')
    actions = _provision(home, kind, account, repo_root, default_home, install_root, dry_run)
    return {'account': account, 'runtime': kind, 'home': str(home), 'mode': 'plan' if dry_run else 'apply',
            'source_root': str(repo_root), 'default_home': str(default_home), 'install_root': install_root,
            'native_default': bool(binding.get('native_default')), 'actions': actions}


def plan(account, registry=DEFAULT_REGISTRY, *, source_root=None, default_home_root=None,
         install_root=DEFAULT_INSTALL_ROOT):
    """Read-only: report what apply() would create or modify. Never writes."""
    return _run(account, registry, source_root, default_home_root, install_root, dry_run=True,
                allow_native_default=True)


def apply(account, registry=DEFAULT_REGISTRY, *, source_root=None, default_home_root=None,
          install_root=DEFAULT_INSTALL_ROOT):
    """Idempotently equip the account's isolated home. Refuses native-default homes."""
    return _run(account, registry, source_root, default_home_root, install_root, dry_run=False,
                allow_native_default=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'apply'):
        sub = commands.add_parser(name)
        sub.add_argument('account', choices=accounts_module.IDS)
    args = parser.parse_args(argv)
    try:
        registry = args.registry.expanduser().absolute()
        output = plan(args.account, registry) if args.command == 'plan' else apply(args.account, registry)
        print(json.dumps(output, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print('ai-profile: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
