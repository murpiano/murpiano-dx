#!/usr/bin/env python3
"""Connect project instructions to the shared store without publishing anything."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

SOURCE_ROOT = Path(__file__).resolve().parent
ROOT = SOURCE_ROOT
DATA_ROOT = Path(os.environ.get(
    'MURPIANO_DX_DATA_DIR',
    Path.home() / '.murpiano-dx',
)).expanduser()
STORE = DATA_ROOT / 'projects'
PATHS = ('AGENTS.md', '.agents')
BEGIN = '# >>> murpiano-dx'
END = '# <<< murpiano-dx'
ACTIVE_ROOT = ROOT

WORKSPACE_FILES = (
    'murpiano-dx', 'install.sh', 'sync.sh', 'sync.py', 'configure-codex.py',
    'config.env', 'README.md', 'LICENSE', 'resources/logo.png',
    'resources/project-data-flow.svg',
)
WORKSPACE_DIRS = ('global', 'skills', 'defaults')
WORKSPACE_MARKER = '.murpiano-dx-workspace'


def copy_missing_tree(source, target):
    if not source.is_dir():
        return
    for item in source.rglob('*'):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def bootstrap_workspace_files():
    """Copy the distributable framework into the user's local workspace."""
    global ACTIVE_ROOT
    if DATA_ROOT.resolve() == SOURCE_ROOT.resolve():
        ACTIVE_ROOT = SOURCE_ROOT
        return
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name in WORKSPACE_FILES:
        source = SOURCE_ROOT / name
        destination = DATA_ROOT / name
        if source.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for name in WORKSPACE_DIRS:
        copy_missing_tree(SOURCE_ROOT / name, DATA_ROOT / name)
    workspace_ignore = DATA_ROOT / '.gitignore'
    if not workspace_ignore.exists():
        workspace_ignore.write_text('__pycache__/\n*.pyc\n')
    marker = DATA_ROOT / WORKSPACE_MARKER
    if not marker.exists():
        marker.write_text('Local murpiano-dx workspace.\n')
    ACTIVE_ROOT = DATA_ROOT


def ensure_workspace():
    """Create the editable local workspace without overwriting user files."""
    bootstrap_workspace_files()
    (DATA_ROOT / 'config').mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / 'rules').mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / 'templates').mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / 'logs').mkdir(parents=True, exist_ok=True)
    STORE.mkdir(parents=True, exist_ok=True)
    machine = DATA_ROOT / 'config' / 'machine.json'
    if not machine.exists():
        machine.write_text(json.dumps({
            'git_name': os.environ.get('GIT_NAME', ''),
            'git_email': os.environ.get('GIT_EMAIL', ''),
            'github_owner': os.environ.get('GITHUB_OWNER', ''),
        }, indent=2) + '\n')
    defaults = SOURCE_ROOT / 'defaults'
    for group in ('rules', 'templates'):
        source = defaults / group
        target = DATA_ROOT / group
        if source.is_dir():
            for item in source.iterdir():
                destination = target / item.name
                if not destination.exists():
                    shutil.copy2(item, destination)


def initialize_workspace_repo():
    """Make the local workspace a Git repository, preserving existing files."""
    if DATA_ROOT.resolve() == SOURCE_ROOT.resolve() or (DATA_ROOT / '.git').exists():
        return
    result = subprocess.run(['git', 'init', '-b', 'main'], cwd=DATA_ROOT,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Could not initialize workspace Git')
    for name, env_name in [('user.name', 'GIT_NAME'), ('user.email', 'GIT_EMAIL')]:
        value = os.environ.get(env_name)
        if value:
            subprocess.run(['git', '-C', str(DATA_ROOT), 'config', name, value], check=True)
    identity = subprocess.run(['git', '-C', str(DATA_ROOT), 'config', '--get', 'user.name'],
                              text=True, capture_output=True, check=False).stdout.strip()
    email = subprocess.run(['git', '-C', str(DATA_ROOT), 'config', '--get', 'user.email'],
                           text=True, capture_output=True, check=False).stdout.strip()
    if identity and email:
        subprocess.run(['git', '-C', str(DATA_ROOT), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(DATA_ROOT), 'commit', '-m',
                        'chore: initialize local workspace'], check=True,
                       capture_output=True, text=True)


def sync_workspace():
    """Commit workspace state and push it when a private remote is configured."""
    if (DATA_ROOT / WORKSPACE_MARKER).is_file() is False:
        return
    if not (DATA_ROOT / '.git').exists() or not (DATA_ROOT / 'config/machine.json').exists():
        return
    subprocess.run(['git', '-C', str(DATA_ROOT), 'add', '-A'], check=True)
    changes = subprocess.run(['git', '-C', str(DATA_ROOT), 'diff', '--cached', '--quiet'],
                             check=False)
    if changes.returncode:
        identity = subprocess.run(
            ['git', '-C', str(DATA_ROOT), 'config', '--get', 'user.name'],
            text=True, capture_output=True, check=False).stdout.strip()
        email = subprocess.run(
            ['git', '-C', str(DATA_ROOT), 'config', '--get', 'user.email'],
            text=True, capture_output=True, check=False).stdout.strip()
        if not identity or not email:
            raise RuntimeError('Workspace Git identity is not configured; run murpiano-dx setup.')
        subprocess.run(['git', '-C', str(DATA_ROOT), 'commit', '-m',
                        'chore(workspace): sync project state'], check=True,
                       capture_output=True, text=True)
        print('Workspace state committed.')
    remote = git(DATA_ROOT, 'remote', 'get-url', 'origin', check=False)
    if remote:
        git(DATA_ROOT, 'push')
        print(f'Workspace state pushed to {remote}.')


def load_machine_config():
    path = DATA_ROOT / 'config' / 'machine.json'
    if not path.is_file():
        return
    try:
        values = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    for key, env_name in [('git_name', 'GIT_NAME'), ('git_email', 'GIT_EMAIL'),
                          ('github_owner', 'GITHUB_OWNER')]:
        if not os.environ.get(env_name) and values.get(key):
            os.environ[env_name] = str(values[key])


def git(project, *args, check=True):
    result = subprocess.run(['git', '-C', str(project), *args], text=True,
                            capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git command failed')
    return result.stdout.strip()


def git_path(project, name):
    path = Path(git(project, 'rev-parse', '--git-path', name))
    return path if path.is_absolute() else project / path


def project_key(url):
    match = re.fullmatch(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?', url)
    if match:
        owner, repo = match.groups()
    else:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'ssh') or parsed.hostname != 'github.com':
            return None
        parts = parsed.path.strip('/').split('/')
        if len(parts) != 2:
            return None
        owner, repo = parts
        repo = repo.removesuffix('.git')
    expected = os.environ['GITHUB_OWNER']
    if (owner.lower() != expected.lower() or
            not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or repo in ('.', '..')):
        return None
    return f'{expected}/{repo}'


@contextmanager
def store_lock():
    STORE.mkdir(parents=True, exist_ok=True)
    try:
        handle = (STORE / '.sync.lock').open('a')
    except OSError as error:
        raise RuntimeError(f'Could not acquire the project store lock: {error}') from error
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('The project store is busy with another sync; retry the command.') from error
        yield


def exclude_agent_files(project):
    path = git_path(project, 'info/exclude')
    text = path.read_text() if path.exists() else ''
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise RuntimeError(f'Invalid exclusion markers: {path}')
    if BEGIN in text:
        prefix, rest = text.split(BEGIN, 1)
        _, suffix = rest.split(END, 1)
        text = prefix + suffix
    rules = (ACTIVE_ROOT / 'global/gitignore-agents').read_text().rstrip()
    updated = text.rstrip() + '\n\n' + BEGIN + '\n' + rules + '\n' + END + '\n'
    if not path.exists() or path.read_text() != updated:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated)


def remove_old_hook(project):
    path = git_path(project, 'hooks') / 'pre-commit'
    if not path.is_file() or path.is_symlink():
        return
    lines = path.read_text().splitlines()
    marker = '# murpiano-dx: agent-trace pre-commit scan (skills/repo-cleanup)'
    if marker not in lines:
        return
    if (len(lines) == 3 and lines[0] == '#!/usr/bin/env bash' and lines[1] == marker
            and lines[2] == f'exec bash "{ACTIVE_ROOT}/skills/repo-cleanup/pre-commit-hook.sh"'):
        path.unlink()
        print('Removed the previous murpiano-dx pre-commit hook.')
    else:
        print(f'Check the previous repo-cleanup call in {path}: the modified hook was preserved.')


def attach(project, key):
    files = STORE / key / 'files'
    files.mkdir(parents=True, exist_ok=True)
    for name in PATHS:
        source, target = project / name, files / name
        if source.is_symlink():
            if source.resolve() != target.resolve():
                print(f'Link conflict: {source}. The link was preserved.')
            continue
        if git(project, 'ls-files', '--', name):
            print(f'{name} is tracked by the project; left in place.')
            continue
        moved = False
        if source.exists():
            if target.exists() or target.is_symlink():
                print(f'File conflict: {source} and {target}. Merge manually.')
                continue
            shutil.move(str(source), str(target))
            moved = True
        elif not target.exists() and not target.is_symlink():
            if name == '.agents':
                target.mkdir()
            else:
                text = (ACTIVE_ROOT / 'global/project-rules.md').read_text()
                for token, value in [('{{PROJECT}}', key), ('{{ROOT}}', str(ACTIVE_ROOT)),
                                     ('{{DATA_ROOT}}', str(DATA_ROOT)),
                                     ('{{STORE}}', str(STORE / key)),
                                     ('{{SYNC}}', 'bash ' + shlex.quote(str(ACTIVE_ROOT / 'sync.sh')))]:
                    text = text.replace(token, value)
                target.write_text(text)
        try:
            source.symlink_to(target, target_is_directory=(name == '.agents'))
        except OSError:
            if moved:
                shutil.move(str(target), str(source))
            raise
    print(f'Project data: {STORE / key}')
    memory = STORE / key / 'memory'
    if memory.is_dir():
        print(f'Saved memory: {memory}. Read MEMORY.md and relevant notes.')


def kysaro_gaps(project):
    gaps = []
    if shutil.which('node') is None:
        gaps.append('Node.js')
    binary = project / 'node_modules/.bin/kysaro'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        gaps.append('local kysaro')
    for name in ('commit', 'merge', 'request'):
        path = project / f'.kysaro/settings/commits/{name}.json'
        try:
            if not isinstance(json.loads(path.read_text()), dict):
                gaps.append(f'{name} settings')
        except (OSError, ValueError):
            gaps.append(f'{name} settings')
    hooks = git_path(project, 'hooks')
    active = hooks / 'commit-msg'
    hooked = active.is_file() and os.access(active, os.X_OK) and 'kysaro' in active.read_text()
    if hooks.name == '_' and hooks.parent.name == '.husky':
        user_hook = hooks.parent / 'commit-msg'
        hooked = (active.is_file() and os.access(active, os.X_OK) and
                  user_hook.is_file() and 'kysaro' in user_hook.read_text())
    if not hooked:
        gaps.append('active commit-msg')
    workflows = project / '.github/workflows'
    checked_in_ci = workflows.is_dir() and any(
        p.suffix in ('.yml', '.yaml') and 'kysaro ci' in p.read_text()
        for p in workflows.iterdir() if p.is_file())
    if not checked_in_ci:
        gaps.append('CI kysaro')
    return gaps


def load_workflow(key):
    path = STORE / key / 'workflow.json'
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text())
    except (ValueError, UnicodeError) as error:
        raise RuntimeError(f'Invalid initialization state: {path}') from error
    if not isinstance(state, dict) or state.get('kysaro') not in (
            'pending', 'approved', 'declined', 'enabled'):
        raise RuntimeError(f'Invalid initialization state: {path}')
    return state


def save_workflow(key, state):
    path = STORE / key / 'workflow.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(path)


def report(project, key, state, initializing=False):
    status = state['kysaro']
    if status == 'enabled':
        gaps = kysaro_gaps(project)
        status = 'configured' if not gaps else 'restore: ' + ', '.join(gaps)
    else:
        status = {'pending': 'decision pending', 'approved': 'approved, setup incomplete',
                  'declined': 'declined by owner'}[status]
    branch = git(project, 'branch', '--show-current')
    print(f'{key} | branch: {branch or "detached HEAD"} | kysaro: {status}')
    print(f'Context: {STORE / key}. Task rules: {ACTIVE_ROOT}/skills/')
    if any(not (project / name).exists() for name in PATHS):
        print('Instructions or notes are not connected in this copy; restore them through init on request.')
    if initializing and state['kysaro'] == 'pending':
        print('Offer kysaro installation: local dependency, commit-msg, settings, and CI. '
              'Continue with: skills/repo-init/SKILL.md.')
    elif initializing and state['kysaro'] == 'approved':
        print('Continue the approved setup from skills/repo-init/kysaro.md.')


def connect(folder, mode='start', choice=None, quiet=False):
    initialize = mode == 'init'
    root = git(folder, 'rev-parse', '--show-toplevel', check=False)
    if not root:
        if not initialize:
            if not quiet:
                print(f'No Git repository. To connect: bash '
                      f'{shlex.quote(str(ACTIVE_ROOT / "sync.sh"))} init {shlex.quote(str(folder))}')
            return
        git(folder, 'init', '-b', 'main')
        for name, value in [('user.name', os.environ['GIT_NAME']),
                            ('user.email', os.environ['GIT_EMAIL'])]:
            if not git(folder, 'config', '--get', name, check=False):
                git(folder, 'config', '--local', name, value)
        root = str(folder)
    project = Path(root).resolve()
    if project == ACTIVE_ROOT:
        if not quiet:
            print('murpiano-dx: use skills/ as the shared rules source; self-connection is not required.')
        return
    url = git(project, 'remote', 'get-url', 'origin', check=False)
    if not url:
        if quiet:
            return
        if not initialize:
            print('No origin. Connect through repo-init when the owner requests it.')
            return
        exclude_agent_files(project)
        print('Local Git is ready. Offer the owner a private GitHub repository.')
        print('After approval, from the project directory: gh repo create --private --source=. --remote=origin')
        print('Then repeat init. Commits, GitHub repository creation, and push are not automatic.')
        return
    key = project_key(url)
    if key is None:
        if not quiet:
            print('Origin does not belong to the configured GitHub owner; unchanged. Connection skipped.')
        return
    if mode == 'start':
        state = load_workflow(key)
        if state is None:
            print(f'{key}: project is not initialized. Use repo-init when the owner requests it.')
        else:
            report(project, key, state)
        return
    with store_lock():
        state = load_workflow(key)
        if state is None and not initialize:
            if not quiet:
                print(f'{key}: first perform explicit initialization through repo-init.')
            return
        state = state or {'kysaro': 'pending'}
        exclude_agent_files(project)
        remove_old_hook(project)
        attach(project, key)
        if initialize:
            if choice == 'enabled':
                gaps = kysaro_gaps(project)
                if gaps:
                    raise RuntimeError('Kysaro setup incomplete: ' + ', '.join(gaps))
            if choice:
                state['kysaro'] = choice
            elif state['kysaro'] == 'pending' and not kysaro_gaps(project):
                state['kysaro'] = 'enabled'
            save_workflow(key, state)
    if not quiet and initialize:
        report(project, key, state, initializing=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['init', 'start', 'end', 'link', 'workspace'], nargs='?', default='start')
    parser.add_argument('project', type=Path, nargs='?', default=Path.cwd())
    parser.add_argument('--kysaro', choices=['approved', 'declined', 'enabled'],
                        help='Record the owner decision or verify completed setup (init only)')
    args = parser.parse_args()
    ensure_workspace()
    load_machine_config()
    initialize_workspace_repo()
    if args.kysaro and args.mode != 'init':
        parser.error('--kysaro is only available with init')
    if args.mode == 'workspace':
        print(f'Local workspace: {DATA_ROOT}')
        print('Framework files and project data are stored in this Git repository.')
        return
    if args.mode == 'link':
        parent = Path(os.environ.get('PROJECTS_DIR', Path.home() / 'projects'))
        if parent.is_dir():
            for folder in sorted(parent.iterdir()):
                if folder.is_dir():
                    connect(folder.resolve(), mode='link', quiet=True)
    else:
        connect(args.project.resolve(), mode=args.mode, choice=args.kysaro)
    if args.mode == 'end':
        sync_workspace()


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
