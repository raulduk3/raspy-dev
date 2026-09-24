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
                                    (b'perplexity', b'session-entry', b'identity.md', b'[Skills]')):
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
