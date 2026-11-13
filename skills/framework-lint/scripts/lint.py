#!/usr/bin/env python3
"""Check murpiano-dx's own skills/ for broken cross-references: dead
relative links, skills missing from any GRAPH.md, and SKILL.md "Governs"
lines that disagree with project-profile.md's "Governed by" column."""
import argparse
from pathlib import Path
import re
import sys

LINK_RE = re.compile(r'\[[^\]]*\]\((?!https?://|mailto:)([^)#]+)(?:#[^)]*)?\)')
BACKTICK_RE = re.compile(r'`([a-z][a-z0-9-]*)`')
GOVERNS_RE = re.compile(r'Governs `project-profile\.md` fields:\s*(.+?)(?:\n\s*\n|\Z)', re.S)
TABLE_ROW_RE = re.compile(r'^\|(.+)\|\s*$')


def skill_dirs(skills_root):
    return sorted(p for p in skills_root.iterdir() if p.is_dir() and (p / 'SKILL.md').is_file())


def check_frontmatter(skill_dir, errors):
    text = (skill_dir / 'SKILL.md').read_text()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        errors.append(f'{skill_dir.name}/SKILL.md: missing --- frontmatter block')
        return
    front = m.group(1)
    name_m = re.search(r'^name:\s*(\S+)', front, re.M)
    if not name_m:
        errors.append(f'{skill_dir.name}/SKILL.md: frontmatter missing name:')
    elif name_m.group(1) != skill_dir.name:
        errors.append(f'{skill_dir.name}/SKILL.md: frontmatter name {name_m.group(1)!r} '
                       f'does not match directory name')
    if not re.search(r'^description:\s*\S', front, re.M):
        errors.append(f'{skill_dir.name}/SKILL.md: frontmatter missing description:')


def in_templates_dir(md_file, skills_root):
    """A file under any templates/ directory describes a future project's
    own structure, not this framework's — its relative links are not
    resolvable here and are not checked."""
    return 'templates' in md_file.relative_to(skills_root).parts[:-1]


FENCE_RE = re.compile(r'```.*?```', re.S)
INLINE_CODE_RE = re.compile(r'`[^`\n]*`')


def strip_code(text):
    """Blank out fenced and inline code spans so a literal example of
    markdown link syntax inside backticks isn't treated as a real link."""
    text = FENCE_RE.sub(lambda m: ' ' * len(m.group(0)), text)
    return INLINE_CODE_RE.sub(lambda m: ' ' * len(m.group(0)), text)


def check_links(md_file, skills_root, framework_root, errors):
    if in_templates_dir(md_file, skills_root):
        return
    text = strip_code(md_file.read_text())
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            continue
        if '<' in target or '>' in target:
            continue  # a {{placeholder}}-style path, not a real file
        resolved = (md_file.parent / target).resolve()
        if not resolved.exists():
            rel = md_file.relative_to(framework_root)
            errors.append(f'{rel}: broken link -> {target}')


def check_orphan_skills(skills_root, errors):
    dirs = {p.name for p in skill_dirs(skills_root)}
    mentioned = set()
    for graph in skills_root.rglob('GRAPH.md'):
        mentioned |= set(BACKTICK_RE.findall(graph.read_text()))
    for name in sorted(dirs - mentioned):
        errors.append(f'{name}: skill exists but is not named (in backticks) in any GRAPH.md '
                       f'— unreachable from the overview')


SECTION_HEADING_RE = re.compile(r'^##\s+\d+\.\s*(.+?)\s*$')


def parse_profile_table(profile_md_text):
    """(section, field name) -> set of skill names from its "Governed by" column.

    Section-scoped because the same field name appears in more than one
    section (e.g. "Language" in both Frontend and Backend) — a flat
    field-name key would silently merge two unrelated rows.
    """
    rows = {}
    section = None
    for line in profile_md_text.splitlines():
        heading = SECTION_HEADING_RE.match(line)
        if heading:
            section = heading.group(1)
            continue
        m = TABLE_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split('|')]
        if len(cells) < 3:
            continue
        field = cells[0]
        if not field or field == 'Field' or set(field) <= {'-', ':'}:
            continue
        governed = cells[2]
        names = set(BACKTICK_RE.findall(governed))
        if names:
            rows[(section, field)] = names
    return rows


def parse_governs_claims(skills_root):
    """(section, field name) -> set of skill names claiming to govern it.

    A claim like "Git workflow → Branching model, Commit convention" names
    the section once and lists several fields under it; a part with its own
    "→" (e.g. "..., Frontend → Language") switches the current section for
    every part after it. Section-scoped for the same reason the table side
    is — "Language" means something different in Frontend vs. Backend.
    """
    claimed = {}
    for skill_dir in skill_dirs(skills_root):
        text = (skill_dir / 'SKILL.md').read_text()
        match = GOVERNS_RE.search(text)
        if not match:
            continue
        section = None
        for part in re.split(r',| and ', match.group(1)):
            part = re.sub(r'\s+', ' ', part)
            if '→' in part:
                section, field = part.rsplit('→', 1)
                section = section.strip().rstrip('.').strip()
            else:
                field = part
            field = field.strip().rstrip('.').strip()
            if field:
                claimed.setdefault((section, field), set()).add(skill_dir.name)
    return claimed


def check_governs(skills_root, errors):
    profile_md = skills_root / 'project-profile' / 'templates' / 'project-profile.md'
    if not profile_md.is_file():
        return
    table = parse_profile_table(profile_md.read_text())
    claimed = parse_governs_claims(skills_root)

    for (section, field), skills in claimed.items():
        label = f'{section} → {field}' if section else field
        table_skills = table.get((section, field), set())
        if not table_skills:
            errors.append(f'project-profile.md: field {label!r} is claimed by '
                           f'{sorted(skills)} but has no "Governed by" entry in the table')
        elif not (skills & table_skills):
            errors.append(f'project-profile.md: field {label!r} is "Governed by" '
                           f'{sorted(table_skills)} in the table but claimed by '
                           f'{sorted(skills)} instead — these should name each other')
    for (section, field), table_skills in table.items():
        label = f'{section} → {field}' if section else field
        for skill in table_skills:
            if skill not in claimed.get((section, field), set()):
                errors.append(f'{skill}/SKILL.md: project-profile.md marks it as governing '
                               f'{label!r}, but this skill has no matching "Governs" line '
                               f'naming that field')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument('--skills-root', type=Path, default=default_root,
                         help='Path to the skills/ directory (default: this script\'s own)')
    args = parser.parse_args()
    skills_root = args.skills_root
    framework_root = skills_root.parent

    errors = []
    for skill_dir in skill_dirs(skills_root):
        check_frontmatter(skill_dir, errors)
    for md_file in skills_root.rglob('*.md'):
        check_links(md_file, skills_root, framework_root, errors)
    check_orphan_skills(skills_root, errors)
    check_governs(skills_root, errors)

    if errors:
        for error in sorted(errors):
            print(error, file=sys.stderr)
        print(f'{len(errors)} problem(s) found.', file=sys.stderr)
        return 1
    print('Framework lint passed: no broken links, no orphan skills, '
          '"Governs" lines match project-profile.md.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
