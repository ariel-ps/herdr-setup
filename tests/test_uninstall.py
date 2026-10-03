import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('uninstall', ROOT / 'src/installer/uninstall.py')
uninstall = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'src/installer'))
spec.loader.exec_module(uninstall)
installer = importlib.import_module('main')


class UninstallShellTests(unittest.TestCase):
    def test_strip_block_removes_managed_section(self):
        original = f"before\n{installer.BEGIN}\nsource /tmp/x\n{installer.END}\nafter\n"
        text, removed = uninstall.strip_block(original, installer.BEGIN, installer.END)
        self.assertTrue(removed)
        self.assertEqual(text, 'before\nafter\n')

    def test_strip_block_noop_when_missing(self):
        text, removed = uninstall.strip_block('plain\n', installer.BEGIN, installer.END)
        self.assertFalse(removed)
        self.assertEqual(text, 'plain\n')

    def test_remove_shell_blocks_writes_file(self):
        with tempfile.TemporaryDirectory() as temp:
            rc = Path(temp) / '.zshrc'
            rc.write_text(
                f'keep\n{installer.BEGIN}\nsource x\n{installer.END}\n'
            )
            changed = uninstall.remove_shell_blocks([rc], include_tools=False)
            self.assertEqual(changed, [rc])
            self.assertEqual(rc.read_text(), 'keep\n')


if __name__ == '__main__':
    unittest.main()
