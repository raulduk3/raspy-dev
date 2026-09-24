"""Real Git/check fixtures, no user config, network, AI workers, or external writes."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CHECK = PLATFORM / 'hooks/check-once.sh'
LOOP = PLATFORM / 'skills/loop/scripts/loop.sh'
GUARD = PLATFORM / 'hooks/pre-tool-use-guard.sh'
GHX = PLATFORM / 'skills/loop/scripts/ghx'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='platform-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = self.base / 'config'
        self.config.mkdir()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.fakebin = self.base / 'fakebin'
        self.fakebin.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        DEV_PLATFORM_REPOS=str(self.config / 'repos.conf'),
                        DEV_PLATFORM_BRIEF=str(self.config / 'absent.conf'),
                        DEV_PLATFORM_PERSONAL=str(self.config / 'personal.conf'),
                        DEV_PLATFORM_ENV_DIR=str(self.config / 'env.d'),
                        LOOP_STATE_DIR=str(self.base / 'state'),
                        GH_CALLS=str(self.base / 'gh.calls'))
        (self.config / 'personal.conf').write_text('')
        self.env['PATH'] = str(self.fakebin) + os.pathsep + self.env['PATH']
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.run_cmd('git', 'init', '-q', '-b', 'main', cwd=self.repo)
        (self.repo / 'source').write_text('initial\n')
        (self.repo / 'bin').mkdir()
        self.write_check('echo checked >> "$(git rev-parse --path-format=absolute --git-path calls)"\n')
        self.commit()
        self.configure()

    def run_cmd(self, *args, cwd=None, expected=0, input=None, env=None):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.repo,
                                env=env or self.env, input=input, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=25)
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def commit(self):
        self.run_cmd('git', 'add', '.')
        self.run_cmd('git', 'commit', '-qm', 'test: fixture')

    def write_check(self, body):
        check = self.repo / 'bin/check'
        check.write_text('#!/usr/bin/env bash\nset -eu\n' + body)
        check.chmod(0o755)

    def configure(self, base='main', personal=False, identity='owner', path=None):
        (self.config / 'repos.conf').write_text(f'test/repo\t{path or self.repo}\t{identity}\t{base}\n')
        (self.config / 'personal.conf').write_text(str(self.repo) + '\n' if personal else '')

    def calls(self, cwd=None):
        gitdir = self.run_cmd('git', 'rev-parse', '--path-format=absolute', '--git-path', 'calls', cwd=cwd).stdout.strip()
        p = Path(gitdir)
        return len(p.read_text().splitlines()) if p.exists() else 0

    def check(self, *args, **kwargs):
        return self.run_cmd('bash', CHECK, *args, **kwargs)

    def setup_remote(self):
        remote = self.base / 'remote.git'
        self.run_cmd('git', 'clone', '--bare', '-q', self.repo, remote)
        self.run_cmd('git', 'remote', 'add', 'origin', remote)
        self.run_cmd('git', 'fetch', '-q', 'origin')
        self.run_cmd('git', 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        gh = self.fakebin / 'gh'
        gh.write_text('''#!/usr/bin/env python3
import os,sys
with open(os.environ['GH_CALLS'], 'a') as f: f.write(' '.join(sys.argv[1:])+'\\n')
if sys.argv[1:3] in (['issue','list'], ['pr','list']): print('[]')
else: sys.exit('external operation refused by fixture')
''')
        gh.chmod(0o755)
        claude = self.fakebin / 'claude'
        claude.write_text('#!/bin/sh\necho UNEXPECTED_WORKER >&2\nexit 99\n')
        claude.chmod(0o755)

    def loop(self, *args, **kwargs):
        return self.run_cmd('bash', LOOP, args[0], 'test/repo', *args[1:], **kwargs)

    def ctl(self):
        return self.base / 'state/test__repo'


class CheckTests(Fixture):
    def test_artifacts_ignored_source_and_untracked_invalidated(self):
        self.check('--status', expected=1)
        self.assertEqual(self.calls(), 0)
        self.check()
        (self.repo / '.worker-pr.md').write_text('after check')
        (self.repo / 'notes').mkdir()
        (self.repo / 'notes/.worker-report.md').write_text('nested artifact')
        self.check('--status')
        self.check()
        self.assertEqual(self.calls(), 1)
        (self.repo / 'source').write_text('edited\n')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 2)
        (self.repo / 'new file\nwith newline').write_text('untracked source')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 3)
        (self.repo / 'new file\nwith newline').write_text('changed again')
        self.check('--status', expected=1)

    def test_index_changes_even_when_worktree_reverted(self):
        self.check()
        (self.repo / 'source').write_text('staged\n')
        self.run_cmd('git', 'add', 'source')
        (self.repo / 'source').write_text('initial\n')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 2)

    def test_tracked_artifacts_not_ignored(self):
        (self.repo / '.worker-source').write_text('tracked')
        self.commit()
        self.check()
        (self.repo / '.worker-source').write_text('changed')
        self.check('--status', expected=1)

    def test_failure_never_caches(self):
        self.write_check('exit 7\n')
        self.check(expected=1)
        self.check('--status', expected=1)
        self.write_check('echo passing\n')
        self.check()
        self.check('--status')

    def test_changed_during_check_is_not_blessed(self):
        self.write_check("printf 'changed during check\\n' >> source\n")
        result = self.check(expected=1)
        self.assertIn('changed during check', result.stdout)
        self.check('--status', expected=1)

    def test_missing_check_fails_closed(self):
        (self.repo / 'bin/check').unlink()
        (self.repo / 'package.json').write_text('{"description":"check"}')
        self.check(expected=2)
        self.check('--status', expected=2)

    def test_env_key_main_and_linked_worktree(self):
        envdir = self.config / 'env.d'
        envdir.mkdir()
        (envdir / 'repo.sh').write_text('export EXPECTED_VALUE=shared\n')
        self.write_check('[ "${EXPECTED_VALUE:-}" = shared ]\necho checked >> "$(git rev-parse --path-format=absolute --git-path calls)"\n')
        self.commit()
        self.check()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        self.check('--status', cwd=linked, expected=1)
        self.check(cwd=linked)
        self.assertEqual(self.calls(linked), 1)
        self.assertEqual(self.calls(), 1)
        (envdir / 'repo.sh').write_text('export EXPECTED_VALUE=changed\n')
        self.check('--status', expected=1)
        self.check('--status', cwd=linked, expected=1)
        self.check(cwd=linked, expected=1)

    def test_dirty_submodule_fails_closed(self):
        sub = self.base / 'sub-source'
        self.run_cmd('git', 'clone', '-q', '--local', self.repo, sub)
        self.run_cmd('git', '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(sub), 'module')
        self.commit()
        self.check()
        (self.repo / 'module/source').write_text('dirty module')
        result = self.check('--status', expected=1)
        self.assertIn('dirty submodule cannot be cached', result.stdout)
        self.check(expected=1)

    def test_pinned_bun_selected_after_env(self):
        (self.repo / 'bin/check').unlink()
        (self.repo / 'package.json').write_text('{"scripts":{"check":"fixture"}}')
        bun = self.base / 'pinned-bun'
        bun.write_text('#!/bin/sh\n[ "$1 $2" = "run check" ]\n')
        bun.chmod(0o755)
        envdir = self.config / 'env.d'; envdir.mkdir()
        (envdir / 'repo.sh').write_text(f'BUN_PATH="{bun}"\n')
        self.check()

    def test_existing_lock_does_not_run_check(self):
        lock = self.repo / '.git/dev-platform/check-lock'
        lock.mkdir(parents=True)
        self.check(expected=3)
        self.assertEqual(self.calls(), 0)


class LoopTests(Fixture):
    def test_main_base_start_and_pinning(self):
        self.setup_remote()
        self.loop('start')
        ctl = self.ctl()
        self.assertEqual((ctl / 'day-base').read_text().strip(), 'main')
        day = (ctl / 'day-branch').read_text().strip()
        self.assertEqual(self.run_cmd('git', 'rev-parse', day).stdout,
                         self.run_cmd('git', 'rev-parse', 'origin/main').stdout)
        self.configure(base='develop')
        self.assertIn('origin/main', self.loop('status').stdout)
        self.loop('start', expected=3)

    def test_explicit_stacked_base(self):
        self.run_cmd('git', 'branch', 'fix/bootstrap')
        self.setup_remote()
        self.configure(base='fix/bootstrap', personal=True)
        self.loop('start')
        self.assertEqual((self.ctl() / 'day-base').read_text().strip(), 'fix/bootstrap')

    def test_personal_remote_default_main(self):
        self.setup_remote()
        self.configure(base='', personal=True)
        self.loop('start')
        self.assertEqual((self.ctl() / 'day-base').read_text().strip(), 'main')

    def test_personal_symlink_default_main(self):
        self.setup_remote()
        alias = self.base / 'repo-alias'
        alias.symlink_to(self.repo, target_is_directory=True)
        self.configure(base='', path=alias)
        (self.config / 'personal.conf').write_text(str(alias) + '\n')
        self.loop('start')
        self.assertEqual((self.ctl() / 'day-base').read_text().strip(), 'main')

    def test_personal_linked_alias_default_main(self):
        self.setup_remote()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        alias = self.base / 'linked-alias'
        alias.symlink_to(linked, target_is_directory=True)
        self.configure(base='', path=alias)
        (self.config / 'personal.conf').write_text(str(alias) + '\n')
        self.loop('start')
        self.assertEqual((self.ctl() / 'day-base').read_text().strip(), 'main')

    def test_professional_stays_develop_even_if_default_main(self):
        self.run_cmd('git', 'branch', 'develop')
        self.setup_remote()
        self.configure(base='', personal=False)
        self.loop('start')
        self.assertEqual((self.ctl() / 'day-base').read_text().strip(), 'develop')

    def test_mapping_accepts_linked_worktree(self):
        self.setup_remote()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        self.configure(path=linked)
        self.loop('status')

    def test_owner_gates_no_bypass_or_network(self):
        self.setup_remote()
        env = dict(self.env, LOOP_AGENT_ACTS='1')
        for personal in (False, True):
            self.configure(personal=personal)
            for args in [('fold', '1'), ('finish', '1'), ('tidy', '--apply')]:
                with self.subTest(personal=personal, args=args):
                    self.loop(*args, env=env, expected=4)
        self.assertFalse(Path(self.env['GH_CALLS']).exists())

    def test_close_ready_and_professional_push_gated(self):
        self.setup_remote(); self.loop('start')
        self.loop('close', '--push', expected=4)
        self.configure(personal=True)
        self.loop('close', '--ready', expected=4)
        self.loop('close', '--push', '--ready', expected=4)

    def test_only_does_not_override_plan(self):
        self.setup_remote(); self.loop('start')
        result = self.loop('go', 'only', '999')
        self.assertIn('nothing to dispatch', result.stdout)
        self.assertEqual(list(self.repo.glob('.claude/worktrees/loop-*')), [])

    def test_invalid_limits_and_base_refused(self):
        for limit in ('0', '-1', 'bogus'):
            self.loop('status', env=dict(self.env, LOOP_CAP=limit), expected=2)
        self.configure(base='--bad')
        self.loop('status', expected=2)

    def test_resume_respects_cap_without_launch(self):
        self.setup_remote(); self.loop('start')
        day = (self.ctl() / 'day-branch').read_text().strip().split('/', 1)[1]
        (self.ctl() / day / 'workers/1.pid').write_text(str(os.getpid()))
        result = self.loop('resume', '2', env=dict(self.env, LOOP_CAP='1'))
        self.assertIn('cap reached', result.stdout)

    def test_close_uses_base_and_accurate_verification(self):
        self.setup_remote(); self.loop('start')
        ctl = self.ctl(); day = (ctl / 'day-branch').read_text().strip().split('/', 1)[1]
        out = ctl / day
        (out / 'folded.tsv').write_text('1\tfix/example\t123\tnow\n')
        (out / 'folded-1.md').write_text('## What changed and why\n\nFixture.\n\n## Verification\n\nFixture check.\n\n## Deploy and provider impact\n\nNone.\n\n## Review notes\n\nReview locally.\n')
        result = self.loop('close')
        self.assertIn('--base "main"', result.stdout)
        body = (out / 'pr.md').read_text()
        self.assertIn('integrated head passed', body)
        self.assertNotIn('bun run check', body)
        self.assertNotIn('every merge', body)
        self.loop('close', '--as', 'main', expected=2)
        (out / 'folded-1.md').write_text('## What changed and why\n\nGenerated with Codex\n')
        self.loop('close', expected=1)


class GuardTests(Fixture):
    def guard(self, command, expected):
        return self.run_cmd('bash', GUARD, input=json.dumps({'cwd': str(self.repo),
                            'tool_input': {'command': command}}), expected=expected)

    def test_hard_refusals_everywhere(self):
        for personal in (False, True):
            self.configure(personal=personal)
            for command in ('git push origin main', 'git push origin develop',
                            'git push --force origin fix/example', 'git push',
                            'git -C /tmp push origin main', 'git -c foo=bar rebase main',
                            'git commit --amend', 'git reset --hard',
                            'git checkout develop && git merge fix/example',
                            'gh pr merge 1', 'gh pr ready 1', 'gh pr review 1 --approve',
                            'docker compose restart', 'ssh root@host uptime'):
                with self.subTest(personal=personal, command=command):
                    self.guard(command, 2)
            self.guard('git status', 0)
            self.guard('git push -u origin fix/example', 0)

    def test_ghost_attribution_professional_only(self):
        command = 'git commit -m "Generated with Codex"'
        self.guard(command, 2)
        self.configure(personal=True)
        self.guard(command, 0)

    def test_ghx_owner_actions_refused_for_both_identities(self):
        self.setup_remote()
        for identity in ('owner', 'bot'):
            self.configure(identity=identity)
            for args in [('pr', 'merge', '1'), ('pr', 'ready', '1'),
                         ('pr', 'review', '1', '--approve'), ('api', 'repos/test/repo'),
                         ('pr', 'list', '--repo', 'other/repo')]:
                self.run_cmd('bash', GHX, 'test/repo', *args, expected=3)
        self.assertFalse(Path(self.env['GH_CALLS']).exists())

    def test_ghx_professional_bot_refused_before_credentials(self):
        self.configure(identity='bot')
        self.run_cmd('bash', GHX, 'test/repo', 'pr', 'list', expected=3)


class PersonalIdentityTests(Fixture):
    def setUp(self):
        super().setUp()
        self.linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', self.linked)
        self.alias = self.base / 'repo-alias'
        self.alias.symlink_to(self.repo, target_is_directory=True)
        self.linked_alias = self.base / 'linked-alias'
        self.linked_alias.symlink_to(self.linked, target_is_directory=True)
        # Credential access always stops at a local fixture; no secret is read.
        self.op_calls = self.base / 'op.calls'
        self.env['OP_CALLS'] = str(self.op_calls)
        op = self.fakebin / 'op'
        op.write_text('#!/bin/sh\necho called >> "$OP_CALLS"\nexit 1\n')
        op.chmod(0o755)

    def assert_identity(self, checkout, entry, personal):
        self.configure(base='', identity='bot', path=checkout)
        (self.config / 'personal.conf').write_text(str(entry) + '\n')
        command = 'git commit -m "Generated with Codex"'
        self.run_cmd('bash', GUARD, input=json.dumps({'cwd': str(checkout),
                     'tool_input': {'command': command}}), expected=0 if personal else 2)
        self.run_cmd('bash', GHX, 'test/repo', 'pr', 'list', expected=4 if personal else 3)
        self.assertEqual(self.op_calls.exists(), personal)
        if self.op_calls.exists():
            self.op_calls.unlink()

    def test_main_linked_and_symlink_entries_share_exact_identity(self):
        paths = (self.repo.resolve(), self.alias, self.linked.resolve(), self.linked_alias)
        for checkout in paths:
            for entry in paths:
                with self.subTest(checkout=checkout, entry=entry):
                    self.assert_identity(checkout, entry, True)

    def test_siblings_nested_repos_and_nonrepos_stay_professional(self):
        sibling = self.base / 'repo-other'
        nested = self.repo / 'nested-professional'
        for checkout in (sibling, nested):
            self.run_cmd('git', 'init', '-q', '-b', 'main', checkout)
            with self.subTest(checkout=checkout):
                self.assert_identity(checkout, self.alias, False)
                self.assert_identity(checkout, self.repo.resolve(), False)
        for entry in (self.base, self.base / 'missing'):
            with self.subTest(entry=entry):
                self.assert_identity(self.repo, entry, False)


class WorkerBoundTests(Fixture):
    def wait_for_file(self, path, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.02)
        self.fail(f'timed out waiting for {path}')

    def detached_supervisor(self, timed_out):
        self.setup_remote()
        self.loop('start')
        day = (self.ctl() / 'day-branch').read_text().strip().split('/', 1)[1]
        workers = self.ctl() / day / 'workers'
        wt = self.repo / '.claude/worktrees/loop-1-fixture'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'fix/fixture', wt)
        (wt / '.worker-brief.md').write_text('Harmless lifecycle fixture only.\n')
        gh = self.fakebin / 'gh'
        gh.write_text('#!/bin/sh\nprintf \'%s\\n\' \'{"labels":[],"body":"Scope: source"}\'\n')
        claude = self.fakebin / 'claude'
        claude.write_text('''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
assert sys.stdin.read() == ''
assert 'DO_NOT_INHERIT' not in os.environ
assert os.environ['SAFE_FIXTURE'] == 'yes'
Path('child.started').write_text(json.dumps({'pid': os.getpid(), 'parent': os.getppid()}))
print('fixture stdout', flush=True)
print('fixture stderr', file=sys.stderr, flush=True)
while not Path('child.release').exists(): time.sleep(0.02)
sys.exit(7)
''')
        env = dict(self.env, LOOP_WORKER_MAX_SECONDS='3' if timed_out else '10',
                   DO_NOT_INHERIT='fixture', SAFE_FIXTURE='yes', DEV_PLATFORM_ENV_PASS='SAFE_FIXTURE')
        ready = self.base / 'launcher.ready'
        # Keep a short-lived outer shell in its own group, then emulate tool cleanup.
        launcher = subprocess.Popen(
            ['bash', '-c', 'bash "$1" resume test/repo 1 && touch "$2"; exec sleep 20',
             'fixture-launcher', str(LOOP), str(ready)], cwd=self.repo, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        supervisor = child = None
        try:
            self.wait_for_file(ready)
            self.wait_for_file(wt / 'child.started')
            metadata = json.loads((wt / 'child.started').read_text())
            child = metadata['pid']
            supervisor = int((workers / '1.pid').read_text())
            self.assertEqual(supervisor, metadata['parent'], 'PID must name the actual supervisor')
            os.killpg(launcher.pid, signal.SIGTERM)
            launcher.wait(timeout=3)
            time.sleep(0.1)
            os.kill(supervisor, 0)
            os.kill(child, 0)
            self.assertFalse((workers / '1.exit').exists(), 'supervisor must wait for its child')
            self.assertEqual(os.getpgid(supervisor), supervisor, 'supervisor must detach from launcher')
            if not timed_out:
                (wt / 'child.release').touch()
            self.wait_for_file(workers / '1.exit')
            result = json.loads((workers / '1.exit').read_text())
            self.assertEqual(result['exit_code'], 124 if timed_out else 7)
            self.assertEqual(result['reason'], 'wall_time_limit' if timed_out else 'exited')
            if timed_out:
                self.assertLess(result['elapsed_seconds'], 8)
            log = (workers / '1.log').read_text()
            self.assertIn('fixture stdout', log)
            self.assertIn('fixture stderr', log)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            # Only fixture process groups. Never touch real loop state or workers.
            for pid in (launcher.pid, supervisor, child):
                if pid is not None:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            launcher.wait(timeout=3)

    def test_supervisor_survives_launcher_group_cleanup_and_reports_exit(self):
        self.detached_supervisor(timed_out=False)

    def test_supervisor_survives_launcher_group_cleanup_and_bounds_worker(self):
        self.detached_supervisor(timed_out=True)

    def test_supervisor_sanitizes_environment_and_reports_exit(self):
        result = self.base / 'worker.exit'
        env = dict(self.env, DO_NOT_INHERIT='fixture', SAFE_FIXTURE='yes', DEV_PLATFORM_ENV_PASS='SAFE_FIXTURE')
        command = "import os; assert 'DO_NOT_INHERIT' not in os.environ; assert os.environ['SAFE_FIXTURE']=='yes'"
        self.run_cmd(sys.executable, PLATFORM / 'skills/loop/scripts/worker-run.py',
                     '5', result, '--', sys.executable, '-c', command, env=env)
        self.assertEqual(json.loads(result.read_text())['exit_code'], 0)

    def test_supervisor_times_out_harmless_process(self):
        result = self.base / 'worker.exit'
        self.run_cmd(sys.executable, PLATFORM / 'skills/loop/scripts/worker-run.py',
                     '1', result, '--', sys.executable, '-c', 'import time; time.sleep(20)', expected=124)
        self.assertEqual(json.loads(result.read_text())['reason'], 'wall_time_limit')
