"""README contract regressions; no network or installed workspace required."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'readme_check', ROOT / 'skills/repo-readme/scripts/check_readme.py')
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ReadmeContract(unittest.TestCase):
    template = '''# <Name>

## Usage

<Paragraph.>

## Rough edges

- <Real limitation, stated as a fact.>

---

<sub>[Bogdan Trotsenko](https://github.com/murpiano) · [Telegram](https://t.me/murpiano) · [<License>](LICENSE)</sub>
'''
    valid = template.replace('<Name>', 'Example').replace('<Paragraph.>', 'Run the CLI.').replace(
        '<Real limitation, stated as a fact.>', 'Requires Python 3.11.').replace('<License>', 'MIT')

    def test_complete_document(self):
        self.assertEqual(CHECKER.check(self.valid, self.template), [])

    def test_replaced_or_reordered_headings_fail(self):
        for readme in (self.valid.replace('## Rough edges', '## License'),
                       self.valid.replace('## Usage', '## Temp').replace(
                           '## Rough edges', '## Usage').replace('## Temp', '## Rough edges')):
            self.assertTrue(CHECKER.check(readme, self.template))

    def test_copyright_cannot_replace_footer(self):
        readme = self.valid.split('---')[0] + '## License\n\nCopyright 2026 Bogdan Trotsenko.\n'
        self.assertTrue(any('footer' in error for error in CHECKER.check(readme, self.template)))

    def test_changed_footer_link_fails(self):
        self.assertTrue(CHECKER.check(self.valid.replace('https://t.me/murpiano', 'https://example.com'),
                                      self.template))

    def test_placeholders_fail_but_code_and_comments_are_not_headings(self):
        self.assertTrue(CHECKER.check(self.valid.replace('Run the CLI.', '<Paragraph.>'), self.template))
        readme = self.valid.replace('## Rough edges', '<!-- ## Hidden -->\n```md\n## Fake\n```\n## Rough edges')
        self.assertEqual(CHECKER.check(readme, self.template), [])

    def test_explicit_cli_conditional(self):
        template = '## API\n<!-- CLI: rename to "## CLI". Library: rename to "## Usage". -->\n'
        self.assertEqual(CHECKER.check('## CLI\n', template), [])
        self.assertTrue(CHECKER.check('## Configuration\n', template))

    def test_optional_license_link(self):
        template = self.template.replace('---', '---\n<!-- Omit the license link when LICENSE does not exist. -->')
        readme = self.valid.replace(' · [MIT](LICENSE)', '')
        self.assertEqual(CHECKER.check(readme, template, has_license=False), [])


if __name__ == '__main__':
    unittest.main()
