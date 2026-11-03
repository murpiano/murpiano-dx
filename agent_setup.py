#!/usr/bin/env python3
"""Detect supported coding agents and connect their shared workflow instructions."""
from pathlib import Path
import os
import shlex
import shutil
import sys

BEGIN = '<!-- >>> murpiano-dx -->'
END = '<!-- <<< murpiano-dx -->'


def agent_profiles(home):
    return (
        ('codex', 'Codex', 'CODEX_HOME', home / '.codex', 'AGENTS.md'),
        ('claude', 'Claude Code', 'CLAUDE_CONFIG_DIR', home / '.claude', 'CLAUDE.md'),
    )


def instruction_plan(path, block):
    # Preserve linked Windows/WSL instruction files and all text outside our block.
    if path.is_symlink():
        path = path.resolve(strict=True)
    text = path.read_text() if path.exists() else ''
    if (text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1 or
            (BEGIN in text and text.index(BEGIN) > text.index(END))):
        raise RuntimeError(f'Invalid murpiano-dx instruction markers: {path}; file left untouched')
    managed = BEGIN + '\n' + block.rstrip() + '\n' + END
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END)
        updated = text[:start] + managed + text[finish:]
    else:
        separator = '' if not text or text.endswith('\n\n') else ('\n' if text.endswith('\n') else '\n\n')
        updated = text + separator + managed + '\n'
    return path, updated


def configure(root, only=None):
    home = Path.home()
    data = Path(os.environ.get('MURPIANO_DX_DATA_DIR', root)).expanduser().resolve()
    block = (root / 'global/agent-rules.md').read_text()
    for token, value in [('{{ROOT}}', str(root)), ('{{DATA_ROOT}}', str(data)),
                         ('{{SYNC}}', 'bash ' + shlex.quote(str(root / 'sync.sh')))]:
        block = block.replace(token, value)
    plans = []
    folders = [home / '.agents/skills']
    for command, label, variable, default, filename in agent_profiles(home):
        configured = os.environ.get(variable)
        profile = Path(configured).expanduser() if configured else default
        if only is not None:
            if command not in only:
                continue
        elif not (configured or profile.is_dir() or shutil.which(command)):
            continue
        path = profile / filename
        if command == 'codex':
            override = profile / 'AGENTS.override.md'
            if override.is_symlink() and not override.exists():
                raise RuntimeError(f'Broken agent instruction link: {override}')
            if override.is_file() and override.stat().st_size:
                path = override
        # Validate every detected adapter before modifying any global instructions.
        target, updated = instruction_plan(path, block)
        plans.append((label, target, updated))
        if command == 'claude':
            folders.append(profile / 'skills')
        elif str(target).startswith('/mnt/'):
            folders.append(target.parent.parent / '.agents/skills')
    connect_skills(root, folders)
    for label, target, updated in plans:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != updated:
            target.write_text(updated)
        print(f'{label} connected: {target}')
    retire_legacy_guard(home)
    print(f'Agent entry point: {root / "AGENTS.md"}')
    if not plans:
        print('No supported agent detected. Point your agent to the shared entry point.')


def connect_skills(root, folders):
    for folder in dict.fromkeys(folders):
        folder.mkdir(parents=True, exist_ok=True)
        retired = folder / 'repo-cleanup'
        if retired.is_symlink() and retired.resolve() == root / 'skills/repo-cleanup':
            retired.unlink()
        for skill in sorted((root / 'skills').iterdir()):
            if not (skill / 'SKILL.md').is_file():
                continue
            link = folder / skill.name
            if link.is_symlink():
                if link.resolve() == skill:
                    continue
                print(f'Skip conflicting link: {link}', file=sys.stderr)
            elif link.exists():
                print(f'Skip existing skill: {link}', file=sys.stderr)
            else:
                link.symlink_to(skill, target_is_directory=True)


def retire_legacy_guard(home):
    # Retire only the exact global guard shipped by the previous setup.
    legacy_guard = '''# Sourced by husky before every hook. Runs the murpiano-dx pre-commit guard in kysaro,
# where husky owns the pre-commit hook and sync.sh does not replace it.
if [ "$(basename "$0")" = pre-commit ] &&
  git remote get-url origin 2>/dev/null | grep -qE 'murpiano/kysaro(\\.git)?$'; then
  bash "$HOME/projects/murpiano-dx/skills/repo-cleanup/pre-commit-hook.sh" || exit 1
fi
'''
    husky_init = home / '.config/husky/init.sh'
    if husky_init.is_file() and not husky_init.is_symlink():
        previous = husky_init.read_text()
        if legacy_guard in previous:
            husky_init.write_text(previous.replace(legacy_guard, '', 1))
            print('Removed legacy murpiano-dx Husky guard; other initialization preserved')
        elif 'repo-cleanup/pre-commit-hook.sh' in previous:
            print(f'Review legacy guard in {husky_init}: customized initialization left unchanged',
                  file=sys.stderr)


if __name__ == '__main__':
    try:
        configure(Path(sys.argv[1]).resolve())
    except (OSError, RuntimeError) as error:
        print(f'murpiano-dx: {error}', file=sys.stderr)
        sys.exit(1)
