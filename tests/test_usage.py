"""Hermetic checks for the unified usage readout: no native probes, no credentials, no clock races."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / 'integrations/claude/usage-collector.py'
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import usage  # noqa: E402


def realistic_payload(extra=None):
    payload = {
        'session_id': 'sess-abc123', 'session_name': 'my-session',
        'transcript_path': '/Users/example/.claude/projects/x/one.jsonl',
        'cwd': '/Users/example/project', 'version': '2.1.280',
        'model': {'id': 'claude-x', 'display_name': 'Claude'},
        'workspace': {'current_dir': '/Users/example/project', 'project_dir': '/Users/example/project'},
        'context_window': {'used_percentage': 12.0},
        'rate_limits': {
            'five_hour': {'used_percentage': 42.3, 'resets_at': 4102444800},
            'seven_day': {'used_percentage': 18.0, 'resets_at': 4102531200},
        },
    }
    if extra:
        payload.update(extra)
    return payload


class Collector(unittest.TestCase):
    """Exercises integrations/claude/usage-collector.py as the real subprocess Claude Code
    would invoke: JSON on stdin, a account-scoped cache under a fake HOME, one status line."""

    def setUp(self):
        # The desktop app sets ANTHROPIC_* / CLAUDECODE*; the collector must not need or trip
        # on them, and the boundary rule requires stripping them here regardless (see
        # tests/test_host_environment.py setUp).
        temp = tempfile.TemporaryDirectory(prefix='usage-collector-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))
                 and k not in ('CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT')}
        clean['HOME'] = str(self.home)
        self.env = clean

    def run_collector(self, stdin_text, account='anthropic-apple'):
        return subprocess.run([sys.executable, str(COLLECTOR), '--account', account],
                              input=stdin_text, env=self.env, text=True,
                              capture_output=True, timeout=15)

    def cache_file(self, account='anthropic-apple'):
        return self.home / '.local/state/dev-platform/usage' / f'{account}.json'

    def test_realistic_payload_writes_cache_and_prints_one_line(self):
        result = self.run_collector(json.dumps(realistic_payload()))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('42', lines[0])
        self.assertIn('18', lines[0])
        cache = self.cache_file()
        self.assertTrue(cache.is_file())
        written = json.loads(cache.read_text())
        self.assertEqual(written['account'], 'anthropic-apple')
        self.assertEqual(written['windows']['five_hour']['used_percentage'], 42.3)
        self.assertEqual(written['windows']['seven_day']['resets_at'], 4102531200)
        self.assertIn('captured_at', written)

    def test_cache_and_directory_permissions_are_owner_only(self):
        self.run_collector(json.dumps(realistic_payload()))
        cache = self.cache_file()
        self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(cache.parent.stat().st_mode), 0o700)

    def test_garbage_input_exits_zero_and_writes_nothing(self):
        result = self.run_collector('not json at all {{{')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertFalse(self.cache_file().exists())
        self.assertFalse(self.cache_file().parent.exists())

    def test_empty_stdin_exits_zero_and_writes_nothing(self):
        result = self.run_collector('')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.cache_file().exists())

    def test_valid_payload_without_rate_limits_does_not_clobber_prior_reading(self):
        first = self.run_collector(json.dumps(realistic_payload()))
        self.assertEqual(first.returncode, 0)
        before = self.cache_file().read_text()
        second = self.run_collector(json.dumps({'session_id': 'x', 'version': '2.1.280'}))
        self.assertEqual(second.returncode, 0)
        self.assertEqual(self.cache_file().read_text(), before)

    def test_no_credential_or_transcript_content_reaches_cache_or_stdout(self):
        poisoned = realistic_payload({
            'api_key': 'sk-ant-NEVER-SHOULD-APPEAR',
            'oauth_token': 'NEVER-SHOULD-APPEAR-TOKEN',
            'transcript_path': '/Users/example/.claude/projects/SECRET-PROJECT/one.jsonl',
            'cwd': '/Users/example/SECRET-PROJECT',
        })
        result = self.run_collector(json.dumps(poisoned))
        cache_text = self.cache_file().read_text()
        for poison in ('sk-ant-NEVER', 'NEVER-SHOULD-APPEAR-TOKEN', 'SECRET-PROJECT', 'session_id', 'transcript_path'):
            self.assertNotIn(poison, cache_text)
            self.assertNotIn(poison, result.stdout)

    def test_missing_account_flag_still_exits_zero_and_writes_no_cache(self):
        result = subprocess.run([sys.executable, str(COLLECTOR)], input=json.dumps(realistic_payload()),
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.home / '.local/state/dev-platform/usage').exists())


def make_codex_observation(account, state, used_percent, resets_at=4102444800):
    quota = [{'limit_id': 'codex', 'primary': {'usedPercent': used_percent, 'windowDurationMins': 10080,
                                               'resetsAt': resets_at}}]
    return dict(account=account, runtime='codex', state=state, observed_at=100, remaining_percent=100 - used_percent,
               quota=quota, reason=None, capabilities={'codex': 'authenticated'})


def make_claude_observation(account, state='quota_unknown', reason='Claude auth status does not expose quota; use native /usage'):
    return dict(account=account, runtime='claude', state=state, observed_at=100, remaining_percent=None,
               quota=None, reason=reason, capabilities={'claude': 'authenticated' if state == 'quota_unknown' else 'unverified'})


class UnifiedView(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='usage-view-')
        self.addCleanup(temp.cleanup)
        self.cache_root = Path(temp.name)
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.data = {'version': 1, 'selected': None, 'bindings': {}}

    def write_cache(self, account, windows, captured_at):
        directory = self.cache_root
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f'{account}.json').write_text(json.dumps({
            'account': account, 'captured_at': captured_at, 'source': 'claude-code-statusline', 'windows': windows,
        }))

    def observe_all(self, rows):
        return lambda data: rows

    def test_missing_cache_renders_as_unknown_never_zero(self):
        rows = [make_codex_observation('openai-apple', 'ready', 10), make_codex_observation('openai-gmail', 'exhausted', 100),
                make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail')]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        claude_rows = [r for r in view['accounts'] if r['client'] == 'Claude Code']
        self.assertEqual(len(claude_rows), 2)
        for row in claude_rows:
            self.assertIsNone(row['windows'])
            self.assertIn('unknown', row['freshness'])
            self.assertEqual(row['source'], 'none')
            # Never a fabricated zero standing in for "we don't know".
            self.assertNotIn('0%', json.dumps(row))

    def test_old_cache_renders_as_stale_with_its_age(self):
        captured = (self.now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.write_cache('anthropic-apple', {'five_hour': {'used_percentage': 55, 'resets_at': 4102444800}}, captured)
        rows = [make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail'),
                make_codex_observation('openai-apple', 'ready', 10), make_codex_observation('openai-gmail', 'exhausted', 100)]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        row = next(r for r in view['accounts'] if r['account'] == 'anthropic-apple')
        self.assertEqual(row['state'], 'stale')
        self.assertIn('stale', row['freshness'])
        self.assertIn('120 minutes old', row['freshness'])
        self.assertEqual(row['windows'][0]['used_percent'], 55)
        # It is genuinely the number that was captured -- not interpolated forward.
        self.assertEqual(row['source'], 'status line cache')

    def test_fresh_cache_renders_as_cached_not_live(self):
        captured = (self.now - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.write_cache('anthropic-apple', {'seven_day': {'used_percentage': 30, 'resets_at': 4102444800}}, captured)
        rows = [make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail'),
                make_codex_observation('openai-apple', 'ready', 10), make_codex_observation('openai-gmail', 'exhausted', 100)]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        row = next(r for r in view['accounts'] if r['account'] == 'anthropic-apple')
        self.assertEqual(row['state'], 'cached')
        self.assertNotEqual(row['state'], 'ready')  # cached is never presented as an eligible-live state
        self.assertIn('5 minutes old', row['freshness'])
        self.assertNotIn('live', row['freshness'])

    def test_window_past_its_reset_is_dropped_not_shown_stale(self):
        captured = (self.now - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        already_reset = int((self.now - timedelta(minutes=1)).timestamp())
        self.write_cache('anthropic-apple', {'five_hour': {'used_percentage': 90, 'resets_at': already_reset}}, captured)
        rows = [make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail'),
                make_codex_observation('openai-apple', 'ready', 10), make_codex_observation('openai-gmail', 'exhausted', 100)]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        row = next(r for r in view['accounts'] if r['account'] == 'anthropic-apple')
        self.assertIsNone(row['windows'])
        self.assertEqual(row['state'], 'quota_unknown')

    def test_unverified_claude_account_shows_no_cached_number_even_if_cache_exists(self):
        captured = self.now.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.write_cache('anthropic-apple', {'five_hour': {'used_percentage': 5, 'resets_at': 4102444800}}, captured)
        rows = [make_claude_observation('anthropic-apple', state='unverified', reason='not bound'),
                make_claude_observation('anthropic-gmail'),
                make_codex_observation('openai-apple', 'ready', 10), make_codex_observation('openai-gmail', 'exhausted', 100)]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        row = next(r for r in view['accounts'] if r['account'] == 'anthropic-apple')
        self.assertEqual(row['state'], 'unverified')
        self.assertIsNone(row['windows'])

    def test_merges_live_codex_row_and_cached_claude_row(self):
        captured = (self.now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.write_cache('anthropic-apple', {'five_hour': {'used_percentage': 12, 'resets_at': 4102444800}}, captured)
        rows = [make_codex_observation('openai-apple', 'ready', 3, resets_at=4102444800),
                make_codex_observation('openai-gmail', 'exhausted', 100),
                make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail')]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        by_account = {r['account']: r for r in view['accounts']}
        self.assertEqual(by_account['openai-apple']['source'], 'live native probe')
        self.assertEqual(by_account['openai-apple']['freshness'], 'live')
        self.assertEqual(by_account['openai-apple']['windows'][0]['used_percent'], 3)
        self.assertEqual(by_account['anthropic-apple']['source'], 'status line cache')
        self.assertIn('10 minutes old', by_account['anthropic-apple']['freshness'])
        self.assertEqual(by_account['anthropic-apple']['windows'][0]['used_percent'], 12)
        # account order follows environments.ACCOUNTS regardless of observe() ordering
        self.assertEqual([r['account'] for r in view['accounts']],
                         ['anthropic-apple', 'anthropic-gmail', 'openai-apple', 'openai-gmail'])

    def test_no_secret_shaped_value_from_the_probe_reaches_the_rendered_table(self):
        poisoned_codex = make_codex_observation('openai-apple', 'ready', 3)
        poisoned_codex['secret'] = 'NEVER-SHOULD-RENDER'
        poisoned_codex['quota'][0]['primary']['secret'] = 'NEVER-SHOULD-RENDER-EITHER'
        rows = [poisoned_codex, make_codex_observation('openai-gmail', 'exhausted', 100),
                make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail')]
        view = usage.unified_view(self.data, observe=self.observe_all(rows), cache_root=self.cache_root, now=self.now)
        rendered = usage.table(view)
        self.assertNotIn('NEVER-SHOULD-RENDER', rendered)
        self.assertNotIn('NEVER-SHOULD-RENDER-EITHER', json.dumps(view))

    def test_table_renders_without_crashing_and_shows_freshness(self):
        rows = [make_codex_observation('openai-apple', 'ready', 3), make_codex_observation('openai-gmail', 'exhausted', 100),
                make_claude_observation('anthropic-apple'), make_claude_observation('anthropic-gmail')]
        rendered = usage.table(usage.unified_view(self.data, observe=self.observe_all(rows),
                                                   cache_root=self.cache_root, now=self.now))
        self.assertIn('FRESHNESS', rendered)
        self.assertIn('live', rendered)
        self.assertIn('unknown: no reading yet', rendered)

    def test_cache_path_matches_the_collector_contract(self):
        # integrations/claude/usage-collector.py writes to ~/.local/state/dev-platform/usage/<account>.json;
        # this must be the same path usage.py reads from, independent of any override.
        self.assertEqual(usage.cache_path('anthropic-apple'),
                         Path.home() / '.local/state/dev-platform/usage/anthropic-apple.json')


if __name__ == '__main__':
    unittest.main()


class OpenRigSeatSource(unittest.TestCase):
    """OpenRig keeps its own status line cache, one file per seat. A reading is attributed to
    the account whose home the seat ran in, by the node's config_home, and the freshest
    reading with a live window wins. Everything here is a fake OpenRig home under a temp dir;
    the real ~/.openrig is never read because `openrig_home` is passed explicitly."""

    def setUp(self):
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        patcher = unittest.mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        temp = tempfile.TemporaryDirectory(prefix='usage-openrig-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.apple_home = self.root / 'homes' / 'anthropic-apple'
        self.apple_home.mkdir(parents=True)
        self.data = {'version': 1, 'selected': None, 'bindings': {
            'anthropic-apple': {'home': str(self.apple_home), 'expected_email': 'a@example.test'},
            'anthropic-gmail': {'home': str(self.root / 'homes' / 'default'), 'expected_email': 'g@example.test',
                                'native_default': True},
        }}
        self.openrig = self.root / 'openrig'
        (self.openrig / 'state' / 'provider-usage').mkdir(parents=True)
        self.cache_root = self.root / 'cache'
        self.cache_root.mkdir()
        self.now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
        import sqlite3
        conn = sqlite3.connect(self.openrig / 'openrig.sqlite')
        conn.executescript('CREATE TABLE nodes (id TEXT, runtime TEXT, config_home TEXT);'
                           'CREATE TABLE sessions (node_id TEXT, session_name TEXT);')
        conn.executemany('INSERT INTO nodes VALUES (?, ?, ?)', [
            ('n-apple', 'claude-code', str(self.apple_home)),
            ('n-default', 'claude-code', None),
            ('n-codex', 'codex', str(self.apple_home)),
        ])
        conn.executemany('INSERT INTO sessions VALUES (?, ?)', [
            ('n-apple', 'lead@team'), ('n-default', 'control@dev'), ('n-codex', 'planner@team')])
        conn.commit()
        conn.close()

    def seat_file(self, seat, as_of, five_hour=None, seven_day=None):
        limits = {}
        if five_hour:
            limits['five_hour'] = {'usedPercent': five_hour[0], 'resetsAt': five_hour[1]}
        if seven_day:
            limits['seven_day'] = {'usedPercent': seven_day[0], 'resetsAt': seven_day[1]}
        body = {'seatSession': seat, 'asOf': as_of}
        if limits:
            body.update(accountKind='subscription', rateLimits=limits)
        (self.openrig / 'state' / 'provider-usage' / (seat + '.json')).write_text(json.dumps(body))

    def observe(self, data):
        return [{'account': a, 'runtime': 'claude', 'state': 'quota_unknown', 'capabilities': {}, 'quota': None,
                 'observed_at': 0, 'remaining_percent': None, 'reason': None}
                for a in ('anthropic-apple', 'anthropic-gmail')] + [
                {'account': a, 'runtime': 'codex', 'state': 'unverified', 'capabilities': {}, 'quota': None,
                 'observed_at': 0, 'remaining_percent': None, 'reason': None}
                for a in ('openai-apple', 'openai-gmail')]

    def view(self):
        v = usage.unified_view(self.data, observe=self.observe, cache_root=self.cache_root,
                               now=self.now, openrig_home=self.openrig)
        return {r['account']: r for r in v['accounts']}

    def test_pinned_seat_reading_is_attributed_to_the_account_owning_that_home(self):
        self.seat_file('lead@team', '2026-09-24T11:50:00.000Z', five_hour=(33, '2026-09-24T15:00:00.000Z'))
        row = self.view()['anthropic-apple']
        self.assertEqual(row['state'], 'cached')
        self.assertEqual(row['source'], 'OpenRig seat lead@team')
        self.assertEqual(row['freshness'], 'OpenRig seat lead@team, 10 minutes old')
        self.assertEqual(row['windows'][0]['used_percent'], 33)
        self.assertEqual(self.view()['anthropic-gmail']['freshness'], 'unknown: no reading yet')

    def test_unpinned_seat_reading_goes_to_the_native_default_account(self):
        self.seat_file('control@dev', '2026-09-24T11:59:00.000Z', seven_day=(8, '2026-09-30T00:00:00.000Z'))
        rows = self.view()
        self.assertEqual(rows['anthropic-gmail']['source'], 'OpenRig seat control@dev')
        self.assertEqual(rows['anthropic-apple']['freshness'], 'unknown: no reading yet')

    def test_codex_seats_and_files_without_windows_contribute_nothing(self):
        self.seat_file('planner@team', '2026-09-24T11:59:00.000Z', five_hour=(99, '2026-09-24T15:00:00.000Z'))
        self.seat_file('lead@team', '2026-09-24T11:59:00.000Z')  # asOf only, the pre-fix OpenRig shape
        self.assertEqual(self.view()['anthropic-apple']['freshness'], 'unknown: no reading yet')

    def test_freshest_reading_across_both_sources_wins_and_names_its_source(self):
        older = (self.now - timedelta(minutes=40)).strftime('%Y-%m-%dT%H:%M:%SZ')
        usage.cache_path('anthropic-apple', self.cache_root).parent.mkdir(exist_ok=True)
        usage.cache_path('anthropic-apple', self.cache_root).write_text(json.dumps({
            'account': 'anthropic-apple', 'captured_at': older, 'source': 'claude-code-statusline',
            'windows': {'five_hour': {'used_percentage': 50, 'resets_at': 4102444800}}}))
        self.seat_file('lead@team', '2026-09-24T11:55:00.000Z', five_hour=(61, '2026-09-24T15:00:00.000Z'))
        row = self.view()['anthropic-apple']
        self.assertEqual(row['source'], 'OpenRig seat lead@team')
        self.assertEqual(row['windows'][0]['used_percent'], 61)
        # and the platform cache still wins when it is the newer one
        newer = (self.now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        usage.cache_path('anthropic-apple', self.cache_root).write_text(json.dumps({
            'account': 'anthropic-apple', 'captured_at': newer, 'source': 'claude-code-statusline',
            'windows': {'five_hour': {'used_percentage': 50, 'resets_at': 4102444800}}}))
        self.assertEqual(self.view()['anthropic-apple']['source'], 'status line cache')

    def test_missing_openrig_home_or_database_is_simply_no_source(self):
        self.assertEqual(usage.openrig_seat_readings(self.root / 'nowhere'), [])
        (self.openrig / 'openrig.sqlite').unlink()
        self.assertEqual(usage.openrig_seat_readings(self.openrig), [])
