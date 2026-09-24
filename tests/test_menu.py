"""The ai menu: scripted answers in, the exact hand-off command out. Nothing is launched."""
from contextlib import redirect_stdout
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MENU = Path(__file__).resolve().parents[1] / 'bin/ai'


def load_menu():
    loader = importlib.machinery.SourceFileLoader('ai_menu', str(MENU))
    spec = importlib.util.spec_from_loader('ai_menu', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class Menu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.menu = load_menu()
        self.menu.DRY = True
        self.menu.ENGAGEMENTS = self.root / 'engagements'
        self.menu.PI_PROFILES = self.root / 'pi'
        (self.root / 'pi/openai-apple').mkdir(parents=True)
        self.project = {'id': 'owner-repo-1', 'root': str(self.root / 'Research Agent'), 'repo': 'owner/repo',
                        'group': 'owner', 'source': 'repos.conf', 'loop_enabled': True, 'available': True,
                        'common_dir': None}
        Path(self.project['root']).mkdir()

    def drive(self, function, *answers, **kwargs):
        """Run one menu function with scripted answers; return what it printed."""
        replies = iter(answers)

        def answer(prompt=''):
            try:
                return next(replies)
            except StopIteration:
                raise EOFError from None
        out = io.StringIO()
        with mock.patch('builtins.input', answer), redirect_stdout(out):
            try:
                function(**kwargs)
            except self.menu.Quit:
                pass
        return out.getvalue()

    def runs(self, output):
        return [line[4:] for line in output.splitlines() if line.startswith('RUN ')]

    def test_claude_opens_in_the_project_on_the_account_with_most_room(self):
        rows = [{'account': 'anthropic-apple', 'client': 'Claude Code', 'state': 'cached', 'freshness': 'live',
                 'windows': [{'window': 'seven_day', 'used_percent': 56}]},
                {'account': 'anthropic-gmail', 'client': 'Claude Code', 'state': 'cached', 'freshness': 'live',
                 'windows': [{'window': 'seven_day', 'used_percent': 4}]}]
        with mock.patch.object(self.menu, 'usage_rows', return_value=rows):
            output = self.drive(self.menu.project_menu, '1', '1', project=self.project)
        self.assertIn('anthropic-gmail  cached        7d 4% used  · most room', output)
        run = self.runs(output)[0]
        self.assertIn('bin/ai-environment run --client claude --provider anthropic '
                      '--preferred-account anthropic-gmail --allow-unknown-quota', run)
        self.assertTrue(run.endswith(f"--cwd {self.project['root']}"))

    def test_a_session_resumes_by_picking_it(self):
        rows = {'sessions': [{'id': 'claude-abc', 'runtime': 'claude', 'owner': 'user', 'title': None,
                              'cwd': '/x/research-agent/.claude/worktrees/loop-4-fix', 'project': 'owner-repo-1',
                              'updated_at': '2026-09-24T00:00:00Z'},
                             {'id': 'openclaw-x', 'runtime': 'openclaw', 'owner': 'openclaw', 'title': None,
                              'cwd': '/x', 'project': None, 'updated_at': None}]}
        with mock.patch.object(self.menu, 'catalog', return_value=[self.project]), \
                mock.patch.object(self.menu.workspace, 'session_rows', return_value=rows):
            output = self.drive(self.menu.sessions_menu, '1', project=None)
        self.assertIn('[claude] · Research Agent · loop-4-fix', output)
        self.assertNotIn('openclaw', output)
        self.assertTrue(self.runs(output)[0].endswith('bin/ai-session resume claude-abc --execute'))

    def test_iztac_continues_the_projects_conversation_without_an_id(self):
        state = self.root / 'state'
        folder = state / 'conversations/conversation-0123456789abcdef0123'
        (folder / 'native/pi').mkdir(parents=True)
        (folder / 'native/pi/one.jsonl').write_text('{}\n')
        (folder / 'session.json').write_text(json.dumps({
            'version': 1, 'id': 'conversation-0123456789abcdef0123', 'agent': 'iztac', 'title': 'Research',
            'scope': {'kind': 'project', 'project_id': 'owner-repo-1'}, 'binding': {}, 'created_at': 1}))
        with mock.patch.dict(os.environ, {'AI_SESSION_STATE': str(state)}):
            output = self.drive(self.menu.role_menu, '1', agent='iztac', project=self.project)
            fresh = self.drive(self.menu.role_menu, '2', '', agent='iztac', project=self.project)
        self.assertIn('Continue: Research', output)
        self.assertTrue(self.runs(output)[0].endswith(
            'bin/ai-role launch conversation-0123456789abcdef0123 --account openai-apple --resume latest'))
        self.assertIn('conversation create --agent iztac --title Research Agent --project owner-repo-1 '
                      f"--workspace {self.project['root']}", self.runs(fresh)[0])

    def test_a_project_team_starts_outside_the_repository_under_its_own_name(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            output = self.drive(self.menu.project_team, 'y', '', project=self.project)
        folder = self.root / 'engagements/research-agent'
        self.assertTrue(folder.is_dir())
        self.assertTrue(self.runs(output)[0].endswith(
            f'bin/dev-workspace start iztac --cwd {folder} --rig iztac-research-agent'))
        with mock.patch.object(self.menu, 'rigs', return_value=[]):
            declined = self.drive(self.menu.project_team, 'n', project=self.project)
        self.assertEqual(self.runs(declined), [])

    def test_team_seats_attach_relaunch_and_stop(self):
        seats = [{'rigId': 'R1', 'logicalId': 'control.lead', 'runtime': 'claude-code', 'sessionStatus': 'running',
                  'lifecycleState': 'attention_required',
                  'agentActivity': {'state': 'needs_input', 'reason': 'selection_prompt'},
                  'canonicalSessionName': 'control-lead@t'},
                 {'rigId': 'R1', 'logicalId': 'review.overseer', 'runtime': 'codex', 'sessionStatus': 'exited',
                  'lifecycleState': 'attention_required', 'agentActivity': {}, 'canonicalSessionName': 'review-overseer@t'}]
        with mock.patch.object(self.menu, 'seats', return_value=seats), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.team_menu, '2', '3', 'y', '4', 'y', team='t')
        self.assertIn('control.lead · claude-code · waiting on you\n', output)
        flagged = {'sessionStatus': 'running', 'lifecycleState': 'attention_required', 'agentActivity': {'state': 'running'}}
        self.assertEqual(self.menu.seat_state(flagged), 'working · OpenRig asks you to look')
        self.assertIn('review.overseer · codex · stopped\n', output)
        runs = self.runs(output)
        self.assertEqual(runs[0], 'tmux attach -t control-lead@t')
        self.assertTrue(runs[1].endswith('bin/rig launch R1 review.overseer'))
        self.assertTrue(runs[2].endswith('bin/rig down R1'))

    def test_herdr_view_replaces_only_this_teams_views(self):
        listing = {'result': {'workspaces': [
            {'workspace_id': 'w1', 'label': 'openrig:rig:t#l1'}, {'workspace_id': 'w2', 'label': 'openrig:pod:t/intake#l2'},
            {'workspace_id': 'w3', 'label': 'openrig:rig:t-two#l3'}, {'workspace_id': 'w4', 'label': '~'}]}}
        with mock.patch.object(self.menu, 'read_json', return_value=listing), \
                mock.patch.object(self.menu.shutil, 'which', return_value='/bin/herdr'), \
                mock.patch.dict(os.environ, {'HERDR_ENV': '1', 'HERDR_WORKSPACE_ID': 'w2'}):
            runs = self.runs(self.drive(self.menu.herdr_view, team='t'))
        self.assertEqual(runs[:1], ['herdr workspace close w1'])  # w2 holds this menu
        self.assertTrue(runs[1].endswith('bin/rig terminal open t'))
        self.assertNotIn('herdr', runs)  # inside herdr it focuses, never nests

    def test_loop_dispatches_seats_only_into_a_running_team(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]):
            refused = self.drive(self.menu.loop_menu, '5', project=self.project)
        self.assertIn('Start iztac-research-agent first', refused)
        self.assertEqual(self.runs(refused), [])
        with mock.patch.object(self.menu, 'rigs', return_value=[{'name': 'iztac-research-agent'}]):
            output = self.drive(self.menu.loop_menu, '5', '1', project=self.project)
        runs = self.runs(output)
        self.assertTrue(runs[0].endswith('bin/ai-work loop owner-repo-1 go LOOP_SEAT_RIG=iztac-research-agent'))
        self.assertTrue(runs[1].endswith('bin/ai-work loop owner-repo-1 status'))
        self.assertIn('dev-loop fold owner/repo <issue>', output)

    def test_choosing_filters_and_refuses_numbers_that_are_not_shown(self):
        items = [('alpha', 'a'), ('beta', 'b'), ('alphabet', 'c')]
        picked = {}
        output = self.drive(lambda: picked.setdefault('value', self.menu.choose('T', items)), 'alph', '3', '2')
        self.assertIn('There is no 3 here.', output)
        self.assertEqual(picked['value'], 'c')

    def test_only_the_default_anthropic_url_is_dropped(self):
        with mock.patch.dict(os.environ, {'ANTHROPIC_BASE_URL': 'https://api.anthropic.com', 'CLAUDECODE': '1'}):
            self.menu.clean_environment()
            self.assertNotIn('ANTHROPIC_BASE_URL', os.environ)
            self.assertNotIn('CLAUDECODE', os.environ)
        with mock.patch.dict(os.environ, {'ANTHROPIC_BASE_URL': 'http://127.0.0.1:1'}):
            self.menu.clean_environment()
            self.assertEqual(os.environ['ANTHROPIC_BASE_URL'], 'http://127.0.0.1:1')


if __name__ == '__main__':
    unittest.main()
