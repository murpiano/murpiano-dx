#!/usr/bin/env python3
"""Check README structure, footer, and placeholders against a selected template."""
import argparse
from pathlib import Path
import re
import sys

PROJECT_KINDS = ('app', 'framework', 'npm-package', 'personal-brand')
KIND_GROUPS = {'code': ('app', 'framework', 'npm-package')}


def without_comments(text):
    return re.sub(r'<!--.*?-->', '', text, flags=re.S)


def headings(text):
    result = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None and re.match(r'^#{2,6} ', line):
            result.append(line.rstrip())
    return result


def section_comments(source):
    """Pair each heading in `source` with the comment block right after it, if any."""
    lines = source.splitlines()
    sections = []
    fence = None
    i = 0
    while i < len(lines):
        line = lines[i]
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            i += 1
            continue
        if fence is None and re.match(r'^#{2,6} ', line):
            heading = line.rstrip()
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            comment = ''
            if j < len(lines) and lines[j].lstrip().startswith('<!--'):
                buf = []
                while j < len(lines):
                    buf.append(lines[j])
                    closed = '-->' in lines[j]
                    j += 1
                    if closed:
                        break
                comment = '\n'.join(buf)
            sections.append((heading, comment))
            i += 1
            continue
        i += 1
    return sections


def required_kinds(comment):
    """Project kinds this section applies to, or None when it applies to all of them."""
    match = re.search(r'kind:\s*([a-z0-9,\s\-]+?)[.\n]', comment)
    if not match:
        return None
    kinds = []
    for token in match.group(1).split(','):
        token = token.strip()
        if not token:
            continue
        kinds.extend(KIND_GROUPS.get(token, (token,)))
    return kinds


def rename_choices(comment):
    return re.findall(r'rename to "(#{2,6} [^"]+)"', comment)


def check(readme, template, kind=None):
    errors = []
    content = without_comments(readme)
    actual = headings(content)
    cursor = 0
    for heading, comment in section_comments(template):
        if re.search(r'<[^<>\n]+>|\{\{[^{}]+\}\}', heading):
            continue
        kinds = required_kinds(comment)
        required = kinds is None or (kind is not None and kind in kinds)
        choices = [heading] + rename_choices(comment)
        found = next((i for i in range(cursor, len(actual)) if actual[i] in choices), None)
        if found is None:
            if required:
                errors.append('Missing or out-of-order heading: ' + ' / '.join(choices))
            continue
        cursor = found + 1

    source = without_comments(template)
    placeholders = set(re.findall(r'<[^<>\n]+>|\{\{[^{}\n]+\}\}', source))
    placeholders = {p for p in placeholders if not re.fullmatch(r'</?[a-z][a-z0-9]*(?: /)?>', p)}
    # Lowercase tokens such as <repo> are placeholders, whereas <sub> is HTML.
    placeholders.update(p for p in ('<repo>', '<url>', '<dir>', '<path>', '<owner>', '<anchor>')
                        if p in source)
    for placeholder in sorted(placeholders):
        if placeholder in content:
            errors.append('Unfilled template placeholder: ' + placeholder)

    parts = re.split(r'^---\s*$', source, flags=re.M)
    if len(parts) > 1 and parts[-1].strip():
        footer = parts[-1].strip()
        pattern = re.escape(footer)
        for placeholder in placeholders:
            pattern = pattern.replace(re.escape(placeholder), r'[^<>\n]+?')
        pattern = r'\s+'.join(pattern.split(r'\ '))
        if not re.search(r'^---\s*\n\s*' + pattern + r'\s*\Z', content, flags=re.M):
            errors.append('Missing or changed template footer (text, links, or position)')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readme', type=Path)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--kind', choices=PROJECT_KINDS,
                         help='Project kind: sections tagged for other kinds become optional')
    args = parser.parse_args()
    try:
        errors = check(args.readme.read_text(), args.template.read_text(), kind=args.kind)
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f'README template: {args.template.resolve()}')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print('README template check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
