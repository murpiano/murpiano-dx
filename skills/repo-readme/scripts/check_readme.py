#!/usr/bin/env python3
"""Check README structure, footer, and placeholders against a selected template."""
import argparse
from pathlib import Path
import re
import sys


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


def check(readme, template):
    errors = []
    content = without_comments(readme)
    source = without_comments(template)
    actual = headings(content)
    cursor = 0
    for heading in headings(source):
        if re.search(r'<[^<>\n]+>|\{\{[^{}]+\}\}', heading):
            continue
        choices = [heading]
        # Only this explicitly documented conditional heading may be renamed.
        if heading == '## API' and 'rename to "## CLI"' in template:
            choices.append('## CLI')
            if 'rename to "## Usage"' in template:
                choices.append('## Usage')
        found = next((i for i in range(cursor, len(actual)) if actual[i] in choices), None)
        if found is None:
            errors.append('Missing or out-of-order heading: ' + ' / '.join(choices))
        else:
            cursor = found + 1

    placeholders = set(re.findall(r'<[^<>\n]+>|\{\{[^{}\n]+\}\}', source))
    placeholders = {p for p in placeholders if not re.fullmatch(r'</?[a-z][a-z0-9]*(?: /)?>', p)}
    # Lowercase tokens such as <repo> are placeholders, whereas <sub> is HTML.
    placeholders.update(p for p in ('<repo>', '<url>', '<dir>', '<path>') if p in source)
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
    args = parser.parse_args()
    try:
        errors = check(args.readme.read_text(), args.template.read_text())
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
