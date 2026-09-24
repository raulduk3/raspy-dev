"""Hermetic tests for lib/ai_ecosystem/profiles.py: home provisioning.

No native login, no network, no real ~/.claude or ~/.codex. Fake homes and
fake "live default" instruction sources live entirely under a TemporaryDirectory.
The one real, shared thing read from disk is this repository's own hooks/
directory (hooks/claude-settings.hooks.json, hooks/codex.rules) -- the
authoritative fragments profiles.py is supposed to install verbatim.
"""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import accounts
from ai_ecosystem import profiles


def write_registry(path, bindings):
    path.write_text(json.dumps({'version': 1, 'selected': None, 'bindings': bindings}))


class ProfilesBase(unittest.TestCase):
    def setUp(self):
        # The service and its tests refuse inherited provider overrides; strip them
        # the same way tests/test_host_environment.py does.
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Resolve once up front: macOS puts TemporaryDirectory() under /var, a
        # symlink to /private/var, which would otherwise trip the ancestor-symlink
        # refusal on every single test.
        self.root = Path(self.tmp.name).resolve()
        self.registry = self.root / 'accounts.json'
        self.default_claude_home = self.root / 'default-claude'
        self.default_codex_home = self.root / 'default-codex'
        self.default_claude_home.mkdir()
        self.default_codex_home.mkdir()
        (self.default_claude_home / 'CLAUDE.md').write_text('# Fixture global Claude instructions\nBe direct.\n')
        (self.default_codex_home / 'AGENTS.md').write_text('# Fixture global Codex instructions\nBe direct.\n')

    def claude_home(self, name='anthropic-apple'):
        home = self.root / 'homes' / name
        home.mkdir(parents=True, mode=0o700)
        write_registry(self.registry, {name: {'home': str(home), 'expected_email': 'x@example.invalid'}})
        return home

    def codex_home(self, name='openai-gmail'):
        home = self.root / 'homes' / name
        home.mkdir(parents=True, mode=0o700)
        write_registry(self.registry, {name: {'home': str(home), 'expected_email': 'x@example.invalid'}})
        return home

    def apply_claude(self, name='anthropic-apple'):
        return profiles.apply(name, self.registry, default_home_root=self.default_claude_home)

    def plan_claude(self, name='anthropic-apple'):
        return profiles.plan(name, self.registry, default_home_root=self.default_claude_home)

    def apply_codex(self, name='openai-gmail'):
        return profiles.apply(name, self.registry, default_home_root=self.default_codex_home)


class BareClaudeHome(ProfilesBase):
    def test_bare_home_gains_hooks_instructions_and_status_line(self):
        home = self.claude_home()
        result = self.apply_claude()
        self.assertEqual(result['runtime'], 'claude')
        settings_path = home / 'settings.json'
        claude_md = home / 'CLAUDE.md'
        self.assertTrue(settings_path.is_file())
        self.assertEqual(settings_path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(claude_md.is_file())
        self.assertEqual(claude_md.stat().st_mode & 0o777, 0o600)

        settings = json.loads(settings_path.read_text())
        commands = {hook['command']
                    for event in ('PreToolUse', 'PostToolUse', 'Stop')
                    for entry in settings['hooks'][event]
                    for hook in entry['hooks']}
        self.assertIn('$HOME/Dev/dev-platform/hooks/pre-tool-use-guard.sh', commands)
        self.assertIn('$HOME/Dev/dev-platform/hooks/post-tool-use-format.sh', commands)
        self.assertIn('$HOME/Dev/dev-platform/hooks/stop-check.sh', commands)
        self.assertEqual(settings['statusLine'], {
            'type': 'command',
            'command': 'python3 $HOME/Dev/dev-platform/integrations/claude/usage-collector.py '
                       '--account anthropic-apple',
        })
        self.assertIn('Fixture global Claude instructions', claude_md.read_text())
        self.assertIn(profiles.MANAGED_BEGIN, claude_md.read_text())

        # Nothing else was created in the home.
        self.assertEqual(sorted(p.name for p in home.iterdir()), ['CLAUDE.md', 'settings.json'])

    def test_second_apply_is_byte_identical_noop(self):
        home = self.claude_home()
        self.apply_claude()
        settings_before = (home / 'settings.json').read_bytes()
        claude_md_before = (home / 'CLAUDE.md').read_bytes()
        backups_before = sorted(home.glob('*.bak'))
        result = self.apply_claude()
        for action in result['actions']:
            self.assertEqual(action['action'], 'unchanged', action)
        self.assertEqual((home / 'settings.json').read_bytes(), settings_before)
        self.assertEqual((home / 'CLAUDE.md').read_bytes(), claude_md_before)
        self.assertEqual(sorted(home.glob('*.bak')), backups_before)

    def test_plan_is_read_only(self):
        home = self.claude_home()
        result = self.plan_claude()
        self.assertEqual(result['mode'], 'plan')
        self.assertEqual(list(home.iterdir()), [])
        for action in result['actions']:
            self.assertIn(action['action'], ('created', 'merged'))
            self.assertNotIn('bytes', action)

    def test_provisioned_settings_passes_configuration_check(self):
        home = self.claude_home()
        self.apply_claude()
        # Must not raise: the platform's own account-selection safety scan must
        # accept the file this module writes.
        accounts.configuration_check('anthropic-apple', home, self.root)


class ExistingUserSettings(ProfilesBase):
    def test_existing_settings_json_is_merged_not_clobbered(self):
        home = self.claude_home()
        original = {
            'foo': 'bar',
            'hooks': {'PreToolUse': [{'matcher': 'Something', 'hooks': [{'type': 'command', 'command': 'custom.sh'}]}]},
        }
        original_bytes = (json.dumps(original, indent=2) + '\n').encode()
        (home / 'settings.json').write_bytes(original_bytes)

        result = self.apply_claude()
        settings_action = next(a for a in result['actions'] if a['kind'] == 'settings')
        self.assertEqual(settings_action['action'], 'merged')
        self.assertIn('backup', settings_action)
        backup_path = Path(settings_action['backup'])
        self.assertTrue(backup_path.is_file())
        self.assertEqual(backup_path.read_bytes(), original_bytes)
        self.assertEqual(backup_path.stat().st_mode & 0o777, 0o600)

        merged = json.loads((home / 'settings.json').read_text())
        self.assertEqual(merged['foo'], 'bar')
        pre_tool_commands = {hook['command'] for entry in merged['hooks']['PreToolUse'] for hook in entry['hooks']}
        self.assertIn('custom.sh', pre_tool_commands)
        self.assertIn('$HOME/Dev/dev-platform/hooks/pre-tool-use-guard.sh', pre_tool_commands)

    def test_existing_claude_md_is_merged_preserving_original_text(self):
        home = self.claude_home()
        (home / 'CLAUDE.md').write_text('My own personal notes.\n')
        result = self.apply_claude()
        instructions_action = next(a for a in result['actions'] if a['kind'] == 'instructions')
        self.assertEqual(instructions_action['action'], 'merged')
        self.assertIn('backup', instructions_action)
        content = (home / 'CLAUDE.md').read_text()
        self.assertIn('My own personal notes.', content)
        self.assertIn('Fixture global Claude instructions', content)


class SecretsAreUntouched(ProfilesBase):
    def test_auth_json_is_never_opened_or_modified(self):
        home = self.claude_home()
        auth = home / 'auth.json'
        auth.write_bytes(b'{"secret": "do-not-touch"}')
        original = auth.read_bytes()
        os.chmod(auth, 0)
        try:
            self.apply_claude()  # must not raise PermissionError, and must not touch auth.json
        finally:
            os.chmod(auth, 0o600)
        self.assertEqual(auth.read_bytes(), original)

    def test_credentials_json_is_never_opened_or_modified(self):
        home = self.claude_home()
        creds = home / '.credentials.json'
        creds.write_bytes(b'{"secret": "do-not-touch"}')
        original = creds.read_bytes()
        os.chmod(creds, 0)
        try:
            self.apply_claude()
        finally:
            os.chmod(creds, 0o600)
        self.assertEqual(creds.read_bytes(), original)


class SymlinkRefusals(ProfilesBase):
    def test_symlinked_home_is_refused(self):
        real_home = self.root / 'real-home'
        real_home.mkdir(mode=0o700)
        link_home = self.root / 'link-home'
        link_home.symlink_to(real_home)
        write_registry(self.registry, {'anthropic-apple': {'home': str(link_home), 'expected_email': 'x@example.invalid'}})
        with self.assertRaises(ValueError):
            self.plan_claude()
        with self.assertRaises(ValueError):
            self.apply_claude()
        self.assertEqual(list(real_home.iterdir()), [])

    def test_symlinked_ancestor_is_refused(self):
        real_dir = self.root / 'real-dir'
        real_dir.mkdir()
        shortcut = self.root / 'shortcut'
        shortcut.symlink_to(real_dir)
        home = shortcut / 'anthropic-apple'
        write_registry(self.registry, {'anthropic-apple': {'home': str(home), 'expected_email': 'x@example.invalid'}})
        with self.assertRaises(ValueError):
            self.apply_claude()


class NativeDefaultRefusal(ProfilesBase):
    def test_apply_refuses_native_default_binding(self):
        home = self.claude_home()
        write_registry(self.registry, {'anthropic-apple': {'home': str(home), 'expected_email': 'x@example.invalid',
                                                            'native_default': True}})
        with self.assertRaises(ValueError):
            self.apply_claude()
        self.assertEqual(list(home.iterdir()), [])
        # plan() is still allowed (read-only audit of an already-equipped default home).
        result = self.plan_claude()
        self.assertEqual(result['mode'], 'plan')


class CodexHome(ProfilesBase):
    def test_bare_codex_home_gains_agents_md_and_guard_rules(self):
        home = self.codex_home()
        result = self.apply_codex()
        self.assertEqual(result['runtime'], 'codex')
        agents_md = home / 'AGENTS.md'
        rules = home / 'rules' / 'default.rules'
        self.assertTrue(agents_md.is_file())
        self.assertEqual(agents_md.stat().st_mode & 0o777, 0o600)
        self.assertTrue(rules.is_file())
        self.assertEqual(rules.stat().st_mode & 0o777, 0o600)
        self.assertEqual(rules.parent.stat().st_mode & 0o777, 0o700)
        self.assertIn('Fixture global Codex instructions', agents_md.read_text())
        managed_body = rules.read_text().split(profiles.MANAGED_BEGIN, 1)[1].split(profiles.MANAGED_END, 1)[0]
        self.assertEqual((ROOT / 'hooks' / 'codex.rules').read_text().strip('\n'), managed_body.strip('\n'))

    def test_second_apply_is_noop(self):
        home = self.codex_home()
        self.apply_codex()
        before = {p.name: p.read_bytes() for p in [home / 'AGENTS.md', home / 'rules' / 'default.rules']}
        result = self.apply_codex()
        for action in result['actions']:
            self.assertEqual(action['action'], 'unchanged', action)
        after = {p.name: p.read_bytes() for p in [home / 'AGENTS.md', home / 'rules' / 'default.rules']}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
