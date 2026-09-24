"""Real CLI reads: source references, filtering and original-byte preservation."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'bin/journal'

class Journal(unittest.TestCase):
    def test_real_notes_preserved_and_filtered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            note = root / 'project.md'
            note.write_text('---\ntitle: Work\n---\n- [ ] Ship #work 📅 2026-09-24 🔁 every week\n  - [/] Check #work\n- [x] Shipped ✅ 2026-09-23\n- [-] Cancelled ❌ 2026-09-22\n```markdown\n- [ ] Example\n```\n- [?] Unknown\n- [ ] Bad date 📅 2026-02-30\n- [x] Conflicting ❌ 2026-09-20\n')
            (root/'5. archive').mkdir()
            (root/'5. archive/old.md').write_text('- [ ] Historical\n')
            (root/'alias.md').symlink_to(note)
            before = {p: p.read_bytes() for p in root.rglob('*.md')}
            def run(*args):
                result = subprocess.run([str(CLI),'--root',str(root),'tasks','--json',*args], capture_output=True,text=True,check=True)
                return json.loads(result.stdout)['tasks']
            opened = run()
            self.assertEqual([(r['line'],r['status']) for r in opened], [(4,'todo'),(5,'in-progress'),(11,'unknown'),(12,'todo')])
            self.assertEqual(opened[2]['warnings'],['unknown_status'])
            self.assertEqual(opened[3]['warnings'],['invalid_due_date'])
            due = run('--tag','#work','--due-on-or-before','2026-09-24')
            self.assertEqual([(r['path'],r['line'],r['recurring']) for r in due],[('project.md',4,True)])
            self.assertEqual(run('--status','done')[-1]['warnings'],['cancellation_marker_status_conflict'])
            self.assertEqual(len(run('--status','all','--include-history')),8)
            self.assertEqual(before,{p:p.read_bytes() for p in before})
            bad = subprocess.run([str(CLI),'--root',str(root),'tasks','--due-on-or-before','2026-02-30'],capture_output=True)
            self.assertEqual(bad.returncode,2)
