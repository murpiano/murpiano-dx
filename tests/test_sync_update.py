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


class SkillsUpdateStaysCurrentExceptTemplates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='murpiano-dx-sync-')
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'source'
        self.workspace = Path(self.tmp.name) / 'workspace'
        (self.source / 'skills/example-skill/templates').mkdir(parents=True)
        (self.source / 'skills/example-skill/SKILL.md').write_text('old rule\n')
        (self.source / 'skills/example-skill/templates/README.md').write_text(
            'default template\n')
        self.workspace.mkdir()
        self.sync = load_sync(self.workspace)
        self.addCleanup(os.environ.pop, 'MURPIANO_DX_DATA_DIR', None)

    def test_an_existing_non_template_skill_file_is_overwritten(self):
        existing = self.workspace / 'skills/example-skill/SKILL.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('stale rule, never updated before\n')
        (self.source / 'skills/example-skill/SKILL.md').write_text('fixed rule\n')

        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(existing.read_text(), 'fixed rule\n')

    def test_an_existing_personal_template_override_is_never_touched(self):
        existing = self.workspace / 'skills/example-skill/templates/README.md'
        existing.parent.mkdir(parents=True)
        existing.write_text('owner\'s real README, with their own badge\n')

        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(existing.read_text(), 'owner\'s real README, with their own badge\n')

    def test_a_new_skill_file_not_previously_present_is_added(self):
        self.sync.update_skills_tree(self.source / 'skills', self.workspace / 'skills')

        self.assertEqual(
            (self.workspace / 'skills/example-skill/SKILL.md').read_text(), 'old rule\n')
        self.assertEqual(
            (self.workspace / 'skills/example-skill/templates/README.md').read_text(),
            'default template\n')
