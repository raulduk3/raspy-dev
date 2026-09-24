"""ai-env doctor against a temp home with absent binaries and broken links; must not mutate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-env'


class Doctor(unittest.TestCase):
    def test_reports_missing_and_broken_without_mutation(self):
        with tempfile.TemporaryDirectory(prefix='ai-env-') as tmp:
            home = Path(tmp)
            skills = home / '.claude/skills'
            skills.mkdir(parents=True)
            os.symlink(home / 'nowhere', skills / 'gone')
            (home / 'elsewhere/loop').mkdir(parents=True)
            os.symlink(home / 'elsewhere/loop', skills / 'loop')
            before = sorted((str(p), os.readlink(p) if p.is_symlink() else None) for p in home.rglob('*'))
            run = subprocess.run([sys.executable, str(CLI), 'doctor', '--json', '--home', str(home)],
                                 capture_output=True, text=True, env={'PATH': '/nonexistent', 'HOME': str(home)})
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report['commands']['claude']['state'], 'missing')
            self.assertEqual(report['skills']['.claude/skills']['broken'], ['gone'])
            self.assertEqual(report['skills']['.claude/skills']['divergent'], ['loop'])
            self.assertEqual(report['skills']['.codex/skills']['state'], 'missing')
            self.assertEqual(report['platform_check']['state'], 'ok')
            self.assertEqual(report['laya']['probe']['state'], 'unverified')
            self.assertEqual(report['laya']['listener']['state'], 'unverified')
            after = sorted((str(p), os.readlink(p) if p.is_symlink() else None) for p in home.rglob('*'))
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
