#!/usr/bin/env python3
"""One-off extraction: project-profile.md's table + each governing skill's
real description/default/Basis date, into docs/demo-data.json for the
GitHub Pages demo. Not part of the shipped framework - a snapshot builder.
Run from the repo root: python3 scripts/build-demo-data.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / 'skills/project-profile/templates/project-profile.md'
SKILLS = ROOT / 'skills'

SECTION_RE = re.compile(r'^## (\d+)\. (.+)$')
ROW_RE = re.compile(r'^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|$')
BASIS_DATE_RE = re.compile(r'## Basis \(checked (\d{4}-\d{2}-\d{2})\)')
DEFAULT_LINE_RE = re.compile(
    r'^#+\s*(?:The )?[Dd]efault(?:\s+\w+)?:\s*(.+)$|\*\*Default:?\*\*\s*(.+)',
    re.MULTILINE)
FRONT_DESC_RE = re.compile(r'^description:\s*(.+)$', re.MULTILINE)


def parse_profile():
    sections = []
    current = None
    for line in PROFILE.read_text().splitlines():
        heading = SECTION_RE.match(line)
        if heading:
            current = {'number': heading.group(1), 'name': heading.group(2), 'rows': []}
            sections.append(current)
            continue
        row = ROW_RE.match(line)
        if not row or current is None:
            continue
        field, value, governed = row.groups()
        if field in ('Field', '---'):
            continue
        skills = [s.strip('` ') for s in governed.split('+')] if governed else []
        current['rows'].append({'field': field, 'value': value, 'skills': skills})
    return sections


def skill_detail(name):
    skill_dir = SKILLS / name
    skill_md = skill_dir / 'SKILL.md'
    rules_md = skill_dir / 'rules.md'
    if not skill_md.is_file():
        return None
    text = skill_md.read_text()
    rules_text = rules_md.read_text() if rules_md.is_file() else ''
    description = ''
    m = FRONT_DESC_RE.search(text)
    if m:
        description = m.group(1).strip()
    dates = BASIS_DATE_RE.findall(text) + BASIS_DATE_RE.findall(rules_text)
    basis_date = max(dates) if dates else None
    raw_matches = DEFAULT_LINE_RE.findall(rules_text) + DEFAULT_LINE_RE.findall(text)
    defaults = [heading or bold for heading, bold in raw_matches]
    default_line = re.sub(r'[*`#]', '', defaults[0]).strip() if defaults else None
    if default_line and len(default_line) > 240:
        default_line = default_line[:237] + '...'
    return {
        'name': name,
        'description': description,
        'basis_date': basis_date,
        'default': default_line,
        'path': f'skills/{name}/SKILL.md',
    }


def main():
    sections = parse_profile()
    skill_names = sorted({s for section in sections for row in section['rows'] for s in row['skills']})
    skills = {name: skill_detail(name) for name in skill_names}
    skills = {k: v for k, v in skills.items() if v}
    out = {'sections': sections, 'skills': skills}
    out_path = ROOT / 'docs/demo-data.json'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    total_rows = sum(len(s['rows']) for s in sections)
    print(f'{len(sections)} sections, {total_rows} rows, {len(skills)} skills -> {out_path}')


if __name__ == '__main__':
    main()
