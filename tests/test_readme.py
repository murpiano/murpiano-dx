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

    def test_showcase_footer_requires_sub_separators_and_local_license(self):
        footer = ('<sub>[<Your name or handle>](<your-profile-url>) · '
                  '[<Your org, if any>](<your-org-url>) · '
                  '[<Contact>](<contact-url>) · '
                  '[<License>](LICENSE)</sub>')
        bundled = (ROOT / 'skills/repo-readme/templates/README.md').read_text()
        self.assertEqual(bundled.strip().splitlines()[-1], footer)
        template = '## Rough edges\n\n---\n\n' + footer + '\n'
        filled = template.replace('<Your name or handle>', 'Jane').replace(
            '<your-profile-url>', 'https://example.com/jane').replace(
            '<Your org, if any>', 'Acme').replace('<your-org-url>', 'https://example.com').replace(
            '<Contact>', 'Contact').replace('<contact-url>', 'https://example.com/contact').replace(
            '<License>', 'MIT')
        self.assertEqual(CHECKER.check(filled, template), [])
        filled_footer = filled.strip().splitlines()[-1]
        for wrong in (filled_footer.replace(' · [MIT](LICENSE)', ''), filled_footer.replace(' · ', ' '),
                      filled_footer.removeprefix('<sub>').removesuffix('</sub>'),
                      filled_footer.replace('(LICENSE)', '(https://example.com/LICENSE)')):
            self.assertTrue(CHECKER.check(filled.replace(filled_footer, wrong), template))

    def test_bundled_distribution_template_has_no_real_identity(self):
        bundled = (ROOT / 'skills/repo-readme/templates/README.md').read_text()
        for leaked in ('Bogdan', 'murpiano', 't.me/murpiano'):
            self.assertNotIn(leaked, bundled)

    def test_kind_tagged_section_is_optional_without_a_kind_and_required_with_it(self):
        template = ('## Install\n<!-- kind: app, npm-package. Drop for personal-brand. -->\n\n'
                    '## Rough edges\n\n---\n\n<sub>text</sub>\n')
        without_section = '## Rough edges\n\n---\n\n<sub>text</sub>\n'
        self.assertEqual(CHECKER.check(without_section, template), [])
        self.assertEqual(CHECKER.check(without_section, template, kind='personal-brand'), [])
        self.assertTrue(CHECKER.check(without_section, template, kind='app'))
        self.assertEqual(CHECKER.check(template, template, kind='npm-package'), [])

    def test_kind_rename_choice_is_accepted_as_an_alternate_heading(self):
        template = ('## Run locally\n<!-- kind: app, npm-package. npm-package: rename to '
                    '"## Install". -->\n\n## Rough edges\n\n---\n\n<sub>text</sub>\n')
        renamed = '## Install\n\n## Rough edges\n\n---\n\n<sub>text</sub>\n'
        self.assertEqual(CHECKER.check(renamed, template, kind='npm-package'), [])
        unrelated_heading = '## Something else\n\n## Rough edges\n\n---\n\n<sub>text</sub>\n'
        self.assertTrue(CHECKER.check(unrelated_heading, template, kind='app'))

    def test_framework_keeps_agent_notice_as_first_line(self):
        first = (ROOT / 'README.md').read_text().splitlines()[0]
        self.assertEqual(first, '> Agent entry point: read '
                         '[AGENTS.md](https://github.com/murpiano/murpiano-dx/blob/main/AGENTS.md) '
                         'and stop reading this README. This page is for humans.')


if __name__ == '__main__':
    unittest.main()
