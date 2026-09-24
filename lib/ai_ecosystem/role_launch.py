"""Account-bound Pi role launcher: conversation -> identity -> profile -> lock -> exec.

Selection is explicit or the registry's selected account. The launcher never
imports credentials, never claims Pi identity equals the account's Codex or
Claude binding, and holds the conversation's writer lock across exec.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from . import accounts, conversations, environment_service, pi_launch
from .store import Store

PLATFORM = Path(__file__).resolve().parents[2]
KEEP_ENV = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM', 'COLORTERM', 'TERM_PROGRAM', 'SHELL', 'TMPDIR')
MODEL_ID = r'[A-Za-z0-9][A-Za-z0-9._:-]{0,63}'


def provider_for(account):
    return 'openai-codex' if account.startswith('openai-') else 'anthropic'


def identity_file(agent, agents_root):
    for candidate in (Path(agents_root) / agent / 'identity.md', PLATFORM / 'agents' / agent / 'identity.md'):
        if candidate.is_symlink():
            raise ValueError('identity file cannot be a symlink')
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError(f'no identity file for {agent}; author agents/{agent}/identity.md')


def select_account(data, requested):
    account = requested or data.get('selected')
    if not account:
        raise ValueError('choose an account with --account or ai-account select')
    if account not in environment_service.ACCOUNTS:
        raise ValueError('unknown account')
    return account


def default_model(profile_home, provider, requested):
    import re
    if requested:
        if not re.fullmatch(MODEL_ID, requested):
            raise ValueError('invalid model id')
        return requested
    settings = Path(profile_home) / 'settings.json'
    if settings.is_file() and not settings.is_symlink():
        try:
            saved = json.loads(settings.read_text())
        except ValueError:
            saved = {}
        if isinstance(saved, dict) and saved.get('defaultProvider') == provider and \
                isinstance(saved.get('defaultModel'), str) and re.fullmatch(MODEL_ID, saved['defaultModel']):
            return saved['defaultModel']
    raise ValueError('choose --model; the Pi profile has no default model for this provider')


def resume_file(home, requested):
    if not requested:
        return None
    directory = (home / 'native/pi').resolve()
    if requested == 'latest':
        files = sorted((p for p in directory.glob('*.jsonl') if not p.is_symlink() and p.is_file()),
                       key=lambda p: p.stat().st_mtime)
        if not files:
            raise ValueError('no native Pi session in this conversation yet')
        return files[-1].resolve()
    path = Path(requested).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.parent.resolve() != directory:
        raise ValueError('resume file must be an existing native session inside this conversation')
    return path.resolve()


def plan(conversation_id, *, state_root=None, registry=None, account=None, model=None, resume=None,
         profiles_root=None, agents_root=None, history_archive=None, offline=False, environ=None):
    environ = os.environ if environ is None else environ
    bad = accounts.conflicts(environ)
    if bad:
        raise ValueError('conflicting inherited provider settings: ' + ', '.join(bad) + '; launch from a clean shell')
    store = Store(state_root)
    conversation = conversations.read(store, conversation_id)
    home = conversations.path_for(store, conversation_id)
    if not (home / 'native/pi').is_dir():
        raise ValueError('conversation has no native Pi directory')
    data = accounts.load(Path(registry) if registry else Path.home() / '.config/dev-platform/accounts.json')
    name = select_account(data, account)
    provider = provider_for(name)
    profile = environment_service.profile_plan(
        'pi', name, Path(profiles_root or Path.home() / '.local/share/dev-platform/accounts'))
    observation = environment_service.check_pi_profile(profile)
    if observation['state'] != 'configured':
        raise ValueError(f"Pi profile for {name} is {observation['state']}: {profile['instructions']}")
    if observation.get('provider') != provider:
        raise ValueError('Pi profile provider does not match the account')
    model_id = default_model(profile['profile_home'], provider, model)
    identity = identity_file(conversation['agent'], agents_root or Path.home() / '.local/share/dev-platform/agents')
    archive = None
    if history_archive:
        archive = Path(history_archive).expanduser()
        if not archive.is_absolute() or not archive.is_dir():
            raise ValueError('history archive must be an existing absolute directory')
        archive = archive.resolve()
    node = shutil.which('node')
    if not node:
        raise ValueError('node is required for the Pi runtime')
    entry = PLATFORM / 'integrations/pi/role-launch.mjs'
    if not entry.is_file():
        raise ValueError('role launch entry missing from the platform checkout')
    binding = conversation.get('binding') or {}
    cwd = binding.get('workspace') or str(home / 'workspace')
    launch = {'version': 1,
              'conversation': {key: conversation[key] for key in ('id', 'agent', 'scope')} | {'binding': binding},
              'conversationHome': str(home), 'platformRoot': str(PLATFORM),
              'agentDir': profile['profile_home'], 'identityFile': str(identity),
              'historyArchive': str(archive) if archive else None,
              'accountRef': name + ':pi', 'provider': provider, 'modelId': model_id,
              'resumeFile': str(resume_file(home, resume)) if resume else None, 'offline': bool(offline)}
    env = {key: environ[key] for key in KEEP_ENV if key in environ}
    env.update(profile['environment'])
    if offline:
        env['PI_OFFLINE'] = '1'
    env['DEV_PLATFORM_ROLE_LAUNCH'] = json.dumps(launch)
    attribution = {'account': name, 'pi_profile': observation['state'], 'auth_type': observation.get('auth_type'),
                   'identity': 'unverified',
                   'reason': "Pi sign-in is separate from this account's Codex/Claude binding; equivalence is not established"}
    header = (f"{conversation['agent']} | {conversation['scope']['kind']} | cwd {cwd} | pi {provider}/{model_id} | "
              f"account {name} (identity unverified) | rig unbound")
    result = {'version': 1, 'conversation_id': conversation_id, 'agent': conversation['agent'],
              'scope': conversation['scope'], 'cwd': cwd, 'account': attribution,
              'model': provider + '/' + model_id, 'resume_file': launch['resumeFile'],
              'argv': [str(Path(node).resolve()), str(entry)], 'environment_keys': sorted(env),
              'launch': launch, 'header': header,
              'scope_note': 'New or explicitly resumed execution; the launcher records no account equivalence and replays nothing'}
    return result, env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path)
    parser.add_argument('--registry', type=Path)
    parser.add_argument('--profiles-root', type=Path)
    parser.add_argument('--agents-root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'launch'):
        command = sub.add_parser(name)
        command.add_argument('conversation')
        command.add_argument('--account', choices=environment_service.ACCOUNTS)
        command.add_argument('--model')
        command.add_argument('--resume', help="'latest' or an absolute native session path inside the conversation")
        command.add_argument('--history-archive', type=Path)
        command.add_argument('--offline', action='store_true', help='no model network; wiring checks only')
    args = parser.parse_args(argv)
    try:
        result, env = plan(args.conversation, state_root=args.state_root, registry=args.registry,
                           account=args.account, model=args.model, resume=args.resume,
                           profiles_root=args.profiles_root, agents_root=args.agents_root,
                           history_archive=args.history_archive, offline=args.offline)
        if args.command == 'plan':
            print(json.dumps(result, indent=2))
            return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError('launch needs an interactive terminal; use plan to inspect')
        print(result['header'], file=sys.stderr, flush=True)
        pi_launch.exec_conversation(result['launch']['conversationHome'], result['argv'], env)
    except (OSError, ValueError) as error:
        print('ai-role: ' + str(error), file=sys.stderr)
        return 2
    return 0
