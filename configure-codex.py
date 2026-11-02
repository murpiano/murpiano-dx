#!/usr/bin/env python3
"""Connect shared skills and an idempotent instruction block; never configure Claude."""
from pathlib import Path
import os
import sys
import shlex

root = Path(sys.argv[1]).resolve()
home = Path.home()
instructions = home / '.codex' / 'AGENTS.md'
# Follow the existing Windows/WSL single-source link.
if instructions.is_symlink():
    instructions = instructions.resolve(strict=True)
begin = '<!-- >>> murpiano-dx -->'
end = '<!-- <<< murpiano-dx -->'
text = instructions.read_text() if instructions.exists() else ''
if (text.count(begin) != text.count(end) or text.count(begin) > 1 or
        (begin in text and text.index(begin) > text.index(end))):
    raise SystemExit('Invalid murpiano-dx instruction markers; file left untouched')
if begin in text:
    prefix, rest = text.split(begin, 1)
    _, suffix = rest.split(end, 1)
    text = prefix + suffix
skill_dirs = [home / '.agents' / 'skills']
if str(instructions).startswith('/mnt/'):
    skill_dirs.append(instructions.parent.parent / '.agents' / 'skills')
for folder in dict.fromkeys(skill_dirs):
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
command = 'bash ' + shlex.quote(str(root / 'sync.sh'))
block = (root / 'global' / 'agent-rules.md').read_text()
data_root = Path(os.environ.get('MURPIANO_DX_DATA_DIR', Path.home() / '.murpiano-dx')).expanduser()
block = (block.replace('{{SYNC}}', command)
              .replace('{{ROOT}}', str(root))
              .replace('{{DATA_ROOT}}', str(data_root)))
instructions.parent.mkdir(parents=True, exist_ok=True)
instructions.write_text(text.rstrip() + '\n\n' + begin + '\n' + block.rstrip() + '\n' + end + '\n')
# Retire the exact global Husky guard shipped by the previous setup. Other code stays.
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
        remaining = previous.replace(legacy_guard, '', 1)
        husky_init.write_text(remaining)
        print('Removed legacy murpiano-dx Husky guard; other initialization preserved')
    elif 'repo-cleanup/pre-commit-hook.sh' in previous:
        print(f'Review legacy guard in {husky_init}: customized initialization left unchanged',
              file=sys.stderr)
print(f'Codex skills and instructions connected: {instructions}')
