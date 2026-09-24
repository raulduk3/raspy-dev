#!/usr/bin/env python3
"""Tasks for a local repository, read from docs/tasks/ on a Git ref, in the shape `gh` returns.

A task is `docs/tasks/<N>-<slug>.md`: its first `# ` heading is the title and the file is the
body. A `Status:` line of `ready` makes it selectable (the `sprint-ready` label); `Labels:` adds
comma-separated labels. A task moved to `docs/tasks/done/` is closed. The number N is the join
key the loop uses everywhere else: worktree, branch, ledger and `Closes #N`.

Usage: loop-tasks.py <checkout> <ref> issues          open tasks, as `gh issue list --json`
       loop-tasks.py <checkout> <ref> closed          closed task numbers, as [{"number": N}]
       loop-tasks.py <checkout> <ref> view <N>        one task, as `gh issue view --json`
       loop-tasks.py <checkout> <ref> path <N>        the task file's path in the repository
"""
import json
import re
import subprocess
import sys

TASKS = 'docs/tasks/'
DONE = TASKS + 'done/'
NAME = re.compile(r'^(\d+)-[^/]+\.md$')


def files(checkout, ref):
    listing = subprocess.run(['git', '-C', checkout, 'ls-tree', '-r', '--name-only', ref, '--', TASKS],
                             capture_output=True, text=True)
    if listing.returncode:
        sys.exit(f'loop-tasks: cannot read {TASKS} on {ref}')
    found = {}
    for path in listing.stdout.splitlines():
        folder, _, name = path.rpartition('/')
        match = NAME.match(name)
        if match and folder + '/' in (TASKS, DONE):
            found.setdefault(int(match.group(1)), []).append(path)
    return found


def task(checkout, ref, number, path):
    body = subprocess.run(['git', '-C', checkout, 'show', f'{ref}:{path}'],
                          capture_output=True, text=True, check=True).stdout
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith('# ')), path)
    field = lambda name: next((m.group(1).strip() for m in re.finditer(rf'(?m)^{name}: *(.+)$', body)), '')
    labels = [label.strip() for label in field('Labels').split(',') if label.strip()]
    if field('Status').lower() == 'ready' and path.startswith(TASKS) and not path.startswith(DONE):
        labels.append('sprint-ready')
    return {'number': number, 'title': title, 'body': body, 'milestone': None,
            'labels': [{'name': label} for label in labels], 'path': path}


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    checkout, ref, verb, *rest = argv
    found = files(checkout, ref)
    duplicate = sorted(n for n, paths in found.items() if len(paths) > 1)
    if duplicate:
        sys.exit('loop-tasks: more than one task file for ' + ', '.join(f'#{n}' for n in duplicate))
    closed = {n for n, (path,) in found.items() if path.startswith(DONE)}
    if verb == 'issues':
        print(json.dumps([task(checkout, ref, n, found[n][0]) for n in sorted(found) if n not in closed]))
    elif verb == 'closed':
        print(json.dumps([{'number': n} for n in sorted(closed)]))
    elif verb in ('view', 'path') and len(rest) == 1 and rest[0].isdigit():
        number = int(rest[0])
        if number not in found:
            sys.exit(f'loop-tasks: no task #{number} in {TASKS} on {ref}')
        item = task(checkout, ref, number, found[number][0])
        print(item['path'] if verb == 'path' else json.dumps(item))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
