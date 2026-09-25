"""Role launcher plans and the real offline terminal launch through the lock boundary."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import sys
import tempfile
import termios
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import conversations, role_launch
from ai_ecosystem.store import Store

SYNTHETIC = {"openai-codex": {"type": "oauth", "access": "synthetic-never-sent",
                              "refresh": "synthetic-never-sent", "expires": 1}}


class RoleLaunch(unittest.TestCase):
    def setUp(self):
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_', 'OPENAI_', 'CODEX_', 'AI_'))}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory(prefix='ai-role-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.state = self.root / 'state'
        self.project = self.root / 'project'
        self.project.mkdir()
        (self.project / 'AGENTS.md').write_text('BOUND_PROJECT_CONTEXT\n')
        self.store = Store(self.state)
        self.conversation = conversations.create(self.store, 'iztac', 'Fixture', formation=True,
                                                 workspace=str(self.project))
        self.home = conversations.path_for(self.store, self.conversation['id'])
        self.profiles = self.root / 'profiles'
        self.profile = self.profiles / 'pi' / 'openai-apple'
        self.agents = self.root / 'agents'
        (self.agents / 'iztac').mkdir(parents=True)
        (self.agents / 'iztac/identity.md').write_text('IZTAC_LAUNCH_FIXTURE\n')
        self.registry = self.root / 'registry.json'

    def configure_profile(self):
        self.profile.mkdir(parents=True, mode=0o700)
        (self.profile / 'auth.json').write_text(json.dumps(SYNTHETIC))
        (self.profile / 'settings.json').write_text(json.dumps({'defaultProvider': 'openai-codex',
                                                                 'defaultModel': 'gpt-5.5'}))

    def plan(self, **overrides):
        options = dict(state_root=self.state, registry=self.registry, account='openai-apple',
                       profiles_root=self.profiles, agents_root=self.agents)
        options.update(overrides)
        return role_launch.plan(self.conversation['id'], **options)

    def test_search_key_comes_from_the_keychain_only_at_launch(self):
        fake = self.root / 'fakebin'
        fake.mkdir(exist_ok=True)
        security = fake / 'security'
        security.write_text('#!/bin/sh\n[ "$3" = dev-platform-perplexity ] && [ "$4" = -w ] && [ -n "$KEY" ] '
                            '&& echo "$KEY" && exit 0\nexit 44\n')
        security.chmod(0o755)
        base = {'PATH': '/usr/bin'}
        with mock.patch.dict(os.environ, {'PATH': str(fake), 'KEY': 'pplx-synthetic'}):
            env, state = role_launch.with_search(base, offline=False)
            self.assertEqual((env['PERPLEXITY_API_KEY'], state), ('pplx-synthetic', 'on'))
            self.assertNotIn('PERPLEXITY_API_KEY', base)
            self.assertEqual(role_launch.with_search(base, offline=True), (base, 'offline'))
        with mock.patch.dict(os.environ, {'PATH': str(fake), 'KEY': ''}):
            env, state = role_launch.with_search(base, offline=False)
            self.assertNotIn('PERPLEXITY_API_KEY', env)
            self.assertIn('no dev-platform-perplexity Keychain item', state)

    def test_plan_requires_explicit_account_configured_profile_and_identity(self):
        with self.assertRaisesRegex(ValueError, 'choose an account'):
            self.plan(account=None)
        with self.assertRaisesRegex(ValueError, 'profile_missing'):
            self.plan()
        self.configure_profile()
        auth_before = (self.profile / 'auth.json').read_bytes()
        result, env = self.plan()
        self.assertEqual((self.profile / 'auth.json').read_bytes(), auth_before)
        self.assertTrue(Path(result['argv'][0]).is_absolute())
        self.assertEqual(result['argv'][1], str(ROOT / 'integrations/pi/role-launch.mjs'))
        self.assertEqual(result['cwd'], str(self.project))
        self.assertEqual(result['model'], 'openai-codex/gpt-5.5')
        self.assertEqual(result['account']['identity'], 'unverified')
        self.assertEqual(result['account']['auth_type'], 'oauth')
        launch = json.loads(env['DEV_PLATFORM_ROLE_LAUNCH'])
        self.assertEqual(launch['accountRef'], 'openai-apple:pi')
        self.assertEqual(launch['conversation']['id'], self.conversation['id'])
        self.assertEqual(launch['conversation']['scope'], {'kind': 'formation'})
        self.assertEqual(launch['identityFile'], str(self.agents / 'iztac/identity.md'))
        self.assertEqual(env['PI_CODING_AGENT_DIR'], str(self.profile))
        self.assertFalse(any(k.startswith(('ANTHROPIC_', 'OPENAI_', 'AI_')) for k in env))
        self.assertNotIn('access', json.dumps(result))
        # Explicit model overrides the profile default; the registry's selection replaces --account.
        self.assertEqual(self.plan(model='gpt-6-luna')[0]['model'], 'openai-codex/gpt-6-luna')
        self.registry.write_text(json.dumps({'version': 1, 'selected': 'openai-apple', 'bindings': {}}))
        self.assertEqual(self.plan(account=None)[0]['account']['account'], 'openai-apple')
        with self.assertRaisesRegex(ValueError, 'anthropic-apple is profile_missing'):
            self.plan(account='anthropic-apple')
        # Without an installed identity the platform's own agents/<agent>/identity.md is used.
        shutil.rmtree(self.agents / 'iztac')
        fallback = self.plan(agents_root=self.root / 'no-agents')[0]['launch']['identityFile']
        self.assertEqual(fallback, str(ROOT / 'agents/iztac/identity.md'))
        # Every role now ships a contract, so a personal conversation plans too.
        morty = conversations.create(self.store, 'morty', 'Personal fixture')
        personal, _ = role_launch.plan(morty['id'], state_root=self.state, registry=self.registry,
                                       account='openai-apple', profiles_root=self.profiles,
                                       agents_root=self.agents)
        self.assertEqual(personal['launch']['identityFile'], str(ROOT / 'agents/morty/identity.md'))
        self.assertEqual(personal['scope'], {'kind': 'personal'})
        # A role with no contract anywhere still refuses rather than launching blind.
        with mock.patch.object(role_launch, 'PLATFORM', self.root / 'no-platform'):
            with self.assertRaisesRegex(ValueError, 'no identity file for morty'):
                role_launch.plan(morty['id'], state_root=self.state, registry=self.registry,
                                 account='openai-apple', profiles_root=self.profiles,
                                 agents_root=self.root / 'no-agents')

    def test_journal_is_configured_for_every_role(self):
        self.configure_profile()
        conf = self.root / 'journal.conf'
        vault = self.root / 'vault'
        vault.mkdir()
        conf.write_text(f'# the journal folder\n{vault}\n')
        self.assertEqual(role_launch.journal_root(conf), str(vault))
        # A missing file, a commented-only file, and a path that is not a directory all decline.
        self.assertIsNone(role_launch.journal_root(self.root / 'absent.conf'))
        commented = self.root / 'empty.conf'
        commented.write_text('# nothing here\n')
        self.assertIsNone(role_launch.journal_root(commented))
        gone = self.root / 'gone.conf'
        gone.write_text(str(self.root / 'not-a-directory') + '\n')
        self.assertIsNone(role_launch.journal_root(gone))
        # Every role carries the root; the tool decides what each of them may write.
        with mock.patch.object(role_launch, 'JOURNAL_CONF', conf):
            engineering, _ = self.plan()
            self.assertEqual(engineering['journal'], str(vault))
            personal_id = conversations.create(self.store, 'morty', 'Personal fixture')['id']
            personal, env = role_launch.plan(personal_id, state_root=self.state, registry=self.registry,
                                             account='openai-apple', profiles_root=self.profiles,
                                             agents_root=self.agents)
            self.assertEqual(personal['journal'], str(vault))
            self.assertEqual(json.loads(env['DEV_PLATFORM_ROLE_LAUNCH'])['journalRoot'], str(vault))

    def test_the_pi_package_resolves_in_a_release_that_ships_no_node_modules(self):
        # A release excludes integrations/pi/node_modules, so a launch would die on an
        # unresolved import. A working checkout hides that, which is how it shipped broken.
        platform = self.root / 'release'
        (platform / 'integrations/pi').mkdir(parents=True)
        pinned = self.root / 'pi-runtime' / '0.87.1' / 'node_modules'
        (pinned / role_launch.PI_PACKAGE).mkdir(parents=True)
        with mock.patch.object(role_launch, 'PI_RUNTIMES', self.root / 'pi-runtime'):
            linked = role_launch.pi_modules(platform)
            self.assertTrue(linked.is_symlink())
            self.assertEqual(linked.resolve(), pinned.resolve())
            # Idempotent: a second call keeps the same link.
            self.assertEqual(role_launch.pi_modules(platform), linked)
            # A real directory holding the package is used untouched.
            other = self.root / 'checkout'
            (other / 'integrations/pi/node_modules' / role_launch.PI_PACKAGE).mkdir(parents=True)
            self.assertFalse(role_launch.pi_modules(other).is_symlink())
            # A real directory WITHOUT the package is a broken install, not something to guess at.
            bare = self.root / 'bare'
            (bare / 'integrations/pi/node_modules').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'without the Pi package'):
                role_launch.pi_modules(bare)
        missing = self.root / 'no-runtime'
        (missing / 'integrations/pi').mkdir(parents=True)
        with mock.patch.object(role_launch, 'PI_RUNTIMES', self.root / 'absent'):
            with self.assertRaisesRegex(ValueError, 'pinned Pi runtime is not installed'):
                role_launch.pi_modules(missing)

    def test_resume_only_from_this_conversation_and_clean_environment(self):
        self.configure_profile()
        with self.assertRaisesRegex(ValueError, 'no native Pi session'):
            self.plan(resume='latest')
        older = self.home / 'native/pi/older.jsonl'
        older.write_text('{}\n')
        os.utime(older, (1, 1))
        newer = self.home / 'native/pi/newer.jsonl'
        newer.write_text('{}\n')
        self.assertEqual(self.plan(resume='latest')[0]['resume_file'], str(newer))
        self.assertEqual(self.plan(resume=str(older))[0]['resume_file'], str(older))
        outside = self.root / 'outside.jsonl'
        outside.write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'inside this conversation'):
            self.plan(resume=str(outside))
        with self.assertRaisesRegex(ValueError, 'conflicting inherited'):
            self.plan(environ={**os.environ, 'OPENAI_API_KEY': 'x'})

    def test_offline_launch_renders_role_terminal_under_conversation_lock(self):
        node = shutil.which('node')
        if not node or not (ROOT / 'integrations/pi/node_modules/@earendil-works/pi-coding-agent').is_dir():
            self.skipTest('Node and the pinned Pi package are required for the terminal launch check')
        self.configure_profile()
        pid, fd = pty.fork()
        if pid == 0:  # pragma: no cover - child replaced by the launcher
            env = {key: os.environ[key] for key in ('PATH', 'LANG') if key in os.environ}
            env.update(HOME=str(self.root / 'home'), TERM='xterm-256color')
            os.execve(sys.executable, [sys.executable, str(ROOT / 'bin/ai-role'), '--state-root', str(self.state),
                                       '--registry', str(self.registry), '--profiles-root', str(self.profiles),
                                       '--agents-root', str(self.agents), 'launch', self.conversation['id'],
                                       '--account', 'openai-apple', '--offline'], env)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 220, 0, 0))
        output, sent, status = b'', False, None
        deadline = time.monotonic() + 30
        try:
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .2)[0]:
                    try:
                        output += os.read(fd, 65536)
                    except OSError:
                        pass
                if not sent and all(marker in output for marker in
                                    (b'perplexity', b'skills/develop/', b'identity.md', b'[Skills]')):
                    os.write(fd, b'\x04')  # native Ctrl+D on an empty editor
                    sent = True
                done, status = os.waitpid(pid, os.WNOHANG)
                if done:
                    break
            else:
                os.kill(pid, signal.SIGKILL)
                _, status = os.waitpid(pid, 0)
        finally:
            os.close(fd)
        text = output.decode(errors='replace')
        self.assertTrue(sent, text[-4000:])
        self.assertEqual(os.waitstatus_to_exitcode(status), 0, text[-4000:])
        self.assertIn('iztac | formation | cwd', text)
        with open(self.home / '.pi-writer.lock', 'r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == '__main__':
    unittest.main()
