import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI=Path(__file__).resolve().parents[1]/'bin/journal'

class Daily(unittest.TestCase):
    def test_daily_layout_retry_and_section_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def run(command,*args,ok=True):
                result=subprocess.run([str(CLI),'--root',str(root),command,'2026-09-24',*args],capture_output=True,text=True)
                if not ok:
                    self.assertNotEqual(result.returncode,0)
                    return
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            first=run('log-append','--title','Work','--body','Verified result.')
            self.assertTrue(first['changed'])
            log=root/'0. morty/2026/09/2026-09-24.md'
            self.assertEqual(log.read_text(),'# 2026-09-24\n\n## Work\n\nVerified result.\n')
            self.assertFalse(run('log-append','--title','Work','--body','Verified result.')['changed'])
            before=log.read_bytes()
            run('log-append','--title','Work','--body','Different result.',ok=False)
            self.assertEqual(log.read_bytes(),before)
            note=root/'1. journal/2026/09/24-09-2026.md'
            run('journal-ensure')
            self.assertNotIn('```tasks',note.read_text())
            note.write_text('---\ntitle: Keep this\n---\n\n# Notes\nMy words.\n\n# Other\nKeep this too.\n')
            line='Confirmed the result.'
            self.assertTrue(run('journal-line','--line',line)['changed'])
            expected='---\ntitle: Keep this\n---\n\n# Notes\nMy words.\nConfirmed the result. ([[0. morty/2026/09/2026-09-24|Morty log]])\n\n# Other\nKeep this too.\n'
            self.assertEqual(note.read_text(),expected)
            self.assertFalse(run('journal-line','--line',line)['changed'])
            before=note.read_bytes()
            run('journal-line','--line','bad\nentry',ok=False)
            self.assertEqual(note.read_bytes(),before)

    def test_symlinks_and_legacy_conflicts_are_not_rewritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            target=root/'existing.md';target.write_text('Keep me')
            logs=root/'0. morty/2026/09';logs.mkdir(parents=True)
            canonical=logs/'2026-09-24.md';canonical.symlink_to(target)
            args=[str(CLI),'--root',str(root),'log-ensure','2026-09-24']
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(target.read_text(),'Keep me')
            legacy=root/'0. morty/2026-09-25.md';legacy.write_text('Older record')
            args[-1]='2026-09-25'
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertFalse((logs/'2026-09-25.md').exists())

    def test_two_writers_keep_both_log_sections(self):
        with tempfile.TemporaryDirectory() as folder:
            args=[str(CLI),'--root',folder,'log-append','2026-09-24']
            workers=[subprocess.Popen([*args,'--title',title,'--body',title],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for title in ('One','Two')]
            for worker in workers:
                _,error=worker.communicate(timeout=10)
                self.assertEqual(worker.returncode,0,error)
            text=(Path(folder)/'0. morty/2026/09/2026-09-24.md').read_text()
            self.assertEqual(text.count('## One'),1)
            self.assertEqual(text.count('## Two'),1)
