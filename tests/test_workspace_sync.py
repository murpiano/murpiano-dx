"""Real Git repositories prove workspace sync without contacting GitHub."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workspace_sync_test', SOURCE / 'workspace_sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class WorkspaceSync(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dx-sync-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=str(self.base / 'gitconfig'),
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.remote = self.base / 'backup.git'
        self.git(self.base, 'init', '--bare', '-b', 'main', str(self.remote))
        self.first = self.base / 'first'
        self.first.mkdir()
        self.git(self.first, 'init', '-b', 'main')
        self.git(self.first, 'config', 'user.name', 'Test')
        self.git(self.first, 'config', 'user.email', 'test@example.invalid')
        (self.first / 'config').mkdir()
        (self.first / 'config/machine.json').write_text('{}\n')
        (self.first / '.murpiano-dx-workspace').write_text('workspace\n')
        (self.first / 'rules').mkdir()
        (self.first / 'rules/git.md').write_text('original rules\n')
        self.git(self.first, 'remote', 'add', 'origin', str(self.remote))
        sync.synchronize(self.first)
        self.second = self.base / 'second'
        self.git(self.base, 'clone', str(self.remote), str(self.second))

    def git(self, root, *args, check=True):
        return subprocess.run(['git', '-C', str(root), *args], env=self.env,
                              text=True, capture_output=True, check=check, timeout=10)

    def test_gets_remote_changes_without_local_changes(self):
        (self.second / 'rules/readme.md').write_text('other machine\n')
        sync.synchronize(self.second)
        sync.synchronize(self.first)
        self.assertEqual((self.first / 'rules/readme.md').read_text(), 'other machine\n')

    def test_merges_both_machines_and_excludes_runtime_files(self):
        (self.first / 'local.md').write_text('local data\n')
        (self.second / 'remote.md').write_text('remote data\n')
        sync.synchronize(self.second)
        sync.synchronize(self.first)
        sync.synchronize(self.second)
        self.assertEqual((self.second / 'local.md').read_text(), 'local data\n')
        self.assertEqual((self.first / 'remote.md').read_text(), 'remote data\n')
        (self.first / 'logs/autosync.log').write_text('diagnostic\n')
        (self.first / 'projects').mkdir()
        (self.first / 'projects/.sync.lock').touch()
        sync.synchronize(self.first)
        tracked = self.git(self.first, 'ls-files').stdout
        self.assertNotIn('logs/', tracked)
        self.assertNotIn('.sync.lock', tracked)

    def test_conflict_retains_local_and_remote_commits(self):
        (self.first / 'rules/git.md').write_text('first machine\n')
        (self.second / 'rules/git.md').write_text('second machine\n')
        sync.synchronize(self.second)
        remote_head = self.git(self.remote, 'rev-parse', 'main').stdout
        with self.assertRaisesRegex(RuntimeError, 'commits are preserved'):
            sync.synchronize(self.first)
        self.assertEqual((self.first / 'rules/git.md').read_text(), 'first machine\n')
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main').stdout, remote_head)
        self.assertFalse((self.first / '.git/MERGE_HEAD').exists())
        self.assertEqual(self.git(self.first, 'status', '--porcelain').stdout, '')
        self.assertEqual(self.git(self.first, 'show', 'origin/main:rules/git.md').stdout,
                         'second machine\n')

    def test_offline_keeps_local_commit_and_retries(self):
        (self.first / 'note.md').write_text('offline note\n')
        self.git(self.first, 'remote', 'set-url', 'origin', str(self.base / 'missing.git'))
        with self.assertRaises(RuntimeError):
            sync.synchronize(self.first)
        self.assertEqual(self.git(self.first, 'show', 'HEAD:note.md').stdout, 'offline note\n')
        self.git(self.first, 'remote', 'set-url', 'origin', str(self.remote))
        sync.synchronize(self.first)
        self.assertEqual(self.git(self.remote, 'show', 'main:note.md').stdout, 'offline note\n')

    def test_local_only_workspace_still_commits(self):
        self.git(self.first, 'remote', 'remove', 'origin')
        (self.first / 'note.md').write_text('local note\n')
        sync.synchronize(self.first)
        self.assertEqual(self.git(self.first, 'show', 'HEAD:note.md').stdout, 'local note\n')

    def test_unmarked_source_repository_is_untouched(self):
        (self.first / '.murpiano-dx-workspace').unlink()
        before = self.git(self.first, 'rev-parse', 'HEAD').stdout
        (self.first / 'source.py').write_text('print(1)\n')
        sync.synchronize(self.first)
        self.assertEqual(self.git(self.first, 'rev-parse', 'HEAD').stdout, before)
        self.assertNotIn('source.py', self.git(self.first, 'ls-files').stdout)

    def test_unfinished_merge_is_not_touched(self):
        marker = self.first / '.git/MERGE_HEAD'
        marker.write_text(self.git(self.first, 'rev-parse', 'HEAD').stdout)
        (self.first / 'note.md').write_text('work in progress\n')
        with self.assertRaisesRegex(RuntimeError, 'unfinished Git operation'):
            sync.synchronize(self.first)
        self.assertTrue(marker.exists())
        self.assertNotIn('note.md', self.git(self.first, 'ls-files').stdout)

    def hook(self, event, root=None):
        root = root or self.first
        for name in ('session_hook.py', 'workspace_sync.py'):
            shutil.copy2(SOURCE / name, root / name)
        return subprocess.run([sys.executable, '-B', str(root / 'session_hook.py'), event],
                              env=self.env, input=json.dumps({'cwd': str(root)}),
                              text=True, capture_output=True, check=True, timeout=10)

    def test_session_end_pushes_once_after_hook_returns_without_manual_end(self):
        (self.first / 'automatic.md').write_text('no manual sync\n')
        self.hook('end')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = self.git(self.remote, 'show', 'main:automatic.md', check=False)
            log = self.first / 'logs/session-sync.log'
            if result.returncode == 0 and log.exists() and 'Workspace synchronized.' in log.read_text():
                self.assertEqual(result.stdout, 'no manual sync\n')
                break
            time.sleep(.1)
        else:
            self.fail('SessionEnd did not push the saved file')
        self.assertEqual(log.read_text().count('Workspace synchronized.'), 1)
        self.assertNotIn('logs/', self.git(self.first, 'ls-files').stdout)

    def test_session_start_gets_updates_and_resends_pending_local_data(self):
        (self.second / 'other-machine.md').write_text('remote change\n')
        sync.synchronize(self.second)
        (self.first / 'pending.md').write_text('saved before an interrupted shutdown\n')
        result = self.hook('start')
        output = json.loads(result.stdout)
        self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'SessionStart')
        self.assertIn('--local', output['hookSpecificOutput']['additionalContext'])
        self.assertEqual((self.first / 'other-machine.md').read_text(), 'remote change\n')
        self.assertEqual(self.git(self.remote, 'show', 'main:pending.md').stdout,
                         'saved before an interrupted shutdown\n')

    def test_session_start_offline_reports_pending_without_blocking(self):
        self.git(self.first, 'remote', 'set-url', 'origin', str(self.base / 'unreachable.git'))
        (self.first / 'pending.md').write_text('pending data\n')
        result = self.hook('start')
        self.assertIn('sync pending', json.loads(result.stdout)['hookSpecificOutput']['additionalContext'])
        self.assertEqual(self.git(self.first, 'show', 'HEAD:pending.md').stdout, 'pending data\n')

    def test_hooks_ignore_unmarked_source_repository(self):
        (self.first / '.murpiano-dx-workspace').unlink()
        head = self.git(self.first, 'rev-parse', 'HEAD').stdout
        self.assertEqual(self.hook('start').stdout, '')
        self.assertEqual(self.hook('end').stdout, '')
        self.assertEqual(self.git(self.first, 'rev-parse', 'HEAD').stdout, head)

    def test_backup_choices_public_private_and_decline(self):
        self.git(self.first, 'remote', 'remove', 'origin')
        for visibility in ('public', 'private'):
            answers = iter(['yes', visibility, 'my-workspace'])
            with patch.dict(os.environ, GITHUB_OWNER='owner'), \
                    patch.object(sync.subprocess, 'run') as run, \
                    patch.object(sync, 'synchronize'):
                run.return_value = subprocess.CompletedProcess([], 1, '', '')
                sync.configure_remote(self.first, lambda _: next(answers))
                command = run.call_args_list[-1].args[0]
                self.assertIn('--' + visibility, command)
                self.assertIn('owner/my-workspace', command)
            settings = self.first / 'config/backup.json'
            self.assertEqual(json.loads(settings.read_text())['visibility'], visibility)
            settings.unlink()
        with patch.object(sync, 'synchronize'):
            sync.configure_remote(self.first, lambda _: '')
        self.assertFalse(json.loads(settings.read_text())['enabled'])
        sync.configure_remote(self.first, lambda _: self.fail('Decline must be remembered'))

    def test_existing_origin_is_preserved_without_questions(self):
        sync.configure_remote(self.first, lambda _: self.fail('Origin already configured'))
        self.assertEqual(self.git(self.first, 'remote', 'get-url', 'origin').stdout.strip(), str(self.remote))

    def test_existing_repository_url_is_supported(self):
        self.git(self.first, 'remote', 'remove', 'origin')
        answers = iter(['no', str(self.remote)])
        sync.configure_remote(self.first, lambda _: next(answers))
        self.assertEqual(self.git(self.first, 'remote', 'get-url', 'origin').stdout.strip(), str(self.remote))
        self.assertTrue(json.loads((self.first / 'config/backup.json').read_text())['enabled'])


if __name__ == '__main__':
    unittest.main()
