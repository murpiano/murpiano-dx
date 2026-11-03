"""Integration checks in temporary homes and repositories. No GitHub calls."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]


class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='murpiano-dx-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.home), GIT_CONFIG_GLOBAL=str(self.home / '.gitconfig'),
                        GIT_CONFIG_NOSYSTEM='1', PROJECTS_DIR=str(self.home / 'projects'),
                        MURPIANO_DX_DATA_DIR=str(self.base / 'dx with spaces'))
        # Host-installed agents and profiles must not leak into temporary-home tests.
        for variable in ('CODEX_HOME', 'CLAUDE_CONFIG_DIR'):
            self.env.pop(variable, None)
        self.env['PATH'] = os.pathsep.join(
            folder for folder in self.env['PATH'].split(os.pathsep)
            if not any((Path(folder) / agent).is_file() for agent in ('codex', 'claude')))
        os.environ['MURPIANO_DX_DATA_DIR'] = str(self.base / 'dx with spaces')
        for key in list(self.env):
            if key.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_', 'GIT_CONFIG_')) and key not in (
                    'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM'):
                del self.env[key]
        self.dx = self.base / 'dx with spaces'
        self.dx.mkdir()
        for name in ['install.sh', 'configure-codex.py', 'agent_setup.py',
                     'sync.sh', 'sync.py', 'workspace_sync.py', 'session_hook.py', 'skills', 'global', 'defaults']:
            source = SOURCE / name
            if source.is_dir():
                shutil.copytree(source, self.dx / name)
            else:
                shutil.copy2(source, self.dx / name)
        (self.dx / 'config.env').write_text(
            'GIT_NAME="Test User"\nGIT_EMAIL="test@example.invalid"\nGITHUB_OWNER="owner"\n')
        (self.dx / 'projects').mkdir()
        (self.dx / 'projects/.gitignore').write_text('.sync.lock\n')
        self.repo(self.dx)
        self.project = self.home / 'projects/app'
        self.project.mkdir(parents=True)
        self.repo(self.project)
        self.git(self.project, 'remote', 'add', 'origin', 'git@github.com:owner/app.git')

    def run_cmd(self, args, cwd=None, check=True):
        return subprocess.run(args, cwd=cwd or self.dx, env=self.env, input='', text=True,
                              capture_output=True, check=check, timeout=25)

    def git(self, project, *args):
        return self.run_cmd(['git', *args], project)

    def repo(self, project):
        self.git(project, 'init', '-q', '-b', 'main')
        self.git(project, 'config', 'user.name', 'Test User')
        self.git(project, 'config', 'user.email', 'test@example.invalid')
        (project / 'initial.txt').write_text('initial\n')
        self.git(project, 'add', '.')
        self.git(project, 'commit', '-qm', 'chore: initial')

    def sync(self, mode='init', check=True, project=None, kysaro=None):
        args = ['bash', str(self.dx / 'sync.sh'), mode]
        if kysaro:
            args += ['--kysaro', kysaro]
        return self.run_cmd(args, project or self.project, check)

    def migrate(self, *args, check=True):
        helper = self.dx / 'skills/repo-agent-data/scripts/migrate.py'
        return self.run_cmd(['python3', str(helper), str(self.project), *args], check=check)

    def migration_module(self):
        helper = self.dx / 'skills/repo-agent-data/scripts/migrate.py'
        spec = importlib.util.spec_from_file_location('migration_test', helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_agent_data_preview_does_not_change_files_or_index(self):
        self.sync()
        folder = self.project / '.codex'
        folder.mkdir()
        (folder / 'notes.md').write_text('private decisions\n')
        before = self.git(self.project, 'status', '--porcelain', '--ignored').stdout
        index = (self.project / '.git/index').read_bytes()
        result = self.migrate()
        self.assertIn('.codex ->', result.stdout)
        self.assertEqual(self.git(self.project, 'status', '--porcelain', '--ignored').stdout, before)
        self.assertEqual((self.project / '.git/index').read_bytes(), index)
        self.assertFalse(folder.is_symlink())
        self.assertFalse((self.dx / 'projects/owner/app/files/.codex').exists())

    def test_agent_data_migration_preserves_content_and_other_staged_changes(self):
        (self.project / 'AGENTS.md').write_text('project instructions\n')
        folder = self.project / '.codex'
        folder.mkdir()
        (folder / 'data.bin').write_bytes(bytes(range(256)))
        executable = folder / 'check.sh'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
        self.git(self.project, 'add', 'AGENTS.md', '.codex')
        self.git(self.project, 'commit', '-qm', 'chore: save existing metadata')
        head = self.git(self.project, 'rev-parse', 'HEAD').stdout
        self.sync()
        (self.project / 'feature.py').write_text('print(1)\n')
        self.git(self.project, 'add', 'feature.py')
        staged = self.git(self.project, 'ls-files', '--stage', 'feature.py').stdout
        result = self.migrate('--apply')
        self.assertIn('No commit, push, or history rewrite', result.stdout)
        self.assertEqual(self.git(self.project, 'rev-parse', 'HEAD').stdout, head)
        self.assertTrue(folder.is_symlink())
        self.assertTrue((self.project / 'AGENTS.md').is_symlink())
        self.assertEqual((folder / 'data.bin').read_bytes(), bytes(range(256)))
        self.assertEqual(executable.stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.git(self.project, 'ls-files', '--', 'AGENTS.md', '.codex').stdout, '')
        self.assertEqual(self.git(self.project, 'ls-files', '--stage', 'feature.py').stdout, staged)
        report = self.dx / 'projects/owner/app/agent-data-migration.json'
        before = report.read_bytes()
        state = self.git(self.project, 'diff', '--cached').stdout
        self.migrate('--apply')
        self.assertEqual(report.read_bytes(), before)
        self.assertEqual(self.git(self.project, 'diff', '--cached').stdout, state)
        self.git(self.project, 'add', '-A')
        self.assertEqual(self.git(self.project, 'ls-files', '--', '.codex', 'AGENTS.md').stdout, '')
        self.assertIn('AGENTS.md', json.loads(report.read_text())['paths'])

    def test_agent_data_conflict_preserves_both_copies(self):
        self.sync()
        folder = self.project / '.codex'
        folder.mkdir()
        (folder / 'notes').write_text('local\n')
        stored = self.dx / 'projects/owner/app/files/.codex'
        stored.mkdir()
        (stored / 'notes').write_text('stored\n')
        before = (self.project / '.git/index').read_bytes()
        result = self.migrate('--apply', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Destination differs', result.stderr)
        self.assertEqual((folder / 'notes').read_text(), 'local\n')
        self.assertEqual((stored / 'notes').read_text(), 'stored\n')
        self.assertEqual((self.project / '.git/index').read_bytes(), before)

    def test_agent_data_staged_edits_are_not_discarded(self):
        self.sync()
        (self.project / '.codex').mkdir()
        note = self.project / '.codex/note'
        note.write_text('staged\n')
        self.git(self.project, 'add', '-f', '.codex/note')
        note.write_text('working\n')
        index = (self.project / '.git/index').read_bytes()
        result = self.migrate('--apply', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('staged edits', result.stderr)
        self.assertEqual(note.read_text(), 'working\n')
        self.assertEqual((self.project / '.git/index').read_bytes(), index)

    def test_agent_data_custom_notes_require_explicit_path(self):
        self.sync()
        notes = self.project / 'memory'
        notes.mkdir()
        (notes / 'MEMORY.md').write_text('project memory\n')
        self.migrate('--apply')
        self.assertFalse(notes.is_symlink())
        self.migrate('--path', 'memory', '--apply')
        self.assertTrue(notes.is_symlink())
        self.assertEqual(notes.resolve(), self.dx / 'projects/owner/app/memory')
        self.assertEqual((notes / 'MEMORY.md').read_text(), 'project memory\n')
        self.assertIn('memory', self.git(self.project, 'check-ignore', 'memory').stdout)

    def test_agent_data_rejects_external_links_and_nested_repositories(self):
        self.sync()
        folder = self.project / '.codex'
        folder.mkdir()
        outside = self.base / 'personal'
        outside.write_text('outside data\n')
        (folder / 'external').symlink_to(outside)
        result = self.migrate('--apply', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('symbolic link', result.stderr)
        self.assertEqual(outside.read_text(), 'outside data\n')
        (folder / 'external').unlink()
        (folder / '.git').mkdir()
        result = self.migrate('--apply', check=False)
        self.assertIn('Nested Git repository', result.stderr)

    def test_agent_data_refuses_paths_outside_project_and_product_tooling(self):
        self.sync()
        for path in ('../other', str(self.base), '.', '.git', '.kysaro', '.github', '.github/workflows'):
            with self.subTest(path=path):
                result = self.migrate('--path', path, '--apply', check=False)
                self.assertNotEqual(result.returncode, 0)

    def test_agent_data_git_failure_restores_files_and_exclusions(self):
        (self.project / 'AGENTS.md').write_text('keep instructions\n')
        self.git(self.project, 'add', 'AGENTS.md')
        self.git(self.project, 'commit', '-qm', 'chore: save instructions')
        self.sync()
        helper = self.migration_module()
        data = self.dx / 'projects/owner/app'
        items = helper.plan(self.project, data, [])
        exclude = self.project / '.git/info/exclude'
        before = exclude.read_bytes()
        original = helper.git

        def fail_remove(project, *args):
            if args[0] == 'rm':
                raise RuntimeError('simulated index failure')
            return original(project, *args)

        with patch.object(helper, 'git', side_effect=fail_remove):
            with self.assertRaisesRegex(RuntimeError, 'simulated index failure'):
                helper.apply(self.project, data, items)
        self.assertFalse((self.project / 'AGENTS.md').is_symlink())
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'keep instructions\n')
        self.assertEqual(exclude.read_bytes(), before)
        self.assertIn('AGENTS.md', self.git(self.project, 'ls-files', 'AGENTS.md').stdout)

    def test_agent_data_failed_link_restores_original_and_keeps_verified_copy(self):
        self.sync()
        folder = self.project / '.codex'
        folder.mkdir()
        (folder / 'notes').write_text('keep this\n')
        helper = self.migration_module()
        data = self.dx / 'projects/owner/app'
        items = helper.plan(self.project, data, [])
        with patch.object(Path, 'symlink_to', side_effect=OSError('link denied')):
            with self.assertRaisesRegex(OSError, 'link denied'):
                helper.apply(self.project, data, items)
        self.assertFalse(folder.is_symlink())
        self.assertEqual((folder / 'notes').read_text(), 'keep this\n')
        self.assertEqual((data / 'files/.codex/notes').read_text(), 'keep this\n')

    def test_agent_data_leaves_code_documentation_and_linter_in_project(self):
        self.sync()
        readme = self.project / 'README.md'
        readme.write_text('An AI assistant product.\n')
        settings = self.project / '.kysaro/settings.json'
        settings.parent.mkdir()
        settings.write_text('{}\n')
        self.git(self.project, 'add', 'README.md', '.kysaro/settings.json')
        self.git(self.project, 'commit', '-qm', 'docs: describe product')
        self.migrate('--apply')
        self.assertFalse(readme.is_symlink())
        self.assertFalse(settings.is_symlink())
        self.assertEqual(readme.read_text(), 'An AI assistant product.\n')
        self.assertIn('.kysaro/settings.json', self.git(self.project, 'ls-files').stdout)

    def test_agent_data_helper_installed_as_skill(self):
        self.run_cmd(['bash', 'install.sh'])
        skill = self.home / '.agents/skills/repo-agent-data'
        self.assertTrue(skill.is_symlink())
        self.assertTrue((skill / 'scripts/migrate.py').is_file())

    def prepare_kysaro_components(self):
        binary = self.project / 'node_modules/.bin/kysaro'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nexit 0\n')
        binary.chmod(0o755)
        # Component detection does not execute Node; keep tests independent of host runtimes.
        tools = self.base / 'runtime'
        tools.mkdir()
        node = tools / 'node'
        node.write_text('#!/bin/sh\nexit 0\n')
        node.chmod(0o755)
        self.env['PATH'] = str(tools) + os.pathsep + self.env['PATH']
        settings = self.project / '.kysaro/settings/commits'
        settings.mkdir(parents=True)
        for kind in ['commit', 'merge', 'request']:
            (settings / f'{kind}.json').write_text('{}\n')
        hook = self.project / '.git/hooks/commit-msg'
        hook.write_text('#!/bin/sh\nnpx --no-install kysaro "$1"\n')
        hook.chmod(0o755)
        ci = self.project / '.github/workflows/kysaro.yml'
        ci.parent.mkdir(parents=True)
        ci.write_text('name: kysaro\njobs:\n  check:\n    steps:\n      - run: npx kysaro ci\n')

    def test_installer_preserves_global_settings_and_is_idempotent(self):
        rules = self.home / '.codex/AGENTS.md'
        rules.parent.mkdir()
        rules.write_text('Existing rules\n')
        self.run_cmd(['git', 'config', '--global', 'user.name', 'Keep Me'])
        before = (self.home / '.gitconfig').read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        first = rules.read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(rules.read_bytes(), first)
        self.assertIn('Existing rules', rules.read_text())
        self.assertNotIn('{{', rules.read_text())
        self.assertEqual((self.home / '.gitconfig').read_bytes(), before)
        self.assertFalse((self.home / '.claude').exists())
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertFalse((self.home / '.config/murpiano-dx/release-token').exists())
        for name in ['repo-init', 'repo-commit', 'repo-readme', 'repo-release']:
            self.assertTrue((self.home / '.agents/skills' / name).is_symlink())

    def test_default_setup_has_generic_entry_point_and_no_agent_specific_settings(self):
        result = self.run_cmd(['bash', 'install.sh'])
        self.assertIn('Agent entry point:', result.stdout)
        self.assertNotIn('Codex', result.stdout)
        for name in ('.codex', '.claude', '.cursor'):
            self.assertFalse((self.home / name).exists())
        entry = self.dx / 'AGENTS.md'
        self.assertTrue(entry.is_file())
        self.assertIn(str(self.dx / 'skills'), entry.read_text())
        self.assertNotIn('{{', entry.read_text())
        self.assertTrue((self.home / '.agents/skills/repo-init').is_symlink())

    def test_default_setup_preserves_existing_agent_global_instructions(self):
        instructions = self.home / '.codex/AGENTS.md'
        instructions.parent.mkdir()
        instructions.write_text('Custom instructions\n')
        before = instructions.read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(instructions.read_bytes().startswith(before))
        self.assertIn('<!-- >>> murpiano-dx -->', instructions.read_text())
        self.assertTrue((self.home / '.agents/skills/repo-release').is_symlink())

    def test_legacy_codex_configurator_keeps_explicit_integration(self):
        self.run_cmd(['python3', 'configure-codex.py', str(self.dx)])
        self.assertTrue((self.home / '.codex/AGENTS.md').is_file())
        self.assertTrue((self.home / '.agents/skills/repo-init').is_symlink())

    def fake_agent(self, name):
        binaries = self.base / 'agent-bin'
        binaries.mkdir(exist_ok=True)
        executable = binaries / name
        # Setup may detect the executable but must never launch an agent.
        executable.write_text('#!/bin/sh\nexit 71\n')
        executable.chmod(0o755)
        if str(binaries) not in self.env['PATH'].split(os.pathsep):
            self.env['PATH'] = str(binaries) + os.pathsep + self.env['PATH']

    def test_setup_detects_both_agents_from_path_and_links_shared_skills(self):
        self.fake_agent('codex')
        self.fake_agent('claude')
        result = self.run_cmd(['bash', 'install.sh'])
        self.assertIn('Codex connected:', result.stdout)
        self.assertIn('Claude Code connected:', result.stdout)
        codex = self.home / '.codex/AGENTS.md'
        claude = self.home / '.claude/CLAUDE.md'
        self.assertEqual(codex.read_text(), claude.read_text())
        common = self.home / '.agents/skills/repo-commit'
        native = self.home / '.claude/skills/repo-commit'
        self.assertEqual(common.resolve(), native.resolve())
        self.assertEqual(native.resolve(), self.dx / 'skills/repo-commit')
        first = claude.read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(claude.read_bytes(), first)
        self.assertEqual(claude.read_text().count('<!-- >>> murpiano-dx -->'), 1)

    def test_setup_installs_session_hooks_and_preserves_custom_settings(self):
        for agent, filename in [('codex', 'hooks.json'), ('claude', 'settings.json')]:
            profile = self.home / ('.' + agent)
            profile.mkdir()
            hook = {'hooks': [{'type': 'command', 'command': 'echo my custom hook'}]}
            settings = {'mySetting': 'keep', 'hooks': {'SessionStart': [hook], 'Stop': [hook]}}
            (profile / filename).write_text(json.dumps(settings))
        codex_config = self.home / '.codex/config.toml'
        codex_config.write_text('[features]\nhooks = false\n')
        self.run_cmd(['bash', 'install.sh'])
        first = {}
        for agent, filename in [('codex', 'hooks.json'), ('claude', 'settings.json')]:
            path = self.home / ('.' + agent) / filename
            settings = json.loads(path.read_text())
            self.assertEqual(settings['mySetting'], 'keep')
            self.assertEqual(settings['hooks']['Stop'], [hook])
            self.assertEqual(settings['hooks']['SessionStart'][0], hook)
            self.assertEqual(len(settings['hooks']['SessionStart']), 2)
            self.assertEqual(len(settings['hooks']['SessionEnd']), 1)
            command = settings['hooks']['SessionEnd'][0]['hooks'][0]['command']
            self.assertIn('session_hook.py', command)
            self.assertTrue(command.endswith(' end'))
            first[path] = path.read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        for path, before in first.items():
            self.assertEqual(path.read_bytes(), before)
        self.assertEqual(codex_config.read_text(), '[features]\nhooks = false\n')

    def test_setup_repoints_source_skills_to_personal_workspace(self):
        folder = self.home / '.agents/skills'
        folder.mkdir(parents=True)
        old = folder / 'repo-commit'
        old.symlink_to(self.dx / 'skills/repo-commit', target_is_directory=True)
        custom_target = self.base / 'custom skill'
        custom_target.mkdir()
        custom = folder / 'repo-readme'
        custom.symlink_to(custom_target, target_is_directory=True)
        self.fake_agent('claude')
        native = self.home / '.claude/skills'
        native.mkdir(parents=True)
        native_link = native / 'repo-init'
        native_link.symlink_to(self.dx / 'skills/repo-init', target_is_directory=True)
        workspace = self.base / 'personal workspace'
        env = dict(self.env, MURPIANO_DX_DATA_DIR=str(workspace),
                   XDG_BIN_HOME=str(self.base / 'bin'))
        for _ in range(2):
            result = subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                                    text=True, capture_output=True, check=True)
            self.assertEqual(old.resolve(), workspace / 'skills/repo-commit')
            self.assertEqual(native_link.resolve(), workspace / 'skills/repo-init')
            self.assertEqual(custom.resolve(), custom_target)
        self.assertIn('Skip conflicting link:', result.stderr)
        self.assertTrue((self.dx / 'skills/repo-commit/SKILL.md').is_file())

    def test_setup_fills_empty_saved_identity_without_overwriting_personal_values(self):
        config = self.dx / 'config'
        config.mkdir()
        machine = config / 'machine.json'
        machine.write_text(json.dumps({'git_name': 'My chosen name', 'git_email': '',
                                       'github_owner': '', 'custom': 'keep'}))
        self.run_cmd(['bash', 'install.sh'])
        saved = json.loads(machine.read_text())
        self.assertEqual(saved['git_name'], 'My chosen name')
        self.assertEqual(saved['git_email'], 'test@example.invalid')
        self.assertEqual(saved['github_owner'], 'owner')
        self.assertEqual(saved['custom'], 'keep')
        before = machine.read_bytes()
        self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(machine.read_bytes(), before)

    def test_setup_preserves_hook_config_symlink(self):
        profile = self.home / '.claude'
        profile.mkdir()
        original = self.base / 'shared hooks.json'
        original.write_text('{"custom": "keep"}\n')
        settings = profile / 'settings.json'
        settings.symlink_to(original)
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(settings.is_symlink())
        self.assertEqual(json.loads(original.read_text())['custom'], 'keep')
        self.assertIn('SessionEnd', json.loads(original.read_text())['hooks'])

    def test_invalid_hooks_stop_setup_before_any_agent_instructions_change(self):
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'AGENTS.md').write_text('Preserve Codex\n')
        claude = self.home / '.claude'
        claude.mkdir()
        (claude / 'CLAUDE.md').write_text('Preserve Claude\n')
        settings = claude / 'settings.json'
        settings.write_text('{invalid JSON')
        result = self.run_cmd(['bash', 'install.sh'], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid hook settings', result.stderr)
        self.assertEqual((codex / 'AGENTS.md').read_text(), 'Preserve Codex\n')
        self.assertEqual((claude / 'CLAUDE.md').read_text(), 'Preserve Claude\n')
        self.assertEqual(settings.read_text(), '{invalid JSON')
        self.assertFalse((codex / 'hooks.json').exists())
        self.assertFalse((self.home / '.agents').exists())

    def test_setup_detects_claude_profile_and_preserves_custom_instructions(self):
        instructions = self.home / '.claude/CLAUDE.md'
        instructions.parent.mkdir()
        instructions.write_text('Keep my preferences exactly.\n\n')
        custom = self.home / '.claude/skills/repo-init'
        custom.mkdir(parents=True)
        (custom / 'mine').write_text('my custom skill\n')
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(instructions.read_text().startswith('Keep my preferences exactly.\n\n'))
        self.assertEqual((custom / 'mine').read_text(), 'my custom skill\n')
        self.assertFalse((self.home / '.codex').exists())

    def test_setup_connects_agent_added_after_initial_installation(self):
        self.run_cmd(['bash', 'install.sh'])
        self.assertFalse((self.home / '.claude').exists())
        self.fake_agent('claude')
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue((self.home / '.claude/CLAUDE.md').is_file())
        self.assertFalse((self.home / '.codex').exists())

    def test_setup_respects_custom_agent_profiles_and_codex_override(self):
        codex = self.base / 'custom codex'
        codex.mkdir()
        base = codex / 'AGENTS.md'
        base.write_text('Base stays unchanged\n')
        override = codex / 'AGENTS.override.md'
        override.write_text('Active override\n')
        claude = self.base / 'custom claude'
        self.env.update(CODEX_HOME=str(codex), CLAUDE_CONFIG_DIR=str(claude))
        self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(base.read_text(), 'Base stays unchanged\n')
        self.assertIn('<!-- >>> murpiano-dx -->', override.read_text())
        self.assertTrue((claude / 'CLAUDE.md').is_file())
        self.assertTrue((claude / 'skills/repo-readme').is_symlink())
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude').exists())

    def test_setup_checks_all_markers_before_changing_either_agent(self):
        codex = self.home / '.codex/AGENTS.md'
        codex.parent.mkdir()
        codex.write_text('Keep codex\n')
        claude = self.home / '.claude/CLAUDE.md'
        claude.parent.mkdir()
        claude.write_text('Keep claude\n<!-- >>> murpiano-dx -->\n')
        before = codex.read_bytes(), claude.read_bytes()
        result = self.run_cmd(['bash', 'install.sh'], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid murpiano-dx instruction markers', result.stderr)
        self.assertEqual((codex.read_bytes(), claude.read_bytes()), before)
        self.assertFalse((self.home / '.agents').exists())

    def test_setup_preserves_claude_instruction_symlink(self):
        target = self.base / 'shared claude.md'
        target.write_text('Shared personal instructions\n')
        linked = self.home / '.claude/CLAUDE.md'
        linked.parent.mkdir()
        linked.symlink_to(target)
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(linked.is_symlink())
        self.assertIn('Shared personal instructions', target.read_text())
        self.assertIn('<!-- >>> murpiano-dx -->', target.read_text())

    def test_setup_updates_only_managed_block_and_preserves_surrounding_text(self):
        instructions = self.home / '.claude/CLAUDE.md'
        instructions.parent.mkdir()
        prefix = 'My preferences\n\n'
        suffix = '\n\nMy closing notes\n\n'
        instructions.write_text(prefix + '<!-- >>> murpiano-dx -->\nold\n<!-- <<< murpiano-dx -->' + suffix)
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(instructions.read_text().startswith(prefix))
        self.assertTrue(instructions.read_text().endswith(suffix))
        self.assertNotIn('\nold\n', instructions.read_text())

    def test_installer_builds_one_runtime_workspace_without_maintenance_files(self):
        workspace = self.base / 'workspace'
        env = self.env.copy()
        env.update(MURPIANO_DX_DATA_DIR=str(workspace), GIT_NAME='Workspace User',
                   GIT_EMAIL='workspace@example.invalid', GITHUB_OWNER='owner',
                   XDG_BIN_HOME=str(self.base / 'bin'))
        result = subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                                text=True, capture_output=True, check=True)
        self.assertIn('Local workspace:', result.stdout)
        self.assertTrue((workspace / '.git').is_dir())
        self.assertTrue((workspace / '.murpiano-dx-workspace').is_file())
        self.assertTrue((workspace / 'sync.py').is_file())
        self.assertTrue((workspace / 'agent_setup.py').is_file())
        self.assertTrue((workspace / 'AGENTS.md').is_file())
        self.assertTrue((workspace / 'skills/repo-init/SKILL.md').is_file())
        self.assertTrue((workspace / 'projects').is_dir())
        self.assertFalse((workspace / 'tests').exists())
        self.assertFalse((workspace / '.github').exists())
        self.assertTrue(self.run_cmd(['git', '-C', str(workspace), 'log', '-1'],
                                     cwd=self.base).stdout)
        custom_rule = workspace / 'rules/git.md'
        custom_rule.write_text('custom rule\n')
        entry = workspace / 'AGENTS.md'
        entry.write_text('My own agent entry point\n')
        subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                       text=True, capture_output=True, check=True)
        self.assertEqual(custom_rule.read_text(), 'custom rule\n')
        self.assertEqual(entry.read_text(), 'My own agent entry point\n')

    def test_setup_upgrades_old_runtime_without_overwriting_personal_rules(self):
        workspace = self.base / 'old workspace'
        env = self.env.copy()
        env.update(MURPIANO_DX_DATA_DIR=str(workspace), GIT_NAME='Workspace User',
                   GIT_EMAIL='workspace@example.invalid', GITHUB_OWNER='owner',
                   XDG_BIN_HOME=str(self.base / 'bin'))
        subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                       text=True, capture_output=True, check=True)
        old = workspace / 'install.sh'
        old.write_text('#!/bin/sh\necho old installer\n')
        rules = workspace / 'rules/git.md'
        rules.write_text('My Git rules\n')
        machine = (workspace / 'config/machine.json').read_bytes()
        subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                       text=True, capture_output=True, check=True)
        self.assertEqual(old.read_bytes(), (self.dx / 'install.sh').read_bytes())
        self.assertIn('old installer', (workspace / '.runtime-backup/install.sh').read_text())
        self.assertEqual(rules.read_text(), 'My Git rules\n')
        self.assertEqual((workspace / 'config/machine.json').read_bytes(), machine)

    def test_end_pushes_and_start_gets_other_machine_changes(self):
        workspace = self.base / 'workspace'
        env = self.env.copy()
        env.update(MURPIANO_DX_DATA_DIR=str(workspace), GIT_NAME='Workspace User',
                   GIT_EMAIL='workspace@example.invalid', GITHUB_OWNER='owner',
                   XDG_BIN_HOME=str(self.base / 'bin'))
        subprocess.run(['bash', str(self.dx / 'install.sh')], env=env,
                       text=True, capture_output=True, check=True)
        remote = self.base / 'private.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
        self.run_cmd(['git', '-C', str(workspace), 'remote', 'add', 'origin', str(remote)],
                     cwd=self.base)
        self.run_cmd(['git', '-C', str(workspace), 'push', '-q', '-u', 'origin', 'main'],
                     cwd=self.base)
        (workspace / 'rules/git.md').write_text('private override\n')
        result = subprocess.run(['bash', str(workspace / 'sync.sh'), 'end'],
                                cwd=self.project, env=env, text=True,
                                capture_output=True, check=True)
        self.assertIn('Workspace state pushed', result.stdout)
        self.assertEqual(self.run_cmd(['git', '-C', str(workspace), 'status', '--porcelain'],
                                      cwd=self.base).stdout, '')
        check = self.base / 'check'
        self.run_cmd(['git', 'clone', '-q', '-b', 'main', str(remote), str(check)], cwd=self.base)
        self.assertEqual((check / 'rules/git.md').read_text(), 'private override\n')
        self.git(check, 'config', 'user.name', 'Other Machine')
        self.git(check, 'config', 'user.email', 'other@example.invalid')
        (check / 'rules/git.md').write_text('updated on another machine\n')
        self.git(check, 'add', 'rules/git.md')
        self.git(check, 'commit', '-qm', 'chore: update shared rules')
        self.git(check, 'push')
        subprocess.run(['bash', str(workspace / 'sync.sh'), 'start'],
                       cwd=self.project, env=env, text=True, capture_output=True, check=True)
        self.assertEqual((workspace / 'rules/git.md').read_text(), 'updated on another machine\n')
        head = self.git(workspace, 'rev-parse', 'HEAD').stdout
        (workspace / 'local-only.md').write_text('still uncommitted\n')
        self.git(workspace, 'remote', 'set-url', 'origin', str(self.base / 'offline.git'))
        local = subprocess.run(['bash', str(workspace / 'sync.sh'), 'start', '--local'],
                               cwd=self.project, env=env, text=True, capture_output=True, check=True)
        self.assertNotIn('sync pending', local.stderr)
        self.assertEqual(self.git(workspace, 'rev-parse', 'HEAD').stdout, head)
        # A restored clone has no local Git identity. Setup restores it from saved settings.
        self.git(check, 'config', '--unset', 'user.name')
        self.git(check, 'config', '--unset', 'user.email')
        env['MURPIANO_DX_DATA_DIR'] = str(check)
        subprocess.run(['bash', str(check / 'install.sh')], env=env,
                       text=True, capture_output=True, check=True)
        self.assertTrue(self.git(check, 'config', '--get', 'user.name').stdout.strip())
        self.assertTrue(self.git(check, 'config', '--get', 'user.email').stdout.strip())

    def test_installer_removes_only_owned_retired_skill(self):
        folder = self.home / '.agents/skills'
        folder.mkdir(parents=True)
        retired = folder / 'repo-cleanup'
        retired.symlink_to(self.dx / 'skills/repo-cleanup')
        custom = folder / 'repo-commit'
        custom.mkdir()
        (custom / 'mine').write_text('keep')
        self.run_cmd(['bash', 'install.sh'])
        self.assertFalse(retired.is_symlink())
        self.assertEqual((custom / 'mine').read_text(), 'keep')

    def test_invalid_instruction_markers_leave_installation_untouched(self):
        rules = self.home / '.codex/AGENTS.md'
        rules.parent.mkdir()
        rules.write_text('<!-- <<< murpiano-dx -->\n<!-- >>> murpiano-dx -->\n')
        before = rules.read_bytes()
        result = self.run_cmd(['bash', 'install.sh'], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(rules.read_bytes(), before)
        self.assertFalse((self.home / '.agents').exists())

    def test_installer_follows_existing_instruction_symlink(self):
        target = self.base / 'shared rules.md'
        target.write_text('Shared rules\n')
        rules = self.home / '.codex/AGENTS.md'
        rules.parent.mkdir()
        rules.symlink_to(target)
        self.run_cmd(['bash', 'install.sh'])
        self.assertTrue(rules.is_symlink())
        self.assertIn('Shared rules', target.read_text())
        self.assertIn('murpiano-dx', target.read_text())

    def test_installer_retires_global_guard_and_preserves_other_husky_code(self):
        hook = self.home / '.config/husky/init.sh'
        hook.parent.mkdir(parents=True)
        old = '''# Sourced by husky before every hook. Runs the murpiano-dx pre-commit guard in kysaro,
# where husky owns the pre-commit hook and sync.sh does not replace it.
if [ "$(basename "$0")" = pre-commit ] &&
  git remote get-url origin 2>/dev/null | grep -qE 'murpiano/kysaro(\\.git)?$'; then
  bash "$HOME/projects/murpiano-dx/skills/repo-cleanup/pre-commit-hook.sh" || exit 1
fi
'''
        hook.write_text('export KEEP_THIS=1\n' + old)
        self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(hook.read_text(), 'export KEEP_THIS=1\n')
        hook.write_text(old.replace('|| exit 1', '|| echo custom'))
        before = hook.read_bytes()
        result = self.run_cmd(['bash', 'install.sh'])
        self.assertEqual(hook.read_bytes(), before)
        self.assertIn('customized initialization left unchanged', result.stderr)

    def test_init_new_repository_proposes_private_origin_without_commit(self):
        project = self.base / 'new app'
        project.mkdir()
        (project / 'app.py').write_text('print(1)\n')
        result = self.sync('init', project=project)
        self.assertTrue((project / '.git').is_dir())
        self.assertIn('gh repo create --private', result.stdout)
        self.assertEqual(self.git(project, 'remote').stdout, '')
        head = self.run_cmd(['git', 'rev-parse', '--verify', 'HEAD'], project, False)
        self.assertNotEqual(head.returncode, 0)
        self.assertEqual(self.git(project, 'config', 'user.name').stdout.strip(), 'Test User')

    def test_start_without_git_only_explains_initialization(self):
        project = self.base / 'plain'
        project.mkdir()
        result = self.sync('start', project=project)
        self.assertFalse((project / '.git').exists())
        self.assertIn('init', result.stdout)

    def test_connect_creates_instructions_and_excludes_links(self):
        self.sync('init')
        rules = self.project / 'AGENTS.md'
        self.assertTrue(rules.is_symlink())
        self.assertIn('owner/app', rules.read_text())
        self.assertNotIn('{{', rules.read_text())
        self.assertTrue((self.project / '.agents').is_symlink())
        self.git(self.project, 'add', '-A')
        self.assertEqual(self.git(self.project, 'diff', '--cached', '--name-only').stdout, '')
        self.assertFalse((self.project / '.git/hooks/pre-commit').exists())

    def test_project_notes_update_the_store_and_reconnect(self):
        self.sync()
        note = self.project / '.agents/decisions.md'
        note.write_text('Use SQLite\n')
        self.sync('end')
        saved = self.dx / 'projects/owner/app/files/.agents/decisions.md'
        self.assertEqual(saved.read_text(), 'Use SQLite\n')
        (self.project / 'AGENTS.md').unlink()
        (self.project / '.agents').unlink()
        self.sync()
        self.assertEqual(note.read_text(), 'Use SQLite\n')
        self.assertTrue((self.project / 'AGENTS.md').is_symlink())

    def test_adopt_preserves_existing_rules_memory_and_git_index(self):
        (self.project / 'AGENTS.md').write_text('Project rules\n')
        memory = self.dx / 'projects/owner/app/memory'
        memory.mkdir(parents=True)
        (memory / 'MEMORY.md').write_text('Valuable context\n')
        legacy = self.home / '.claude/projects/legacy/memory'
        legacy.mkdir(parents=True)
        (legacy / 'MEMORY.md').write_text('Legacy context\n')
        self.git(self.project, 'add', 'initial.txt')
        before = self.git(self.dx, 'rev-parse', 'HEAD').stdout
        result = self.sync()
        self.sync('end')
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'Project rules\n')
        self.assertEqual((memory / 'MEMORY.md').read_text(), 'Valuable context\n')
        self.assertEqual((legacy / 'MEMORY.md').read_text(), 'Legacy context\n')
        self.assertIn(str(memory), result.stdout)
        self.assertEqual(self.git(self.dx, 'rev-parse', 'HEAD').stdout, before)
        self.assertEqual(self.git(self.dx, 'diff', '--cached', '--name-only').stdout, '')

    def test_runtime_directories_are_not_moved(self):
        for name in ['.claude', '.superpowers', '.codex']:
            folder = self.project / name
            folder.mkdir()
            (folder / 'runtime.lock').write_text('keep here')
        self.sync()
        for name in ['.claude', '.superpowers', '.codex']:
            self.assertFalse((self.project / name).is_symlink())
            self.assertFalse((self.dx / 'projects/owner/app/files' / name).exists())

    def test_foreign_origins_not_adopted_or_replaced(self):
        for remote in ['https://gitlab.com/owner/app.git', 'https://github.com/other/app.git',
                       'https://github.com.evil/owner/app.git', 'git@github.com:owner/../app.git']:
            self.git(self.project, 'remote', 'set-url', 'origin', remote)
            rules = self.project / 'AGENTS.md'
            rules.write_text('local')
            self.sync()
            self.assertFalse(rules.is_symlink())
            self.assertFalse((self.dx / 'projects/owner/app').exists())
            self.assertEqual(self.git(self.project, 'remote', 'get-url', 'origin').stdout.strip(), remote)

    def test_https_origin_uses_same_project_store(self):
        self.git(self.project, 'remote', 'set-url', 'origin', 'https://github.com/owner/app.git')
        self.sync()
        self.assertEqual((self.project / 'AGENTS.md').resolve(),
                         self.dx / 'projects/owner/app/files/AGENTS.md')

    def test_conflicting_symlink_and_store_files_preserved(self):
        saved = self.dx / 'projects/owner/app/files'
        saved.mkdir(parents=True)
        (saved / 'AGENTS.md').write_text('stored')
        target = self.base / 'mine'
        target.write_text('mine')
        rules = self.project / 'AGENTS.md'
        rules.symlink_to(target)
        self.sync()
        self.assertEqual(rules.resolve(), target)
        rules.unlink()
        rules.write_text('local')
        self.sync()
        self.assertFalse(rules.is_symlink())
        self.assertEqual(rules.read_text(), 'local')
        self.assertEqual((saved / 'AGENTS.md').read_text(), 'stored')

    def test_tracked_instructions_not_moved(self):
        rules = self.project / 'AGENTS.md'
        rules.write_text('Tracked rules\n')
        self.git(self.project, 'add', 'AGENTS.md')
        self.git(self.project, 'commit', '-qm', 'docs: add project rules')
        self.sync()
        self.assertFalse(rules.is_symlink())
        self.assertEqual(rules.read_text(), 'Tracked rules\n')

    def test_local_exclusions_preserved_and_idempotent(self):
        path = self.project / '.git/info/exclude'
        path.write_text('my-local-file\n')
        self.sync()
        first = path.read_bytes()
        self.sync()
        self.assertEqual(path.read_bytes(), first)
        self.assertIn('my-local-file', path.read_text())

    def old_hook(self, custom=False):
        path = self.project / '.git/hooks/pre-commit'
        text = ('#!/usr/bin/env bash\n'
                '# murpiano-dx: agent-trace pre-commit scan (skills/repo-cleanup)\n'
                f'exec bash "{self.dx}/skills/repo-cleanup/pre-commit-hook.sh"\n')
        path.write_text(text + ('# custom changes\n' if custom else ''))
        return path

    def test_only_owned_unmodified_hook_is_removed(self):
        hook = self.old_hook()
        self.sync()
        self.assertFalse(hook.exists())
        hook = self.old_hook(custom=True)
        before = hook.read_bytes()
        self.sync()
        self.assertEqual(hook.read_bytes(), before)

    def test_unrelated_hook_is_preserved(self):
        hook = self.project / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 0\n')
        self.sync()
        self.assertEqual(hook.read_text(), '#!/bin/sh\nexit 0\n')

    def test_store_lock_failure_is_reported_accurately(self):
        (self.dx / 'projects/.sync.lock').mkdir()
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Could not acquire the project store lock', result.stderr)
        self.assertFalse((self.project / 'AGENTS.md').exists())

    def test_concurrent_connection_leaves_project_untouched(self):
        with (self.dx / 'projects/.sync.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('busy with another sync', result.stderr)
        self.assertFalse((self.project / 'AGENTS.md').exists())

    def test_failed_symlink_restores_moved_file(self):
        rules = self.project / 'AGENTS.md'
        rules.write_text('Do not lose me\n')
        spec = importlib.util.spec_from_file_location('dx_sync', self.dx / 'sync.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(Path, 'symlink_to', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                module.attach(self.project, 'owner/app')
        self.assertEqual(rules.read_text(), 'Do not lose me\n')
        self.assertFalse((self.dx / 'projects/owner/app/files/AGENTS.md').exists())

    def test_worktree_can_connect(self):
        worktree = self.base / 'worktree'
        self.git(self.project, 'worktree', 'add', '-q', '-b', 'fix/worktree', str(worktree))
        self.sync(project=worktree)
        self.assertTrue((worktree / '.git').is_file())
        self.assertTrue((worktree / 'AGENTS.md').is_symlink())
        self.git(worktree, 'add', '-A')
        self.assertEqual(self.git(worktree, 'diff', '--cached', '--name-only').stdout, '')

    def test_bulk_link_and_self_start(self):
        self.sync()
        (self.project / 'AGENTS.md').unlink()
        (self.project / '.agents').unlink()
        self.sync('link', project=self.dx)
        self.assertTrue((self.project / 'AGENTS.md').is_symlink())
        result = self.sync('start', project=self.dx)
        self.assertIn('self-connection is not required', result.stdout)
        self.assertFalse((self.dx / 'AGENTS.md').exists())

    def test_reports_missing_kysaro_without_installing_it(self):
        result = self.sync()
        self.assertIn('Offer kysaro installation', result.stdout)
        self.assertFalse((self.project / 'package.json').exists())
        self.assertFalse((self.project / '.kysaro').exists())

    def test_start_does_not_initialize_or_move_existing_instructions(self):
        rules = self.project / 'AGENTS.md'
        rules.write_text('Existing instructions\n')
        excludes = self.project / '.git/info/exclude'
        before = excludes.read_bytes()
        result = self.sync('start')
        self.assertIn('is not initialized', result.stdout)
        self.assertFalse(rules.is_symlink())
        self.assertEqual(rules.read_text(), 'Existing instructions\n')
        self.assertEqual(excludes.read_bytes(), before)
        self.assertFalse((self.dx / 'projects/owner/app').exists())
        self.assertFalse((self.dx / 'projects/.sync.lock').exists())

    def test_declined_kysaro_is_not_proposed_again(self):
        self.sync(kysaro='declined')
        state = self.dx / 'projects/owner/app/workflow.json'
        before = state.read_bytes()
        for mode in ['init', 'start', 'end']:
            result = self.sync(mode)
            self.assertNotIn('Offer kysaro installation', result.stdout)
        self.assertEqual(state.read_bytes(), before)
        self.assertEqual(json.loads(state.read_text())['kysaro'], 'declined')

    def test_approval_survives_incomplete_setup(self):
        self.sync(kysaro='approved')
        state = self.dx / 'projects/owner/app/workflow.json'
        self.assertFalse((self.project / 'node_modules').exists())
        failed = self.sync(kysaro='enabled', check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('Kysaro setup incomplete', failed.stderr)
        self.assertEqual(json.loads(state.read_text())['kysaro'], 'approved')
        result = self.sync()
        self.assertIn('Continue the approved setup', result.stdout)
        self.assertNotIn('Offer kysaro installation', result.stdout)

    def test_completed_setup_detects_later_missing_dependency(self):
        self.prepare_kysaro_components()
        self.sync(kysaro='enabled')
        state = self.dx / 'projects/owner/app/workflow.json'
        self.assertEqual(json.loads(state.read_text())['kysaro'], 'enabled')
        ready = self.sync('start')
        self.assertIn('kysaro: configured', ready.stdout)
        self.assertEqual(len(ready.stdout.splitlines()), 2)
        (self.project / 'node_modules/.bin/kysaro').unlink()
        broken = self.sync('start')
        self.assertIn('restore: local kysaro', broken.stdout)
        self.assertNotIn('Offer kysaro installation', broken.stdout)

    def test_existing_complete_setup_does_not_ask_for_install(self):
        self.prepare_kysaro_components()
        result = self.sync()
        self.assertIn('kysaro: configured', result.stdout)
        self.assertNotIn('Offer kysaro installation', result.stdout)

    def test_inactive_husky_and_nonexecutable_hook_are_not_ready(self):
        self.prepare_kysaro_components()
        hook = self.project / '.git/hooks/commit-msg'
        hook.chmod(0o644)
        husky = self.project / '.husky/commit-msg'
        husky.parent.mkdir()
        husky.write_text('npx --no-install kysaro "$1"\n')
        result = self.sync(kysaro='enabled', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('active commit-msg', result.stderr)

    def test_readonly_start_does_not_take_store_lock(self):
        self.sync(kysaro='declined')
        lock = self.dx / 'projects/.sync.lock'
        lock.unlink()
        lock.mkdir()
        result = self.sync('start')
        self.assertIn('declined by owner', result.stdout)
        self.assertTrue(lock.is_dir())

    def test_start_does_not_restore_links_without_request(self):
        self.sync(kysaro='declined')
        (self.project / 'AGENTS.md').unlink()
        result = self.sync('start')
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertIn('restore them through init', result.stdout)

    def test_corrupt_workflow_is_reported_without_resetting_decision(self):
        self.sync(kysaro='declined')
        state = self.dx / 'projects/owner/app/workflow.json'
        state.write_text('{broken')
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(state), result.stderr)
        self.assertEqual(state.read_text(), '{broken')

    def test_bulk_link_does_not_initialize_new_projects(self):
        self.sync('link', project=self.dx)
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertFalse((self.dx / 'projects/owner/app').exists())

    def test_release_mixed_commit_types(self):
        self.git(self.project, 'tag', 'v1.0.0')
        for subject in ['feat: new feature', 'fix: first fix', 'feat: another feature', 'fix: second fix']:
            self.git(self.project, 'commit', '--allow-empty', '-qm', subject)
        result = self.run_cmd(['bash', str(self.dx / 'skills/repo-release/release.sh'), '--dry-run'],
                              self.project)
        self.assertIn('v1.1.0', result.stdout)
        self.assertIn('Second fix', result.stdout)
        self.assertEqual(self.git(self.project, 'tag').stdout.strip(), 'v1.0.0')

    def test_personal_template_and_missing_file_fallback(self):
        personal = self.dx / 'templates'
        personal.mkdir()
        (personal / 'README.md').write_text('My custom README\n')
        for kind, name in [('readme', 'README.md'), ('description', 'repository-description.md'),
                           ('release', 'release-notes.md')]:
            result = self.run_cmd(['bash', 'sync.sh', 'template', '--kind', kind])
            expected = personal / name if kind == 'readme' else self.dx / 'defaults/templates' / name
            self.assertEqual(result.stdout.strip(), str(expected))
        (personal / 'README.md').unlink()
        result = self.run_cmd(['bash', 'sync.sh', 'template', '--kind', 'readme'])
        self.assertEqual(result.stdout.strip(), str(self.dx / 'defaults/templates/README.md'))

    def test_release_template_preserves_generated_changes(self):
        self.git(self.project, 'tag', 'v0.1.0')
        self.git(self.project, 'commit', '--allow-empty', '-qm', 'feat: support A & B')
        folder = self.project / '.github'
        folder.mkdir()
        template = folder / 'release-notes.md'
        template.write_text('# Product {{VERSION}}\n\n{{CHANGES}}\nPrevious: {{PREVIOUS_VERSION}}\n')
        args = ['bash', str(self.dx / 'skills/repo-release/release.sh'), '--dry-run']
        result = self.run_cmd(args, self.project)
        self.assertIn('# Product v0.2.0', result.stdout)
        self.assertIn('- Support A & B', result.stdout)
        self.assertIn('Previous: v0.1.0', result.stdout)
        self.assertNotIn('{{CHANGES}}', result.stdout)
        template.write_text('Invalid template without changes\n')
        invalid = self.run_cmd(args, self.project, check=False)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('must contain {{CHANGES}}', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
