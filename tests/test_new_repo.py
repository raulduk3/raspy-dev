"""new-repo is installed as a link in ~/.local/bin and must still find the release's templates."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NewRepo(unittest.TestCase):
    def test_runs_through_a_link_like_the_installed_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'bin').mkdir()
            (tmp / 'bin/new-repo').symlink_to(ROOT / 'bin/new-repo')
            home = tmp / 'home'
            home.mkdir()
            # No bun on PATH keeps the run offline; new-repo warns and still commits.
            env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'GIT_CONFIG_GLOBAL': str(home / '.gitconfig'),
                   'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com',
                   'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.com'}
            result = subprocess.run([str(tmp / 'bin/new-repo'), str(tmp / 'game'), '--owner', 'someone'],
                                    capture_output=True, text=True, env=env)
            self.assertNotIn('No such file or directory', result.stderr)
            self.assertTrue((tmp / 'game/AGENTS.md').is_file(), result.stderr)
            self.assertTrue((tmp / 'game/docs/spec').is_dir())


if __name__ == '__main__':
    unittest.main()
