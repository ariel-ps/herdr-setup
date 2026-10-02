import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_manifest_and_patch_integrity(self):
        installer.validate_lock(json.loads((ROOT / 'dependencies.json').read_text()))

    def test_shell_install_preserves_settings_and_is_repeatable(self):
        original = 'export EDITOR=vim\nalias ll="ls -l"\n'
        added = installer.shell_block(original)
        self.assertTrue(added.startswith(original))
        self.assertEqual(installer.shell_block(added), added)
        self.assertEqual(added.count(installer.BEGIN), 1)

    def test_existing_manual_loader_is_not_duplicated(self):
        with self.assertRaisesRegex(ValueError, 'manual'):
            installer.shell_block('source ~/Documents/projects/dev-env/init.zsh\n')

    def test_malformed_shell_block_is_not_overwritten(self):
        for content in [installer.BEGIN, installer.END + '\n' + installer.BEGIN]:
            with self.assertRaises(ValueError):
                installer.shell_block(content)

    def test_existing_configuration_backed_up_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / 'config.toml'
            config.write_text('old')
            writer = installer.Writer(root / 'backups')
            writer.write(config, 'new')
            writer.write(config, 'new')
            self.assertEqual(config.read_text(), 'new')
            self.assertEqual(len(writer.records), 1)
            self.assertEqual(Path(writer.records[0]['backup']).read_text(), 'old')

    def test_symlink_target_not_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'original'
            target.write_text('original')
            link = root / 'config'
            link.symlink_to(target)
            writer = installer.Writer(root / 'backups')
            writer.write(link, 'new')
            self.assertEqual(target.read_text(), 'original')
            self.assertFalse(link.is_symlink())
            self.assertTrue(Path(writer.records[0]['backup']).is_symlink())

    def test_annotated_release_tag_resolves_to_commit(self):
        output = 'a' * 40 + '\trefs/tags/v1.0\n' + 'b' * 40 + '\trefs/tags/v1.0^{}'
        with patch.object(installer, 'run', return_value=output):
            self.assertEqual(installer.resolve_ref('owner/repo', 'v1.0'), 'b' * 40)

    def test_dry_run_does_not_run_commands(self):
        with patch.object(installer, 'run', side_effect=AssertionError('unexpected command')):
            self.assertEqual(installer.main(['--dry-run']), 0)


if __name__ == '__main__':
    unittest.main()
