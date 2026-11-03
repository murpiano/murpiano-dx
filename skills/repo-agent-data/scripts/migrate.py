#!/usr/bin/env python3
"""Preview or migrate project agent metadata without committing or pushing."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if (ROOT / '.murpiano-dx-workspace').is_file():
    os.environ.setdefault('MURPIANO_DX_DATA_DIR', str(ROOT))
spec = importlib.util.spec_from_file_location('dx_sync', ROOT / 'sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

# These are metadata filenames, not evidence that arbitrary product text is a trace.
EXPLICIT_ONLY = {'memory-bank', 'docs/superpowers', '.mcp.json'}


def git(project, *args):
    result = subprocess.run(['git', '--literal-pathspecs', '-C', str(project), *args],
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Git command failed')
    return result.stdout


def snapshot(path):
    """Fingerprint a file tree without following links or nested repositories."""
    result = {}

    def visit(item, relative):
        info = item.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f'Review symbolic link before migration: {item}')
        if stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256()
            with item.open('rb') as handle:
                for chunk in iter(lambda: handle.read(65536), b''):
                    digest.update(chunk)
            result[relative] = {'sha256': digest.hexdigest(), 'mode': mode}
        elif stat.S_ISDIR(info.st_mode):
            result[relative] = {'directory': True, 'mode': mode}
            for child in sorted(item.iterdir()):
                if child.name == '.git':
                    raise RuntimeError(f'Nested Git repository must stay in place: {item}')
                visit(child, str(child.relative_to(path)))
        else:
            raise RuntimeError(f'Unsupported metadata file: {item}')

    visit(path, '.')
    return result


def safe_path(project, name):
    relative = Path(name)
    if (relative.is_absolute() or '..' in relative.parts or not relative.parts
            or '\n' in name or '\r' in name):
        raise RuntimeError(f'Expected a project-relative metadata path: {name}')
    reserved = ('.git', '.kysaro', 'node_modules', '.github/workflows')
    if any(relative == Path(p) or Path(p) in relative.parents or relative in Path(p).parents
           for p in reserved):
        raise RuntimeError(f'Project tooling must stay in place: {name}')
    for parent in relative.parents:
        if (project / parent).is_symlink():
            raise RuntimeError(f'Review symbolic parent before migration: {project / parent}')
    return relative


def candidates(project, extra):
    names = set(extra)
    rules = (ROOT / 'global/gitignore-agents').read_text().splitlines()
    for rule in rules:
        name = rule.removeprefix('/')
        if rule.startswith('/') and name not in EXPLICIT_ONLY:
            names.update(str(p.relative_to(project)) for p in project.glob(name))
    paths = sorted({safe_path(project, name) for name in names}, key=lambda p: p.parts)
    # A selected directory already includes its descendants.
    return [p for p in paths if not any(parent in paths for parent in p.parents)]


def plan(project, data, extra):
    items = []
    for relative in candidates(project, extra):
        source = project / relative
        target = data / 'files' / relative
        if relative == Path('memory'):
            target = data / 'memory'
        for parent in (target, *target.parents):
            if parent.is_symlink():
                raise RuntimeError(f'Review workspace symbolic link before migration: {parent}')
        tracked = git(project, 'ls-files', '-z', '--', str(relative)).strip('\0').split('\0')
        tracked = [p for p in tracked if p]
        staged = git(project, 'diff', '--cached', '--name-only', '--', str(relative))
        if staged and (tracked or not source.is_symlink()):
            raise RuntimeError(f'Preserve or commit staged edits before migration: {relative}')
        if source.is_symlink():
            if source.resolve() != target.resolve() or not target.exists():
                raise RuntimeError(f'Conflicting or broken link; left unchanged: {source}')
            tree = snapshot(target)
            linked = True
        else:
            if not source.exists():
                raise RuntimeError(f'Metadata path does not exist: {source}')
            tree = snapshot(source)
            linked = False
            if target.exists() and snapshot(target) != tree:
                raise RuntimeError(f'Destination differs; merge manually: {target}')
        items.append({'source': str(relative), 'stored': str(target.relative_to(data)),
                      'tracked': tracked, 'snapshot': tree, 'linked': linked})
    return items


def copy_verified(source, target, expected):
    if target.exists():
        if snapshot(target) != expected:
            raise RuntimeError(f'Destination changed during migration: {target}')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.agent-data-', dir=target.parent) as folder:
        staged = Path(folder) / 'data'
        if source.is_dir():
            shutil.copytree(source, staged)
        else:
            shutil.copy2(source, staged)
        if snapshot(staged) != expected:
            raise RuntimeError(f'Copy verification failed; source preserved: {source}')
        if target.exists():
            raise RuntimeError(f'Destination appeared during migration: {target}')
        staged.rename(target)


def apply(project, data, items):
    report = data / 'agent-data-migration.json'
    previous = json.loads(report.read_text()) if report.exists() else {'paths': {}}
    for item in items:
        if not item['linked']:
            copy_verified(project / item['source'], data / item['stored'], item['snapshot'])
        if item['source'] not in previous['paths'] or not item['linked']:
            previous['paths'][item['source']] = {
                key: value for key, value in item.items() if key != 'linked'}

    def save_report(status):
        previous['status'] = status
        temporary = report.with_suffix('.tmp')
        temporary.write_text(json.dumps(previous, indent=2) + '\n')
        temporary.replace(report)

    # Persist recovery information before changing local files or the Git index.
    save_report('prepared')
    changed = []
    exclude = sync.git_path(project, 'info/exclude')
    old_exclude = exclude.read_bytes() if exclude.exists() else None
    backups = Path(tempfile.mkdtemp(prefix='murpiano-dx-migrate-',
                                    dir=sync.git_path(project, '')))
    try:
        sync.exclude_agent_files(project)
        for item in items:
            source, target = project / item['source'], data / item['stored']
            if not item['linked']:
                if snapshot(source) != item['snapshot'] or snapshot(target) != item['snapshot']:
                    raise RuntimeError(f'Data changed during migration; retry: {source}')
                backup = backups / str(len(changed))
                source.rename(backup)
                changed.append((item, backup))
                source.symlink_to(target, target_is_directory=target.is_dir())
            rule = '/' + item['source']
            if rule not in exclude.read_text().splitlines():
                # Escape gitignore metacharacters for explicitly selected filenames.
                escaped = ''.join('\\' + c if c in '\\*?[]#! ' else c for c in rule)
                with exclude.open('a') as handle:
                    handle.write(escaped + '\n')
        tracked = [item['source'] for item in items if item['tracked']]
        if tracked:
            git(project, 'rm', '-r', '--cached', '--', *tracked)
    except Exception:
        for item, backup in reversed(changed):
            source, target = project / item['source'], data / item['stored']
            if source.is_symlink():
                source.unlink()
            backup.rename(source)
        if old_exclude is None:
            exclude.unlink(missing_ok=True)
        else:
            exclude.write_bytes(old_exclude)
        shutil.rmtree(backups)
        raise
    shutil.rmtree(backups)
    save_report('complete')
    print(f'Verified agent data: {data}')
    print('Local access preserved; removals staged. No commit, push, or history rewrite.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path, nargs='?', default=Path.cwd())
    parser.add_argument('--path', action='append', default=[], help='Additional metadata path')
    parser.add_argument('--apply', action='store_true', help='Apply the reviewed migration')
    args = parser.parse_args()
    project = Path(git(args.project.resolve(), 'rev-parse', '--show-toplevel').strip())
    sync.load_machine_config()
    if not os.environ.get('GITHUB_OWNER'):
        raise RuntimeError('Run murpiano-dx setup to configure the GitHub owner.')
    if project == ROOT or sync.DATA_ROOT.resolve().is_relative_to(project):
        raise RuntimeError('Migrate a connected project, not the framework or workspace.')
    key = sync.project_key(git(project, 'remote', 'get-url', 'origin').strip())
    if not key or sync.load_workflow(key) is None:
        raise RuntimeError('Connect this project with repo-init before migrating agent data.')
    data = sync.STORE / key
    if args.apply:
        with sync.store_lock():
            items = plan(project, data, args.path)
            apply(project, data, items)
    else:
        items = plan(project, data, args.path)
        for item in items:
            state = 'already linked' if item['linked'] else 'move and link'
            print(f"{item['source']} -> {data / item['stored']} | {state} | "
                  f"{len(item['tracked'])} tracked files")
        print('Preview only. Review contents, then repeat with --apply.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
