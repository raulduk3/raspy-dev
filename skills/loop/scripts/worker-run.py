#!/usr/bin/env python3
"""Bound one worker's wall time and process group; no scheduling or account fallback."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    seconds, result, sep, *command = sys.argv[1:]
    if sep != '--' or not command or int(seconds) <= 0:
        raise SystemExit('worker-run: invalid arguments')
    names = ['HOME', 'PATH', 'USER', 'LANG', 'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS']
    names.extend(os.environ.get('DEV_PLATFORM_ENV_PASS', '').split())
    env = {k: os.environ[k] for k in names if k in os.environ}
    env['TERM'] = 'dumb'
    process = None
    started = time.monotonic()
    code = 1
    reason = 'failed_to_start'
    def interrupted(signum, frame):
        raise InterruptedError(signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        process = subprocess.Popen(command, env=env, start_new_session=True)
        try:
            code = process.wait(timeout=int(seconds))
            reason = 'exited'
        except (subprocess.TimeoutExpired, InterruptedError) as error:
            code = 124 if isinstance(error, subprocess.TimeoutExpired) else 130
            reason = 'wall_time_limit' if code == 124 else 'interrupted'
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            # Kill remaining grandchildren even if the process-group leader already exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    finally:
        target = Path(result)
        tmp = target.with_suffix('.exit.tmp')
        tmp.write_text(json.dumps({'exit_code': code, 'reason': reason,
                                  'elapsed_seconds': round(time.monotonic() - started, 2)}) + '\n')
        tmp.replace(target)
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    sys.exit(main())
