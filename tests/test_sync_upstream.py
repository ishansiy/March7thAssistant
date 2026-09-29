"""Exercise production sync against real repositories, without GitHub writes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/sync_upstream.sh'
BASH = shutil.which('bash')
if BASH is None and os.name == 'nt':
    candidate = Path(shutil.which('git')).resolve().parent.parent / 'bin/bash.exe'
    if candidate.exists():
        BASH = str(candidate)


@unittest.skipUnless(BASH, 'Bash is required by the production workflow')
class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Sync test')
        self.git('config', 'user.email', 'sync@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.write('app.py', 'base\n')
        self.write('.github/workflows/build.yml', 'base workflow\n')
        self.write('.github/workflows/deleted.yml', 'base deleted workflow\n')
        self.commit('base')
        self.git('branch', 'upstream')

    def git(self, *args, check=True):
        return subprocess.run(['git', *args], cwd=self.repo, text=True,
                              encoding='utf-8', capture_output=True, check=check).stdout.strip()

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def sync(self):
        env = {**os.environ, 'UPSTREAM_REPOSITORY': '.', 'UPSTREAM_BRANCH': 'upstream'}
        return subprocess.run([BASH, str(SCRIPT)], cwd=self.repo, env=env,
                              text=True, encoding='utf-8', capture_output=True)

    def prepare_conflicts(self, application=False):
        self.write('.github/workflows/build.yml', 'custom deployment\n')
        self.git('rm', '.github/workflows/deleted.yml')
        if application:
            self.write('app.py', 'custom application\n')
        self.commit('custom changes')
        self.before = self.git('rev-parse', 'HEAD')
        self.git('switch', 'upstream')
        self.write('.github/workflows/build.yml', 'upstream build\n')
        self.write('.github/workflows/deleted.yml', 'modified upstream workflow\n')
        self.write('.github/workflows/new.yml', 'new upstream automation\n')
        self.write('app.py', 'updated application\n')
        self.commit('upstream update')
        self.git('switch', 'main')

    def test_workflow_conflicts_keep_local_workflows_and_merge_application(self):
        self.prepare_conflicts()
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('show', 'HEAD:app.py'), 'updated application')
        self.assertEqual(self.git('diff', self.before, 'HEAD', '--', '.github/workflows'), '')
        self.assertFalse((self.repo / '.github/workflows/new.yml').exists())
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.git('merge-base', '--is-ancestor', 'upstream', 'HEAD')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_application_conflict_aborts_without_losing_local_changes(self):
        self.prepare_conflicts(application=True)
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('application conflicts need review', result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.before)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('show', 'HEAD:app.py'), 'custom application')
        self.assertFalse((self.repo / '.git/MERGE_HEAD').exists())

    def test_clean_upstream_update_is_merged(self):
        self.git('switch', 'upstream')
        self.write('app.py', 'updated application\n')
        self.commit('upstream update')
        self.git('switch', 'main')
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('show', 'HEAD:app.py'), 'updated application')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_dirty_checkout_is_preserved(self):
        self.write('app.py', 'uncommitted work\n')
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clean checkout', result.stderr)
        self.assertEqual((self.repo / 'app.py').read_text(), 'uncommitted work\n')


if __name__ == '__main__':
    unittest.main()
