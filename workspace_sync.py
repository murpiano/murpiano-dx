#!/usr/bin/env python3
"""Automatic backup of a personal workspace, never of connected source code."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def git(root, *args, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    result = subprocess.run(['git', '-C', str(root), *args], env=env,
                            capture_output=True, text=True, timeout=90)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Git operation failed')
    return result


def is_workspace(root):
    return ((root / '.murpiano-dx-workspace').is_file()
            and (root / '.git').exists() and (root / 'config/machine.json').is_file())


def prepare_local_files(root):
    """Keep machine-local locks and diagnostics out of workspace commits."""
    location = git(root, 'rev-parse', '--git-path', 'info/exclude').stdout.strip()
    exclude = Path(location)
    if not exclude.is_absolute():
        exclude = root / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    text = exclude.read_text() if exclude.exists() else ''
    patterns = ['/logs/', '/projects/.sync.lock', '/.runtime-backup/', '__pycache__/', '*.pyc']
    missing = [pattern for pattern in patterns if pattern not in text.splitlines()]
    if missing:
        exclude.write_text(text + ('\n' if text and not text.endswith('\n') else '')
                           + '\n'.join(missing) + '\n')
    (root / 'logs').mkdir(exist_ok=True)


@contextmanager
def lock(path):
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def synchronize(root):
    """Snapshot, fetch, merge, push. Conflicts retain both committed versions."""
    root = Path(root).resolve()
    if not is_workspace(root):
        return False
    prepare_local_files(root)
    with lock(root / 'logs/sync.lock') as acquired:
        if not acquired:
            return False
        git_dir = Path(git(root, 'rev-parse', '--absolute-git-dir').stdout.strip())
        if any((git_dir / name).exists() for name in
               ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'index.lock')):
            raise RuntimeError('Workspace has an unfinished Git operation; synchronization postponed.')
        branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
        if not branch:
            raise RuntimeError('Workspace HEAD is detached; synchronization postponed.')
        git(root, 'add', '-A')
        changed = git(root, 'diff', '--cached', '--quiet', check=False)
        if changed.returncode == 1:
            git(root, 'commit', '-m', 'chore(workspace): sync project state')
        elif changed.returncode:
            raise RuntimeError(changed.stderr.strip() or 'Cannot inspect workspace changes')
        if not git(root, 'remote', 'get-url', 'origin', check=False).returncode:
            git(root, 'fetch', 'origin')
            remote_ref = f'refs/remotes/origin/{branch}'
            if git(root, 'show-ref', '--verify', '--quiet', remote_ref, check=False).returncode == 0:
                # Files may have changed during fetch. Never stash, reset, or overwrite them.
                if git(root, 'status', '--porcelain').stdout.strip():
                    raise RuntimeError('Workspace changed during fetch; retrying on the next sync.')
                merged = git(root, 'merge', '--no-edit', remote_ref, check=False)
                if merged.returncode:
                    if (git_dir / 'MERGE_HEAD').exists():
                        git(root, 'merge', '--abort')
                    raise RuntimeError('Workspace remote changes could not be merged. '
                                       'Local and remote commits are preserved. Resolve the conflict, '
                                       'then automatic sync will retry. ' + merged.stdout.strip()
                                       + ' ' + merged.stderr.strip())
            git(root, 'push', '-u', 'origin', f'HEAD:refs/heads/{branch}')
        return True


def configure_remote(root, ask=input):
    """Ask once about an optional GitHub backup, preserving an existing origin."""
    root = Path(root)
    choice = root / 'config/backup.json'
    if git(root, 'remote', 'get-url', 'origin', check=False).returncode == 0 or choice.exists():
        return
    answer = ask('Create a GitHub repository for this workspace? [y/N]: ').strip().lower()
    if answer not in ('y', 'yes'):
        remote = ask('Existing repository URL (empty to keep local only): ').strip()
        if remote:
            git(root, 'remote', 'add', 'origin', remote)
        settings = {'enabled': bool(remote), 'remote': remote}
    else:
        owner = os.environ.get('GITHUB_OWNER', '').strip()
        if not owner:
            raise RuntimeError('GitHub owner is not configured. Run setup first.')
        visibility = ask('Visibility [private/public, default private]: ').strip().lower() or 'private'
        if visibility not in ('private', 'public'):
            raise RuntimeError('Visibility must be private or public. No repository was created.')
        name = ask('Repository name [murpiano-dx-workspace]: ').strip() or 'murpiano-dx-workspace'
        subprocess.run(['gh', 'repo', 'create', f'{owner}/{name}', f'--{visibility}',
                        f'--source={root}', '--remote=origin'], check=True)
        settings = {'enabled': True, 'visibility': visibility, 'repository': f'{owner}/{name}'}
    choice.write_text(json.dumps(settings, indent=2) + '\n')
    # Save the choice before network work; the next session can retry an offline push.
    try:
        synchronize(root)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Backup configured; synchronization pending: {error}', file=sys.stderr)


if __name__ == '__main__':
    try:
        if sys.argv[1] == '--configure-remote':
            if sys.stdin.isatty():
                configure_remote(Path(sys.argv[2]))
        else:
            raise RuntimeError('Usage: workspace_sync.py --configure-remote WORKSPACE')
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
