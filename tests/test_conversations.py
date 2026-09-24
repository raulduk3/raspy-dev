"""Exercise conversation creation and native association through real CLI/files."""
import json
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'bin/ai-session'


class Conversations(unittest.TestCase):
    def test_scopes_and_native_association_survive_rescan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, state, project = root / 'home', root / 'state', root / 'project'
            project.mkdir()
            native = home / '.claude/projects/example'
            native.mkdir(parents=True)
            transcript = native / 'native-one.jsonl'
            original = json.dumps({'sessionId': 'native-one', 'cwd': str(project),
                                   'type': 'user', 'message': {'content': 'private history'}}) + '\n'
            transcript.write_text(original)
            env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1')

            def run(*args, ok=True):
                p = subprocess.run([str(CLI), '--state-root', str(state), *args],
                                   env=env, capture_output=True, text=True)
                if ok:
                    self.assertEqual(p.returncode, 0, p.stderr)
                    return json.loads(p.stdout)
                self.assertNotEqual(p.returncode, 0)

            morty = run('conversation', 'create', '--agent', 'morty', '--title', 'Personal')
            self.assertEqual(morty['scope'], {'kind': 'personal'})
            self.assertEqual(morty['binding'], {})
            run('conversation', 'create', '--agent', 'morty', '--title', 'Wrong',
                '--project', 'example', '--workspace', str(project), ok=False)
            run('conversation', 'create', '--agent', 'iztac', '--title', 'Missing project', ok=False)
            run('conversation', 'create', '--agent', 'neo', '--title', 'Missing scope', ok=False)
            neo = run('conversation', 'create', '--agent', 'neo', '--title', 'Operations', '--resource', 'local-host')
            self.assertEqual(neo['scope']['kind'], 'system')
            iztac = run('conversation', 'create', '--agent', 'iztac', '--title', 'Formation',
                        '--formation', '--workspace', str(project))
            self.assertEqual(iztac['scope'], {'kind': 'formation'})
            repository = root / 'repo'
            repository.mkdir()
            subprocess.run(['git', 'init', '-q', str(repository)], check=True)
            config = root / 'repos.conf'
            config.write_text(f'owner/example {repository} owner develop\n')
            run('conversation', 'create', '--agent', 'iztac', '--title', 'Wrong checkout',
                '--project', 'owner/example', '--workspace', str(project), '--repos', str(config), ok=False)
            engineering = run('conversation', 'create', '--agent', 'iztac', '--title', 'Known project',
                '--project', 'owner/example', '--workspace', str(repository), '--repos', str(config))
            self.assertEqual(engineering['scope']['kind'], 'project')
            self.assertNotEqual(engineering['scope']['project_id'], 'owner/example')
            run('scan', '--home', str(home), '--no-openclaw')
            record = run('list', '--json')['sessions'][0]
            run('conversation', 'bind', engineering['id'], record['id'], '--expect-revision', str(record['revision']), ok=False)
            run('conversation', 'bind', iztac['id'], record['id'], '--expect-revision', str(record['revision']))
            run('scan', '--home', str(home), '--no-openclaw')
            result = run('conversation', 'show', iztac['id'])
            self.assertEqual(result['native_sessions'][0]['id'], record['id'])
            self.assertEqual(result['native_sessions'][0]['conversation_id'], iztac['id'])
            revision = result['native_sessions'][0]['revision']
            run('conversation', 'bind', neo['id'], record['id'], '--expect-revision', str(revision), ok=False)
            self.assertTrue((Path(result['home']) / 'native/pi').is_dir())
            self.assertEqual(transcript.read_text(), original)
            self.assertNotIn('private history', json.dumps(result))
            self.assertEqual(Path(result['home']).stat().st_mode & 0o777, 0o700)
            listed = run('conversation', 'list')['conversations']
            self.assertEqual({r['id'] for r in listed}, {morty['id'], neo['id'], iztac['id'], engineering['id']})
