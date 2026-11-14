"""update_workspace()'s skills/ handling; no network or installed workspace."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_sync(data_root):
    spec = importlib.util.spec_from_file_location('sync_update', ROOT / 'sync.py')
    module = importlib.util.module_from_spec(spec)
    os.environ['MURPIANO_DX_DATA_DIR'] = str(data_root)
    spec.loader.exec_module(module)
    return module


class SkillsUpdateStaysCurrentExceptNamedOverrides(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='murpiano-dx-sync-')
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'source'
        self.workspace = Path(self.tmp.name) / 'workspace'
        self.workspace.mkdir()
        self.sync = load_sync(self.workspace)
        self.addCleanup(os.environ.pop, 'MURPIANO_DX_DATA_DIR', None)
        # The one real, documented override: TEMPLATE_LOCATIONS['readme'].
        self.override_relative = self.sync.TEMPLATE_LOCATIONS['readme']
        (self.source / self.override_relative.parent).mkdir(parents=True)
        (self.source / self.override_relative).write_text('default template\n')
        (self.source / 'skills/example-skill').mkdir(parents=True)
        (self.source / 'skills/example-skill/SKILL.md').write_text('old rule\n')
        # Another skill's own templates/ that is NOT in TEMPLATE_LOCATIONS -
        # the exact case the blanket "any templates/ path" rule got wrong.
        (self.source / 'skills/repo-lint-format/templates').mkdir(parents=True)
        (self.source / 'skills/repo-lint-format/templates/eslint.config.js').write_text(
            'export default []\n')

    def test_an_existing_non_template_skill_file_is_overwritten(self):
        existing = self.workspace / 'skills/example-skill/SKILL.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('stale rule, never updated before\n')
        (self.source / 'skills/example-skill/SKILL.md').write_text('fixed rule\n')

        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(existing.read_text(), 'fixed rule\n')

    def test_the_named_readme_template_override_is_never_touched(self):
        existing = self.workspace / self.override_relative
        existing.parent.mkdir(parents=True)
        existing.write_text('owner\'s real README, with their own badge\n')

        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(existing.read_text(), 'owner\'s real README, with their own badge\n')

    def test_a_templates_file_not_in_template_locations_still_force_updates(self):
        existing = self.workspace / 'skills/repo-lint-format/templates/eslint.config.js'
        existing.parent.mkdir(parents=True)
        existing.write_text('stale config\n')
        (self.source / 'skills/repo-lint-format/templates/eslint.config.js').write_text(
            'fixed config\n')

        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(existing.read_text(), 'fixed config\n')

    def test_a_new_skill_file_not_previously_present_is_added(self):
        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(
            (self.workspace / 'skills/example-skill/SKILL.md').read_text(), 'old rule\n')
        self.assertEqual(
            (self.workspace / self.override_relative).read_text(), 'default template\n')
