"""The ai menu: scripted answers in, the exact hand-off command out. Nothing is launched."""
from contextlib import redirect_stdout
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import tty
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

    def test_a_team_follows_its_repository_when_the_checkout_is_renamed(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            self.drive(self.menu.project_team, 'y', '', project=self.project)
        self.assertEqual((self.root / 'engagements/research-agent/project').read_text(), 'owner/repo\n')
        renamed = dict(self.project, root=str(self.root / 'renamed-checkout'))
        with mock.patch.object(self.menu, 'catalog', return_value=[renamed]):
            self.assertEqual(self.menu.team_for(renamed), 'iztac-research-agent')
            self.assertEqual(self.menu.team_project('iztac-research-agent'), renamed)
        other = dict(self.project, repo='owner/other', root=str(self.root / 'other'))
        self.assertEqual(self.menu.team_for(other), 'iztac-other')

    def test_a_team_defined_in_its_engagement_folder_is_started_from_that_folder(self):
        folder = self.root / 'engagements/research-agent'
        folder.mkdir(parents=True)
        (folder / 'project').write_text('owner/repo\n')
        (folder / 'rig.yaml').write_text('name: iztac-research-agent\n')
        # The checkout was renamed; the team still starts from its own engagement folder.
        renamed = dict(self.project, root=str(self.root / 'renamed-checkout'))
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            output = self.drive(self.menu.project_team, 'y', '', project=renamed)
        self.assertIn(f"opens the team defined in {folder / 'rig.yaml'}", output)
        self.assertNotIn('Codex overseer', output)
        self.assertTrue(self.runs(output)[0].endswith(
            f'bin/dev-workspace start iztac --cwd {folder} --rig iztac-research-agent'))

    def test_team_seats_attach_relaunch_and_stop(self):
        seats = [{'rigId': 'R1', 'logicalId': 'control.lead', 'runtime': 'claude-code', 'sessionStatus': 'running',
                  'lifecycleState': 'attention_required',
                  'agentActivity': {'state': 'needs_input', 'reason': 'selection_prompt'},
                  'canonicalSessionName': 'control-lead@t'},
                 {'rigId': 'R1', 'logicalId': 'review.overseer', 'runtime': 'codex', 'sessionStatus': 'exited',
                  'lifecycleState': 'attention_required', 'agentActivity': {}, 'canonicalSessionName': 'review-overseer@t'}]
        with mock.patch.object(self.menu, 'seats', return_value=seats), mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(self.menu, 'herdr', return_value=None):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.team_menu, '2', '3', 'y', '4', 'y', team='t')
        self.assertIn('control.lead · claude-code · waiting on you\n', output)
        flagged = {'sessionStatus': 'running', 'lifecycleState': 'attention_required', 'agentActivity': {'state': 'running'}}
        self.assertEqual(self.menu.seat_state(flagged), 'working · OpenRig asks you to look')
        self.assertIn('review.overseer · codex · stopped\n', output)
        runs = self.runs(output)
        self.assertEqual(runs[0], 'tmux attach -t control-lead@t')
        self.assertTrue(runs[1].endswith('bin/rig snapshot R1'))
        self.assertTrue(runs[2].endswith('bin/rig launch R1 review.overseer'))
        self.assertTrue(runs[3].endswith('bin/rig down R1'))

    class FakeHerdr:
        """Answers herdr socket requests from a small in-memory state and records them."""
        def __init__(self, workspaces=(), tabs=(), panes=()):
            self.workspaces, self.tabs, self.panes, self.calls = list(workspaces), list(tabs), list(panes), []

        def __call__(self, method, **params):
            self.calls.append((method, params))
            ws = params.get('workspace_id')
            if method == 'workspace.list':
                return {'workspaces': self.workspaces}
            if method == 'workspace.create':
                space = {'workspace_id': 'wNEW', 'label': params['label']}
                self.workspaces.append(space)
                self.tabs.append({'tab_id': 'wNEW:t1', 'workspace_id': 'wNEW', 'label': '1'})
                return {'workspace': space}
            if method == 'tab.list':
                return {'tabs': [t for t in self.tabs if t['workspace_id'] == ws]}
            if method == 'pane.list':
                return {'panes': [p for p in self.panes if p['workspace_id'] == ws]}
            if method == 'layout.apply':
                tab = f"{ws}:{params['tab_label']}"
                self.tabs.append({'tab_id': tab, 'workspace_id': ws, 'label': params['tab_label']})
                def leaves(node):
                    return [node] if node['type'] == 'pane' else leaves(node['first']) + leaves(node['second'])
                for leaf in leaves(params['root']):
                    self.panes.append({'pane_id': f"{tab}:{leaf['label']}", 'tab_id': tab, 'workspace_id': ws,
                                       'label': leaf['label']})
            return {}

        def methods(self):
            return [m for m, _ in self.calls if m not in ('workspace.list', 'tab.list', 'pane.list')]

    def seat(self, logical, status='running'):
        return {'logicalId': logical, 'sessionStatus': status, 'agentActivity': {},
                'canonicalSessionName': logical.replace('.', '-') + '@t'}

    def show(self, fake, agent=None, here='wHERE'):
        seats = [self.seat('control.lead'), self.seat('review.overseer'), self.seat('workers.issue-4'),
                 self.seat('workers.issue-5', 'exited')]
        with mock.patch.object(self.menu, 'herdr', fake), \
                mock.patch.dict(os.environ, {'HERDR_ENV': '1', 'HERDR_WORKSPACE_ID': here}):
            with redirect_stdout(io.StringIO()):
                return self.menu.show_in_herdr('t', seats, Path('/p/project'), agent)

    def test_a_new_team_space_holds_rig_tui_and_every_running_agent_in_one_tab(self):
        fake = self.FakeHerdr(workspaces=[{'workspace_id': 'wOLD', 'label': 'openrig:pod:t/control#l2'}])
        self.assertTrue(self.show(fake, agent='review-overseer@t'))
        self.assertEqual(fake.methods(), ['workspace.close', 'workspace.create', 'layout.apply', 'tab.close',
                                          'tab.focus', 'pane.zoom', 'workspace.focus'])
        created = next(p for m, p in fake.calls if m == 'workspace.create')
        self.assertEqual(created, {'label': 't', 'cwd': '/p/project', 'focus': False})
        applied = next(p for m, p in fake.calls if m == 'layout.apply')
        self.assertEqual(applied['tab_label'], 'team')
        tui, agents = applied['root']['first'], applied['root']['second']
        self.assertEqual((tui['label'], tui['cwd'], tui['env']), ('rig tui', '/p/project', {'OPENRIG_REDUCED_MOTION': '1'}))
        self.assertEqual(tui['command'][:2], ['sh', '-c'])
        self.assertIn('bin/rig tui; printf', tui['command'][2])  # quitting it leaves the pane, offering it again

        def leaves(node):
            return [node] if node['type'] == 'pane' else leaves(node['first']) + leaves(node['second'])
        self.assertEqual([(l['label'], l['command']) for l in leaves(agents)], [
            ('control-lead@t', ['tmux', 'attach', '-t', 'control-lead@t']),
            ('review-overseer@t', ['tmux', 'attach', '-t', 'review-overseer@t']),
            ('workers-issue-4@t', ['tmux', 'attach', '-t', 'workers-issue-4@t'])])  # the stopped issue-5 has no tile
        self.assertIn(('tab.close', {'tab_id': 'wNEW:t1'}), fake.calls)
        self.assertIn(('pane.zoom', {'pane_id': 'wNEW:team:review-overseer@t', 'mode': 'on'}), fake.calls)

    def complete_space(self, labels):
        return self.FakeHerdr(
            workspaces=[{'workspace_id': 'w1', 'label': 't'}, {'workspace_id': 'wHERE', 'label': 'openrig:rig:t#l1'}],
            tabs=[{'tab_id': 'w1:team', 'workspace_id': 'w1', 'label': 'team'}],
            panes=[{'pane_id': f'w1:{l}', 'tab_id': 'w1:team', 'workspace_id': 'w1', 'label': l} for l in labels])

    def test_a_complete_space_is_reused_untouched(self):
        fake = self.complete_space(['rig tui', 'control-lead@t', 'review-overseer@t', 'workers-issue-4@t'])
        self.assertTrue(self.show(fake))
        self.assertEqual(fake.methods(), ['tab.focus', 'pane.zoom', 'workspace.focus'])  # the menu's own view stays

    def test_a_space_missing_an_agent_or_from_an_older_layout_is_rebuilt(self):
        for fake in (self.complete_space(['rig tui', 'control-lead@t', 'review-overseer@t']),
                     self.FakeHerdr(workspaces=[{'workspace_id': 'w1', 'label': 't'}],
                                    tabs=[{'tab_id': 'w1:s', 'workspace_id': 'w1', 'label': 'shell'}])):
            self.assertTrue(self.show(fake))
            self.assertEqual(fake.methods()[:3], ['workspace.close', 'workspace.create', 'layout.apply'])
            self.assertIn(('workspace.close', {'workspace_id': 'w1'}), fake.calls)

    def test_an_agent_ended_inside_its_tile_is_stopped_and_relaunched_cleanly(self):
        self.menu.DRY = False
        seat = dict(self.seat('review.overseer'), rigId='R1')
        def answer(argv, **kwargs):
            if argv[:2] == ['tmux', 'display']:
                return mock.Mock(returncode=0, stdout='3272 /dev/ttys012\n')
            if argv[0] == 'ps':  # only the pane's own shell is in the foreground
                return mock.Mock(returncode=0, stdout=' 3272 Ss+\n 3300 S\n')
            return mock.Mock(returncode=0, stdout='')
        with mock.patch.object(self.menu.subprocess, 'run', side_effect=answer) as ran, \
                mock.patch.object(self.menu.shutil, 'which', return_value='/bin/tmux'), \
                mock.patch.object(self.menu, 'run') as handed:
            self.assertEqual(self.menu.seat_state(seat), 'stopped, left at a shell')
            self.menu.relaunch('R1', seat)
        self.assertIn(mock.call(['tmux', 'kill-session', '-t', 'review-overseer@t'], capture_output=True), ran.call_args_list)
        self.assertEqual([c.args[0][-3:] for c in handed.call_args_list],
                         [[str(self.menu.ROOT / 'bin/rig'), 'snapshot', 'R1'], ['launch', 'R1', 'review.overseer']])

    def test_an_agent_under_a_wrapper_script_is_not_mistaken_for_a_bare_shell(self):
        self.menu.DRY = False
        seat = self.seat('review.overseer')

        def answer(argv, **kwargs):
            if argv[:2] == ['tmux', 'display']:
                return mock.Mock(returncode=0, stdout='3272 /dev/ttys012\n')
            return mock.Mock(returncode=0, stdout=' 3272 Ss\n 3301 S+\n 3302 S+\n')  # the agent holds the terminal
        with mock.patch.object(self.menu.subprocess, 'run', side_effect=answer), \
                mock.patch.object(self.menu.shutil, 'which', return_value='/bin/tmux'):
            self.assertFalse(self.menu.exited_to_shell(seat))
            self.assertEqual(self.menu.seat_state(seat), 'running')

    def test_without_herdr_an_agent_opens_directly_in_tmux(self):
        seats = [self.seat('control.lead')]
        with mock.patch.object(self.menu, 'herdr', return_value=None), \
                mock.patch.object(self.menu, 'seats', return_value=[dict(seats[0], rigId='R1')]):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.team_menu, '2', team='t')
        self.assertIn('RUN tmux attach -t control-lead@t', output)

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

    def test_iztac_is_on_the_home_screen_and_asks_for_a_project_first(self):
        other = dict(self.project, id='elsewhere', source='discovered', root='/x/other')
        with mock.patch.object(self.menu, 'catalog', return_value=[self.project, other]), \
                mock.patch.object(self.menu, 'role_menu') as role:
            output = self.drive(self.menu.iztac_menu, '1')
        self.assertNotIn('other', output)
        role.assert_called_once_with('iztac', self.project)

    def test_a_menu_left_open_across_an_update_restarts_into_the_new_release(self):
        self.menu.DRY = False
        release = self.root / 'releases/new'
        (release / 'bin').mkdir(parents=True)
        (release / 'bin/ai').write_text('')
        (self.root / 'current').symlink_to(release)
        with mock.patch.object(self.menu, 'CURRENT', self.root / 'current'), \
                mock.patch.object(self.menu.os, 'execv') as execv:
            self.menu.upgrade_if_released()
        execv.assert_called_once_with(self.menu.sys.executable, [self.menu.sys.executable, str(release.resolve() / 'bin/ai')])
        with mock.patch.object(self.menu, 'CURRENT', self.root / 'current'), \
                mock.patch.object(self.menu, 'ROOT', release.resolve()), mock.patch.object(self.menu.os, 'execv') as execv:
            self.menu.upgrade_if_released()
        execv.assert_not_called()

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


    def test_fast_arrow_presses_are_read_one_at_a_time(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        tty.setcbreak(slave)  # key-at-a-time input, as while the menu is waiting for a key
        os.write(master, b'\x1b[B\x1b[B\x1bOAx\x7f\r')
        with mock.patch.object(self.menu.sys, 'stdin', mock.Mock(fileno=lambda: slave)):
            keys = [self.menu.read_key() for _ in range(6)]
        self.assertEqual(keys, ['down', 'down', 'up', 'x', 'backspace', 'enter'])
        os.write(master, b'\x1b')
        with mock.patch.object(self.menu.sys, 'stdin', mock.Mock(fileno=lambda: slave)):
            self.assertEqual(self.menu.read_key(), 'esc')

    def test_keyboard_picking_moves_filters_and_backs_out(self):
        items = [('alpha', 'a'), ('beta', 'b'), ('alphabet', 'c')]

        def pick(*keys):
            presses = iter(keys)
            with mock.patch.object(self.menu, 'keyboard', return_value=True), \
                    mock.patch.object(self.menu, 'read_key', lambda: next(presses)), redirect_stdout(io.StringIO()):
                return self.menu.choose('T', items)
        self.assertEqual(pick('down', 'down', 'enter'), 'c')
        self.assertEqual(pick('up', 'enter'), 'c')  # up from the top wraps to the bottom
        self.assertEqual(pick('b', 'enter'), 'b')
        self.assertEqual(pick('a', 'l', 'p', 'h', 'down', 'enter'), 'c')
        self.assertEqual(pick('z', 'esc', 'enter'), 'a')  # Esc clears the filter first
        self.assertIsNone(pick('esc'))
        self.assertIsNone(pick('left'))


if __name__ == '__main__':
    unittest.main()
