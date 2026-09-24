#!/usr/bin/env python3
"""Run committed Pi role checks in an image without account homes or networking."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', help='Candidate image tag or immutable image ID')
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    revision = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', args.image]))[0]['Id']
    # Export only committed source: never mount the live checkout, credentials,
    # journal or native account homes into this disposable verification container.
    with tempfile.TemporaryDirectory(prefix='pi-image-check-') as directory:
        root = Path(directory)
        root.chmod(0o755)
        archive = subprocess.check_output(['git', '-C', str(repository), 'archive', revision])
        subprocess.run(['tar', '-x', '-C', directory], input=archive, check=True)
        (root / 'integrations/pi/node_modules').symlink_to('/opt/openrig/node_modules')
        prefix = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
                  '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                  '--tmpfs', '/tmp:rw,nosuid,nodev', '--env', 'HOME=/tmp',
                  '--env', 'PI_OFFLINE=1', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                  '--mount', f'type=bind,source={directory},target=/platform,readonly',
                  '--workdir', '/platform', '--entrypoint']
        checks = [
            ('node', '--version'), ('pi', '--version'),
            ('node', '/platform/integrations/pi/check-role-context.mjs'),
            ('node', '/platform/integrations/pi/check-role-skills.mjs'),
            ('node', '/platform/integrations/pi/check-role-history.mjs'),
            ('node', '/platform/integrations/pi/check-role-session.mjs'),
            ('node', '/platform/integrations/pi/check-perplexity.mjs'),
            ('python3', '/platform/integrations/pi/check-role-terminal.py'),
        ]
        uid = subprocess.check_output([*prefix, 'id', image, '-u'], text=True).strip()
        if uid == '0':
            raise RuntimeError('Image runs as root')
        for executable, argument in checks:
            print(f'Checking {Path(argument).name}', flush=True)
            result = subprocess.run([*prefix, executable, image, argument],
                                    timeout=90, capture_output=True, text=True)
            print(result.stdout, end='', flush=True)
            if result.returncode:
                print(result.stderr, end='', flush=True)
                result.check_returncode()
            if argument == '--version':
                expected = {'node': 'v24.14.0', 'pi': '0.87.1'}[executable]
                if result.stdout.strip() != expected:
                    raise RuntimeError(f'{executable} version differs from {expected}')
    print(json.dumps({'passed': True, 'image': image, 'revision': revision,
                      'checks': len(checks), 'scope': 'Offline image components; no account authentication or bind-mounted conversation acceptance'}))


if __name__ == '__main__':
    main()
