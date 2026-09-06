import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        (self.repo / 'skills/demo').mkdir(parents=True)
        shutil.copy2(ROOT / 'sync.sh', self.repo / 'sync.sh')
        self.target = self.root / 'target'

    def run_sync(self, *args):
        return subprocess.run(['bash', str(self.repo / 'sync.sh'), '-t', str(self.target), *args], capture_output=True, text=True)

    def test_dry_run_does_not_create_destination(self):
        self.assertEqual(self.run_sync('--dry-run').returncode, 0)
        self.assertFalse(self.target.exists())

    def test_conflicts_are_preserved(self):
        self.target.mkdir()
        item = self.target / 'demo'
        item.write_text('user data')
        self.assertEqual(self.run_sync().returncode, 1)
        self.assertEqual(item.read_text(), 'user data')
        item.unlink()
        item.mkdir()
        self.assertEqual(self.run_sync().returncode, 1)
        self.assertEqual(list(item.iterdir()), [])
        item.rmdir()
        item.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_sync().returncode, 1)
        self.assertEqual(item.readlink(), self.root / 'missing')

    def test_idempotent_sync_and_owned_orphan_cleanup(self):
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual((self.target / 'demo').resolve(), self.repo / 'skills/demo')
        orphan = self.target / 'old'
        orphan.symlink_to(self.repo / 'skills/old')
        self.assertEqual(self.run_sync('--dry-run').returncode, 0)
        self.assertTrue(orphan.is_symlink())
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertFalse(orphan.is_symlink())

    def test_unlink_only_removes_owned_links(self):
        self.run_sync()
        foreign = self.target / 'foreign'
        foreign.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_sync('--unlink', '--dry-run').returncode, 0)
        self.assertTrue((self.target / 'demo').is_symlink())
        self.assertEqual(self.run_sync('--unlink').returncode, 0)
        self.assertFalse((self.target / 'demo').is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_invalid_options_fail_before_writing(self):
        for args in [('--install-hook',), ('--status', '--unlink'), ('--target',)]:
            self.assertEqual(self.run_sync(*args).returncode, 2)
            self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
