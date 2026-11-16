"""Resolve ONLY TIPSTER V2 archive add/add or modify conflicts during git rebase.
Fail closed on other conflicts and divergent immutable prediction records.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ARCHIVE = 'tipster_v2_arsiv.json'


def git(*args, check=True):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=check)


def parse(raw):
    obj = json.loads(raw)
    if not isinstance(obj, dict) or not isinstance(obj.get('records'), dict):
        raise ValueError('Archive must contain records object')
    return obj['records']


def merge(ours, theirs):
    result = dict(ours)
    for key, record in theirs.items():
        if key in result and result[key] != record:
            raise ValueError('Immutable archive record differs: ' + key)
        result[key] = record
    return {'records': result}


def run():
    outcome = git('pull', '--rebase', 'origin', 'main', check=False)
    if outcome.returncode == 0:
        print('Rebase completed without conflict')
        return
    print(outcome.stdout, outcome.stderr, file=sys.stderr)
    for attempt in range(10):
        conflicts = {line.strip() for line in git('diff', '--name-only', '--diff-filter=U').stdout.splitlines() if line.strip()}
        if conflicts != {ARCHIVE}:
            raise RuntimeError('Cannot safely resolve conflicts: ' + repr(sorted(conflicts)))
        ours = git('show', ':2:' + ARCHIVE).stdout
        theirs = git('show', ':3:' + ARCHIVE).stdout
        # Rebase swaps branch roles; union is symmetric and rejects revisions.
        combined = merge(parse(ours), parse(theirs))
        Path(ARCHIVE).write_text(json.dumps(combined, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        git('add', ARCHIVE)
        env = dict(os.environ, GIT_EDITOR='true')
        step = subprocess.run(['git', 'rebase', '--continue'], env=env, capture_output=True, text=True)
        if step.returncode == 0:
            print('Archive conflict merged without losing unique records')
            return
        print(step.stdout, step.stderr, file=sys.stderr)
        # If rebase continues and finds another conflict, loop; otherwise fail.
        if not git('diff', '--name-only', '--diff-filter=U').stdout.strip():
            raise RuntimeError('Rebase continue failed without resolvable conflicts')
    raise RuntimeError('Too many rebase conflicts')


if __name__ == '__main__':
    run()
