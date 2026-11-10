#!/usr/bin/env python3
"""List every '## Basis (checked YYYY-MM-DD)' section under skills/, with
its age in days, so a full-sweep refresh knows what to re-check."""
import argparse
from datetime import date
from pathlib import Path
import re
import sys

BASIS_RE = re.compile(r'^## Basis \(checked (\d{4}-\d{2}-\d{2})\)', re.M)
STALE_DAYS = 30


def find_basis_sections(skills_root):
    results = []
    for md_file in sorted(skills_root.rglob('*.md')):
        text = md_file.read_text()
        for match in BASIS_RE.finditer(text):
            checked = date.fromisoformat(match.group(1))
            age_days = (date.today() - checked).days
            results.append((md_file, checked, age_days))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument('--skills-root', type=Path, default=default_root)
    parser.add_argument('--stale-days', type=int, default=STALE_DAYS,
                         help=f'age in days past which a Basis is reported stale (default {STALE_DAYS})')
    args = parser.parse_args()

    results = find_basis_sections(args.skills_root)
    if not results:
        print('No "## Basis (checked ...)" sections found under skills/.')
        return 0

    results.sort(key=lambda r: -r[2])
    stale = [r for r in results if r[2] > args.stale_days]
    fresh = [r for r in results if r[2] <= args.stale_days]

    if stale:
        print(f'Stale (older than {args.stale_days} days) — re-research before reusing:')
        for md_file, checked, age_days in stale:
            print(f'  {md_file.relative_to(args.skills_root.parent)}: checked {checked} ({age_days} days ago)')
    if fresh:
        print('Fresh — safe to apply directly, telling the user the checked date:')
        for md_file, checked, age_days in fresh:
            print(f'  {md_file.relative_to(args.skills_root.parent)}: checked {checked} ({age_days} days ago)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
