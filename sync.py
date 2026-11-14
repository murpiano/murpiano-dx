#!/usr/bin/env python3
"""Connect project instructions and synchronize the personal workspace."""
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
import tempfile
from urllib.parse import urlsplit

SOURCE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE_ROOT))
from workspace_sync import prepare_local_files, synchronize

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
    'agent_setup.py', 'workspace_sync.py', 'session_hook.py',
    'config.env', 'README.md', 'LICENSE', 'resources/logo.png',
    'resources/logo-background.png', 'resources/logo-core.png', 'resources/logo-ring.png',
    'resources/logo-preview.html', 'resources/logo-preview.gif',
    'resources/murpiano-signature.png',
    'resources/Roboto-wdth-wght.ttf', 'resources/Roboto-OFL.txt',
    'resources/project-data-flow.svg',
)
WORKSPACE_DIRS = ('global', 'skills', 'defaults')
WORKSPACE_MARKER = '.murpiano-dx-workspace'
VERSION_MARKER = '.murpiano-dx-version'
GITHUB_REPO = 'murpiano/murpiano-dx'
RUNTIME_FILES = {'murpiano-dx', 'install.sh', 'sync.sh', 'sync.py',
                 'configure-codex.py', 'agent_setup.py', 'workspace_sync.py', 'session_hook.py'}
TEMPLATE_LOCATIONS = {
    'readme': Path('skills/repo-readme/templates/README.md'),
    'description': Path('skills/repo-readme/templates/repository-description.md'),
    'release': Path('skills/repo-release/templates/release-notes.md'),
}


def migrate_skill_templates():
    """Move legacy personal templates on explicit setup; archive redundant copies."""
    moves = []
    archive = DATA_ROOT / '.runtime-backup/skill-templates'
    for relative in TEMPLATE_LOCATIONS.values():
        old = DATA_ROOT / 'templates' / relative.name
        new = DATA_ROOT / relative
        if old.exists():
            if new.exists() and old.read_bytes() != new.read_bytes():
                raise RuntimeError(f'Conflicting templates; both kept: {old} and {new}')
            moves.append((old, archive / 'templates' / relative.name if new.exists() else new))
    workflow = DATA_ROOT / 'skills/repo-release/release.yml'
    new_workflow = DATA_ROOT / 'skills/repo-release/templates/release.yml'
    if workflow.exists():
        if new_workflow.exists() and workflow.read_bytes() != new_workflow.read_bytes():
            raise RuntimeError(f'Conflicting templates; both kept: {workflow} and {new_workflow}')
        moves.append((workflow, archive / 'skills/repo-release/release.yml'
                      if new_workflow.exists() else new_workflow))
    redundant = [DATA_ROOT / 'defaults/templates' / path.name
                 for path in TEMPLATE_LOCATIONS.values()]
    redundant.append(DATA_ROOT / 'skills/repo-readme/template.md')
    for old in redundant:
        if old.exists():
            moves.append((old, archive / old.relative_to(DATA_ROOT)))
    # Validate the whole move plan before changing any template.
    for old, new in moves:
        if old.is_symlink() or new.is_symlink():
            raise RuntimeError(f'Template is a symbolic link; review it before setup: {old} -> {new}')
        if new.exists() and old.read_bytes() != new.read_bytes():
            raise RuntimeError(f'Template archive conflict; both kept: {old} and {new}')
    for old, new in moves:
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists():
            old.unlink()  # Identical archived copy already preserves these bytes.
        else:
            old.rename(new)
    for folder in (DATA_ROOT / 'templates', DATA_ROOT / 'defaults/templates'):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()


def copy_missing_tree(source, target, skip=()):
    if not source.is_dir():
        return
    for item in source.rglob('*'):
        relative = item.relative_to(source)
        destination = target / relative
        if destination in skip:
            continue
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def git_describe(repo):
    """Latest v*.*.* tag reachable from repo's HEAD, or '' if not resolvable."""
    result = subprocess.run(
        ['git', '-C', str(repo), 'describe', '--tags', '--abbrev=0',
         '--match', 'v[0-9]*.[0-9]*.[0-9]*'],
        text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ''


def bootstrap_workspace_files(update_runtime=False, source_root=None):
    """Copy the distributable framework into the user's local workspace."""
    global ACTIVE_ROOT
    source_root = source_root or SOURCE_ROOT
    if update_runtime:
        migrate_skill_templates()
    if DATA_ROOT.resolve() == source_root.resolve():
        ACTIVE_ROOT = source_root
        return
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name in WORKSPACE_FILES:
        source = source_root / name
        destination = DATA_ROOT / name
        if source.is_file() and (not destination.exists() or
                                 (update_runtime and name in RUNTIME_FILES)):
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_symlink():
                raise RuntimeError(f'Runtime file is a symbolic link; review it before setup: {destination}')
            if destination.exists() and source.read_bytes() != destination.read_bytes():
                # Keep a rollback copy when upgrading an already installed runtime.
                backup = DATA_ROOT / '.runtime-backup' / name
                if not backup.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup)
            shutil.copy2(source, destination)
    legacy_templates = {DATA_ROOT / relative for relative in TEMPLATE_LOCATIONS.values()
                        if (DATA_ROOT / 'templates' / relative.name).is_file()}
    if (DATA_ROOT / 'skills/repo-release/release.yml').is_file():
        legacy_templates.add(DATA_ROOT / 'skills/repo-release/templates/release.yml')
    for name in WORKSPACE_DIRS:
        copy_missing_tree(source_root / name, DATA_ROOT / name, skip=legacy_templates)
    workspace_ignore = DATA_ROOT / '.gitignore'
    if not workspace_ignore.exists():
        workspace_ignore.write_text('__pycache__/\n*.pyc\n')
    marker = DATA_ROOT / WORKSPACE_MARKER
    if not marker.exists():
        marker.write_text('Local murpiano-dx workspace.\n')
    version = git_describe(source_root)
    if version:
        (DATA_ROOT / VERSION_MARKER).write_text(version + '\n')
    ACTIVE_ROOT = DATA_ROOT


def update_skills_tree(source, target):
    """Force-update skills/ content, except each skill's own templates/.

    skills/ is the framework's shared knowledge base (SKILL.md, rules.md,
    scripts) - owners aren't meant to hand-edit it, overrides belong under
    rules/ (see global/agent-rules.md) - so a bugfix there must reach an
    already-provisioned workspace the same way a global/ change does, not
    sit frozen at whatever version first installed it. The one established
    exception is a skill's own templates/ subdirectory (e.g.
    repo-readme/templates/README.md, repo-release/templates/release-notes.md):
    select_template()'s own precedence rule depends on a personal copy there
    staying exactly as the owner left it, so those paths stay additive-only
    (new default templates arrive; an existing personal one is never touched).
    """
    for item in source.rglob('*'):
        relative = item.relative_to(source)
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        is_template = 'templates' in relative.parts[:-1]
        if is_template and destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.read_bytes() != item.read_bytes():
            shutil.copy2(item, destination)
            print(f'Updated skills/{relative}')


def update_workspace(source_root=None):
    """Refresh an existing local workspace from a murpiano-dx checkout.

    Unlike bootstrap_workspace_files on a first install (additive only), this
    overwrites the framework-owned runtime files, global/ templates, and
    skills/ (except each skill's own templates/, see update_skills_tree)
    unconditionally, so a change to murpiano-dx reaches an already-provisioned
    workspace. defaults/ stays additive (copy_missing_tree never overwrites a
    file that already exists there) - those are project-scaffold starting
    points owners are expected to adjust per project, unlike skills/.
    source_root defaults to this checkout; pass a fetched release checkout to
    update from a GitHub tag instead (see fetch_release_checkout).
    """
    source_root = source_root or SOURCE_ROOT
    if DATA_ROOT.resolve() == source_root.resolve():
        raise RuntimeError(
            'Run update from a murpiano-dx checkout with MURPIANO_DX_DATA_DIR '
            'pointing at the workspace to refresh, not from inside the workspace itself.')
    bootstrap_workspace_files(update_runtime=True, source_root=source_root)
    for item in (source_root / 'global').iterdir():
        if not item.is_file():
            continue
        destination = DATA_ROOT / 'global' / item.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.read_bytes() != item.read_bytes():
            shutil.copy2(item, destination)
            print(f'Updated global/{item.name}')
    update_skills_tree(source_root / 'skills', DATA_ROOT / 'skills')


def semver_tuple(tag):
    """(major, minor, patch) from a 'v1.2.3'-style tag; non-digits stop each part."""
    parts = []
    for part in tag.lstrip('v').split('.')[:3]:
        digits = ''
        for char in part:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits) if digits else 0)
    parts += [0] * (3 - len(parts))
    return tuple(parts)


def latest_github_release():
    """{'tag_name', 'body', 'html_url'} for the repo's latest release, or None.

    A network or parsing failure returns None; callers treat this path as
    best-effort and never let it block or fail a session.
    """
    import urllib.request
    url = os.environ.get('MURPIANO_DX_RELEASE_API',
                         f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest')
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read())
        return {'tag_name': data['tag_name'], 'body': data.get('body') or '',
                'html_url': data.get('html_url', '')}
    except (OSError, ValueError, KeyError):
        return None


def resolve_release_tag(tag):
    """Pass an explicit tag through; resolve 'latest' via the GitHub API."""
    if tag != 'latest':
        return tag
    release = latest_github_release()
    if release is None:
        raise RuntimeError(f'Could not resolve the latest release of {GITHUB_REPO}.')
    return release['tag_name']


@contextmanager
def fetch_release_checkout(tag):
    """A shallow clone of this repo at `tag`, removed when the block exits."""
    tag = resolve_release_tag(tag)
    remote = os.environ.get('MURPIANO_DX_REMOTE', f'https://github.com/{GITHUB_REPO}.git')
    with tempfile.TemporaryDirectory(prefix='murpiano-dx-fetch-') as tmp:
        result = subprocess.run(
            ['git', 'clone', '--quiet', '--depth', '1', '--branch', tag, remote, tmp],
            text=True, capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(f'Could not fetch {GITHUB_REPO}@{tag}: '
                               f'{result.stderr.strip() or "git clone failed"}')
        yield Path(tmp)


def check_for_update():
    """A one-line notice for the agent when a newer release exists, else None.

    Best-effort: without a recorded local version, or on any network/parsing
    failure, returns None silently. Never raises.
    """
    version_file = DATA_ROOT / VERSION_MARKER
    if not version_file.is_file():
        return None
    current = version_file.read_text().strip()
    if not current:
        return None
    release = latest_github_release()
    if release is None:
        return None
    latest = release['tag_name']
    if semver_tuple(latest) <= semver_tuple(current):
        return None
    notes = release['body'].strip()
    summary = notes[:400] + ('…' if len(notes) > 400 else '')
    return (
        f'murpiano-dx {latest} is available (this workspace is on {current}). '
        'Tell the user what changed and ask whether to update before continuing; '
        f'do not update without asking. Summary:\n{summary}\n'
        f'Full notes: {release["html_url"]}\n'
        f'To update: bash sync.sh update --fetch {latest}'
    )


def ensure_workspace(update_runtime=False):
    """Create the editable local workspace without overwriting user files."""
    bootstrap_workspace_files(update_runtime=update_runtime)
    (DATA_ROOT / 'config').mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / 'rules').mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / 'logs').mkdir(parents=True, exist_ok=True)
    STORE.mkdir(parents=True, exist_ok=True)
    machine = DATA_ROOT / 'config' / 'machine.json'
    if not machine.exists():
        machine.write_text(json.dumps({
            'git_name': os.environ.get('GIT_NAME', ''),
            'git_email': os.environ.get('GIT_EMAIL', ''),
            'github_owner': os.environ.get('GITHUB_OWNER', ''),
        }, indent=2) + '\n')
    elif update_runtime:
        # Earlier local checks could create an empty identity before onboarding.
        # Explicit setup fills missing values without replacing personal settings.
        values = json.loads(machine.read_text())
        if not isinstance(values, dict):
            raise RuntimeError(f'Expected a JSON object in {machine}; settings left unchanged.')
        updated = dict(values)
        for key, env_name in [('git_name', 'GIT_NAME'), ('git_email', 'GIT_EMAIL'),
                              ('github_owner', 'GITHUB_OWNER')]:
            if not updated.get(key) and os.environ.get(env_name):
                updated[key] = os.environ[env_name]
        if updated != values:
            machine.write_text(json.dumps(updated, indent=2) + '\n')
    defaults = SOURCE_ROOT / 'defaults'
    for group in ('rules',):
        source = defaults / group
        target = DATA_ROOT / group
        if source.is_dir():
            for item in source.iterdir():
                destination = target / item.name
                if not destination.exists():
                    shutil.copy2(item, destination)


def ensure_agent_entrypoint():
    """Prepare the shared entry point during setup, preserving user instructions."""
    instructions = DATA_ROOT / 'AGENTS.md'
    if not instructions.exists():
        text = (DATA_ROOT / 'global/agent-rules.md').read_text()
        for token, value in [('{{ROOT}}', str(DATA_ROOT)),
                             ('{{DATA_ROOT}}', str(DATA_ROOT)),
                             ('{{SYNC}}', 'bash ' + shlex.quote(str(DATA_ROOT / 'sync.sh')))]:
            text = text.replace(token, value)
        instructions.write_text('# murpiano-dx\n\n' + text)


def initialize_workspace_repo():
    """Make the local workspace a Git repository, preserving existing files."""
    if (DATA_ROOT.resolve() == SOURCE_ROOT.resolve()
            and not (DATA_ROOT / WORKSPACE_MARKER).is_file()):
        return
    existing = (DATA_ROOT / '.git').exists()
    if not existing:
        result = subprocess.run(['git', 'init', '-b', 'main'], cwd=DATA_ROOT,
                                text=True, capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Could not initialize workspace Git')
    prepare_local_files(DATA_ROOT)
    for name, env_name in [('user.name', 'GIT_NAME'), ('user.email', 'GIT_EMAIL')]:
        value = os.environ.get(env_name)
        if value and not git(DATA_ROOT, 'config', '--get', name, check=False):
            subprocess.run(['git', '-C', str(DATA_ROOT), 'config', name, value], check=True)
    if existing:
        return
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
    completed = synchronize(DATA_ROOT)
    if (completed and (DATA_ROOT / WORKSPACE_MARKER).is_file()
            and git(DATA_ROOT, 'remote', 'get-url', 'origin', check=False)):
        print('Workspace state pushed; remote updates merged.')


def select_template(kind):
    relative = TEMPLATE_LOCATIONS[kind]
    # Read old personal paths until explicit setup migrates them. Template lookup
    # itself is read-only and must not replace an existing personal choice.
    for path in (DATA_ROOT / 'templates' / relative.name,
                 DATA_ROOT / relative, SOURCE_ROOT / relative):
        if path.is_file():
            return path
    raise RuntimeError(f'Template not found: {relative}')


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


PRECOMMIT_MARKER = '# murpiano-dx: agent-trace pre-commit scan (skills/repo-cleanup)'


def install_precommit_hook(project, key):
    """Install the agent-trace pre-commit scanner for a tracked project.

    Idempotent: skipped if already installed, left alone if the project has
    its own unrelated pre-commit hook.
    """
    path = git_path(project, 'hooks') / 'pre-commit'
    if path.exists() or path.is_symlink():
        if path.is_file() and PRECOMMIT_MARKER in path.read_text():
            return
        print(f'{key}: pre-commit hook already exists; not replaced. Agent-trace scan: '
              f'bash {ACTIVE_ROOT}/skills/repo-cleanup/pre-commit-hook.sh')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '#!/usr/bin/env bash\n' + PRECOMMIT_MARKER + '\n'
        f'exec bash "{ACTIVE_ROOT}/skills/repo-cleanup/pre-commit-hook.sh"\n'
    )
    path.chmod(0o755)
    print(f'{key}: pre-commit hook installed. Every commit is scanned for agent traces and '
          f'secrets before it is made (skills/repo-cleanup/policy.md); a false positive '
          f'commits with --no-verify.')


COMMITMSG_MARKER = '# murpiano-dx: agent-trace commit-msg scan (skills/repo-cleanup)'


def install_commitmsg_hook(project, key):
    """Wrap an existing commit-msg hook with an agent-trace scan of the message text.

    pre-commit-hook.sh cannot see the commit message (git finalizes it only
    after pre-commit runs); this is the one check that belongs on commit-msg
    instead. Only ever wraps an ALREADY-present hook -- kysaro's own (see
    skills/repo-init/kysaro.md) or a custom one -- never creates one from a
    blank project, so install order relative to kysaro's own setup never
    matters: whichever sets up commit-msg first, this wraps it on the next
    connect. Idempotent: skipped if already wrapped. Also skipped if the
    existing hook is not executable -- that is a setup gap to report
    (kysaro_gaps), not one to silently fix by making it active.
    """
    path = git_path(project, 'hooks') / 'commit-msg'
    if not path.is_file() or path.is_symlink() or not os.access(path, os.X_OK):
        return
    text = path.read_text()
    if COMMITMSG_MARKER in text:
        return
    original = path.with_name('commit-msg.murpiano-dx-original')
    if not original.exists():
        shutil.copy2(path, original)
        original.chmod(0o755)
    path.write_text(
        '#!/usr/bin/env bash\n' + COMMITMSG_MARKER + '\n'
        f'"{original}" "$1" || exit 1\n'
        f'exec bash "{ACTIVE_ROOT}/skills/repo-cleanup/commit-msg-hook.sh" "$1"\n'
    )
    path.chmod(0o755)
    print(f'{key}: commit-msg hook wrapped with an agent-trace scan of the message text '
          f'(skills/repo-cleanup/policy.md); the previous hook still runs first.')


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
    original = active.with_name('commit-msg.murpiano-dx-original')
    # install_commitmsg_hook wraps commit-msg behind our own text; 'kysaro' then
    # lives in the preserved original, not the active file.
    active_text = (active.read_text() if active.is_file() else '') + (
        original.read_text() if original.is_file() else '')
    hooked = active.is_file() and os.access(active, os.X_OK) and 'kysaro' in active_text
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
        print('Local Git is ready. Ask whether to create a GitHub repository, then choose private or public.')
        print('After approval: gh repo create --private (or --public) --source=. --remote=origin')
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
        install_precommit_hook(project, key)
        install_commitmsg_hook(project, key)
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
    parser.add_argument('mode', choices=['init', 'start', 'end', 'link', 'workspace', 'update', 'template', 'check-readme'], nargs='?', default='start')
    parser.add_argument('project', type=Path, nargs='?', default=Path.cwd())
    parser.add_argument('--kind', choices=['readme', 'release', 'description'])
    parser.add_argument('--template', type=Path, help='Explicit README template (check-readme only)')
    parser.add_argument('--project-kind', choices=['app', 'framework', 'npm-package', 'personal-brand'],
                        help='Project kind for check-readme: sections tagged for other kinds become optional')
    parser.add_argument('--local', action='store_true', help='Check project state without network sync (start only)')
    parser.add_argument('--kysaro', choices=['approved', 'declined', 'enabled'],
                        help='Record the owner decision or verify completed setup (init only)')
    parser.add_argument('--fetch', metavar='TAG',
                        help='With update: fetch TAG ("latest" or "vX.Y.Z") from GitHub '
                             'instead of using this checkout as the source')
    args = parser.parse_args()
    if args.template and args.mode != 'check-readme':
        parser.error('--template is only available with check-readme')
    if args.project_kind and args.mode != 'check-readme':
        parser.error('--project-kind is only available with check-readme')
    if args.fetch and args.mode != 'update':
        parser.error('--fetch is only available with update')
    if args.mode == 'check-readme':
        template = args.template or select_template('readme')
        checker = SOURCE_ROOT / 'skills/repo-readme/scripts/check_readme.py'
        command = [sys.executable, str(checker), str(args.project / 'README.md'),
                   '--template', str(template)]
        if args.project_kind:
            command += ['--kind', args.project_kind]
        sys.exit(subprocess.call(command))
    if args.local and args.mode != 'start':
        parser.error('--local is only available with start')
    if args.mode == 'template':
        if not args.kind:
            parser.error('template requires --kind readme, release, or description')
        print(select_template(args.kind))
        return
    if args.mode == 'update':
        if args.fetch:
            with fetch_release_checkout(args.fetch) as fetched:
                update_workspace(source_root=fetched)
        else:
            update_workspace()
        print(f'Local workspace updated: {DATA_ROOT}')
        return
    ensure_workspace(update_runtime=(args.mode == 'workspace'))
    load_machine_config()
    if args.mode == 'workspace':
        ensure_agent_entrypoint()
    initialize_workspace_repo()
    if args.mode == 'start' and not args.local:
        notice = check_for_update()
        if notice:
            print(notice)
        try:
            sync_workspace()
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f'Workspace sync pending; local data is available: {error}', file=sys.stderr)
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
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
