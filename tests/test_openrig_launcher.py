"""Launcher boundaries: native calls without real agents or host configuration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / 'bin/dev-workspace'


class WorkspaceLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / 'calls.jsonl'
        rig = self.root / 'app/node_modules/.bin/rig'
        rig.parent.mkdir(parents=True)
        node = self.root / 'node-v24.14.0-darwin-arm64/bin/node'
        node.parent.mkdir(parents=True)
        node.touch()
        rig.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps({'args':a, 'codex_home':os.environ.get('CODEX_HOME')})+'\\n')
if a == ['--version']: print('0.5.14 (cc75efdd)')
elif a == ['daemon', 'status']: print(os.environ.get('DAEMON_STATE', 'Daemon running on port 4400 (pid 1)'))
elif a[0] == 'ps': print(os.environ.get('RIGS', '[]'))
elif a[0] == 'up' and '--plan' in a and os.environ.get('PLAN_FAIL'): sys.exit(7)
''')
        rig.chmod(0o755)
        self.env = dict(os.environ, DEV_WORKSPACE_RUNTIME=str(self.root), CALLS=str(self.log),
                        CODEX_HOME='/not-the-personal-store')

    def call(self, *args):
        return subprocess.run([str(LAUNCHER), *args], env=self.env, text=True, capture_output=True)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_open_starts_only_missing_daemon_and_tui(self):
        self.env['DAEMON_STATE'] = 'Daemon stopped'
        self.assertEqual(self.call().returncode, 0)
        records = self.records()
        self.assertEqual([r['args'] for r in records], [
            ['--version'], ['daemon', 'status'], ['daemon', 'start', '--no-kernel'], ['tui']])
        self.assertTrue(all(r['codex_home'] is None for r in records))

    def test_open_reuses_running_daemon_and_shared_is_explicit(self):
        self.assertEqual(self.call('open', '--shared').returncode, 0)
        self.assertEqual([r['args'] for r in self.records()],
                         [['--version'], ['daemon', 'status'], ['tui', '--shared']])

    def test_existing_seat_uses_native_restore_without_cwd_rebinding(self):
        self.env['RIGS'] = json.dumps([{'name':'development-codex'}])
        result = self.call('start', 'codex', '--cwd', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(commands, [['up', 'development-codex', '--existing', '--plan'],
                                    ['up', 'development-codex', '--existing']])

    def test_failed_new_plan_cannot_launch_a_seat(self):
        self.env['PLAN_FAIL'] = '1'
        self.assertNotEqual(self.call('start', 'claude', '--cwd', str(self.root)).returncode, 0)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 1)
        self.assertIn('--plan', commands[0])
        self.assertTrue(commands[0][1].endswith('integrations/openrig/claude.yaml'))

    def test_unverified_or_unhealthy_daemon_does_not_restart(self):
        for state in ['Daemon state UNVERIFIED', 'Daemon running on port 4400 — process present but UNHEALTHY']:
            with self.subTest(state=state):
                self.log.unlink(missing_ok=True)
                self.env['DAEMON_STATE'] = state
                self.assertNotEqual(self.call().returncode, 0)
                self.assertEqual(len(self.records()), 2)

    def test_plan_does_not_start_stopped_daemon(self):
        self.env['DAEMON_STATE'] = 'Daemon stopped'
        self.assertNotEqual(self.call('plan', 'codex', '--cwd', str(self.root)).returncode, 0)
        self.assertEqual(len(self.records()), 2)

    def test_archived_seat_is_not_recreated(self):
        self.env['RIGS'] = json.dumps([{'name':'development-codex', 'isArchived':True}])
        self.assertNotEqual(self.call('start', 'codex', '--cwd', str(self.root)).returncode, 0)
        self.assertFalse(any(r['args'][0] == 'up' for r in self.records()))
