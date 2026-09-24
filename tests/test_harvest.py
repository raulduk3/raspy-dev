"""The Harvest command and its tool. Nothing here reads a credential or calls the API."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'bin/harvest'


class HarvestCommand(unittest.TestCase):
    def test_the_command_is_present_executable_and_valid_shell(self):
        self.assertTrue(COMMAND.is_file())
        self.assertTrue(os.access(COMMAND, os.X_OK))
        subprocess.run(['bash', '-n', str(COMMAND)], check=True, capture_output=True)

    def test_help_needs_no_credential(self):
        # The Keychain read is lazy, so help works on any machine and in any test run.
        result = subprocess.run([str(COMMAND), 'help'], capture_output=True, text=True, timeout=30,
                                env={'PATH': os.environ.get('PATH', ''), 'HOME': os.environ.get('HOME', '')})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('harvest hours', result.stdout)
        self.assertIn('harvest update <id> [--hours H]', result.stdout)
        self.assertNotIn('Bearer', result.stdout)

    def test_the_token_is_only_read_by_the_commands_that_call_the_api(self):
        text = COMMAND.read_text()
        # One lazy reader, invoked per API command, rather than a read at startup.
        self.assertEqual(text.count('security find-generic-password'), 1)
        self.assertIn('authenticate() {', text)
        self.assertEqual(text.count('    authenticate\n'), 6)
        # The secret is never echoed.
        self.assertNotIn('echo "$TOKEN"', text)
        self.assertNotIn('echo $TOKEN', text)


class HarvestTool(unittest.TestCase):
    def test_offline_tool_checks_pass(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for the Harvest tool checks')
        result = subprocess.run([node, str(ROOT / 'integrations/pi/check-harvest-tool.mjs')],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"passed": true', result.stdout)


if __name__ == '__main__':
    unittest.main()
