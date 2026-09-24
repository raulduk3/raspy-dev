"""Exercise a real SQLite history store and prove reads preserve its bytes."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from ai_ecosystem.history import connect, messages, search, windows


class History(unittest.TestCase):
    def test_literal_search_pagination_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sqlite-consistent').mkdir()
            db = root / 'sqlite-consistent/hermes.sqlite'
            with sqlite3.connect(db) as c:
                c.executescript('''CREATE TABLE session_nodes(session_key, current_session_id,
                    label, display_name, updated_at);
                    CREATE TABLE session_windows(session_id, session_key,
                        previous_session_id, reason, created_at, updated_at);
                    CREATE TABLE transcript_events(session_id, seq, event_json, created_at);
                    INSERT INTO session_nodes VALUES('key','id','100% preserved','label',1);
                    INSERT INTO session_windows VALUES('old','key',NULL,'start',0,0);
                    INSERT INTO session_windows VALUES('id','key','old','reset',1,1);''')
                for seq in range(3):
                    c.execute('INSERT INTO transcript_events VALUES(?,?,?,?)',
                              ('id', seq, json.dumps({'message': {'role': 'user',
                               'content': [{'type': 'text', 'text': str(seq)}]}}), seq))
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            c = connect(root, 'iztac')
            try:
                self.assertEqual(len(search(c, '%', 10)), 1)
                self.assertEqual(search(c, "' OR 1=1 --", 10), [])
                timeline = windows(c, 'key', 10)
                self.assertEqual([row['session_id'] for row in timeline], ['old', 'id'])
                self.assertEqual(timeline[1]['previous_session_id'], 'old')
                self.assertEqual(windows(c, 'missing', 10), [])
                page = messages(c, 'id', -1, 2)
                self.assertTrue(page['has_more'])
                self.assertEqual(page['next_after'], 1)
                self.assertEqual(messages(c, 'id', 1, 2)['messages'][0]['text'], '2')
                with self.assertRaises(sqlite3.OperationalError):
                    c.execute('DELETE FROM session_nodes')
                with self.assertRaises(ValueError):
                    messages(c, 'missing', -1, 2)
            finally:
                c.close()
            self.assertEqual(before, hashlib.sha256(db.read_bytes()).hexdigest())
