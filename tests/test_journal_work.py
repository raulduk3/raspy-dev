"""Structured work entries: what one role writes is exactly what another parses."""
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import journal_daily as daily

DASH = '—'


class WorkEntries(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='journal-work-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.today = daily.day()
        self.note = daily.location(self.root, self.today, personal=True)

    def run_cli(self, *args):
        result = subprocess.run([sys.executable, str(ROOT / 'bin/journal'), '--root', str(self.root), *args],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_the_written_line_is_the_parsed_line(self):
        self.run_cli('work', '--role', 'Iztac', '--summary', 'Deployed the webhook fix.',
                     '--project', 'layer7-voice-agent', '--minutes', '75')
        self.run_cli('work', '--role', 'Morty', '--summary', 'Reconciled September hours.')
        read = self.run_cli('entries')
        self.assertEqual([e['role'] for e in read['entries']], ['Iztac', 'Morty'])
        first = read['entries'][0]
        self.assertEqual(first['project'], 'layer7-voice-agent')
        self.assertEqual(first['minutes'], 75)
        self.assertEqual(first['summary'], 'Deployed the webhook fix.')
        # Work with no project cannot be billed, and the reader says so rather than guessing.
        self.assertEqual([e['role'] for e in read['unattributed']], ['Morty'])

    def test_it_matches_the_shape_the_vault_already_uses(self):
        # An entry written before this tool existed still parses, with no project.
        self.note.parent.mkdir(parents=True, exist_ok=True)
        self.note.write_text('---\ntitle: X\n---\n\n# Notes\n\n'
                             f'- Installed shared session discovery and handoff. {DASH} Iztac\n')
        read = self.run_cli('entries')
        self.assertEqual(len(read['entries']), 1)
        self.assertIsNone(read['entries'][0]['project'])
        self.assertIsNone(read['entries'][0]['minutes'])
        self.assertEqual(read['entries'][0]['role'], 'Iztac')
        # And a new labelled entry joins it without disturbing the old one.
        self.run_cli('work', '--role', 'Iztac', '--summary', 'Shipped it.', '--project', 'dev-platform')
        self.assertIn(f'- Installed shared session discovery and handoff. {DASH} Iztac',
                      self.note.read_text())
        self.assertEqual(len(self.run_cli('entries')['entries']), 2)

    def test_writing_the_same_entry_twice_adds_one_line(self):
        for _ in range(2):
            self.run_cli('work', '--role', 'Iztac', '--summary', 'Same work.', '--project', 'p')
        self.assertEqual(len(self.run_cli('entries')['entries']), 1)

    def test_a_work_entry_always_lands_in_todays_note(self):
        self.run_cli('work', '--role', 'Neo', '--summary', 'Checked the trust boundary.')
        self.assertTrue(self.note.is_file())
        self.assertIn(f'{self.today:%d-%m-%Y}.md', str(self.note))
        self.assertIn('title: ' + daily.written_date(self.today), self.note.read_text())

    def test_tasks_use_the_format_the_vault_already_reads(self):
        line = daily.task_line('inventory sound equipment', 'film', due='2026-10-01',
                               scheduled='2026-09-30', priority='high')
        self.assertEqual(line, '- [ ] inventory sound equipment #film ⏫ ⏳ 2026-09-30 \U0001f4c5 2026-10-01')
        self.run_cli('task', '--text', 'call the studio', '--tag', 'work', '--due', '2026-10-02')
        self.assertIn('- [ ] call the studio #work \U0001f4c5 2026-10-02', self.note.read_text())

    def test_malformed_input_is_refused_rather_than_written(self):
        for bad in (('Nobody', 'x', None, None), ('Iztac', '   ', None, None),
                    ('Iztac', 'x', 'bad]label', None)):
            with self.assertRaises(ValueError):
                daily.work_line(*bad)
        with self.assertRaises(ValueError):
            daily.task_line('')
        with self.assertRaises(ValueError):
            daily.task_line('x', tag='two words')
        with self.assertRaises(ValueError):
            daily.task_line('x', priority='urgent')
        self.assertFalse(self.note.exists())

    def test_durations_and_written_dates_round_trip(self):
        for value in (5, 45, 60, 75, 120, 1440):
            self.assertEqual(daily.minutes(daily.span(value)), value)
        self.assertIsNone(daily.minutes('soon'))
        self.assertEqual(daily.written_date(date(2026, 9, 1)), 'September 1st 2026')
        self.assertEqual(daily.written_date(date(2026, 9, 11)), 'September 11th 2026')
        self.assertEqual(daily.written_date(date(2026, 9, 23)), 'September 23rd 2026')


if __name__ == '__main__':
    unittest.main()
