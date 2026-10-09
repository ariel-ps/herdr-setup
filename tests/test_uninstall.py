import importlib.util
import json
import os
import sys
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

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

    def test_strip_block_rejects_reversed_markers(self):
        original = f"tail\n{installer.END}\n{installer.BEGIN}\nsource x\n"
        with self.assertRaises(ValueError):
            uninstall.strip_block(original, installer.BEGIN, installer.END)

    def test_remove_shell_blocks_writes_file(self):
        with tempfile.TemporaryDirectory() as temp:
            rc = Path(temp) / '.zshrc'
            rc.write_text(
                f'keep\n{installer.BEGIN}\nsource x\n{installer.END}\n'
            )
            changed = uninstall.remove_shell_blocks([rc], include_tools=False)
            self.assertEqual(changed, [rc])
            self.assertEqual(rc.read_text(), 'keep\n')


class UninstallPluginTests(unittest.TestCase):
    @patch.object(uninstall.subprocess, 'run')
    @patch.object(uninstall.shutil, 'which', return_value='/usr/bin/herdr')
    def test_uninstall_skips_missing_plugins(self, _which, run):
        listing = json.dumps({'result': {'plugins': [{'plugin_id': 'a.example'}]}})
        run.side_effect = [
            mock.Mock(stdout=listing),
            mock.Mock(returncode=0),
        ]
        removed = uninstall.uninstall_plugins(['a.example', 'b.missing'])
        self.assertEqual(removed, 1)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0], ['herdr', 'plugin', 'uninstall', 'a.example'])


class UninstallWrapperTests(unittest.TestCase):
    def test_uses_uv_when_system_python_is_too_old(self):
        with tempfile.TemporaryDirectory() as temp:
            tools = Path(temp)
            python = tools / 'python3'
            python.write_text('#!/bin/sh\n[ "$1" = "-c" ] && exit 1\nexit 99\n')
            python.chmod(0o755)
            capture = tools / 'uv-args.json'
            uv = tools / 'uv'
            uv.write_text(
                f'#!{sys.executable}\n'
                'import json, os, sys\n'
                'from pathlib import Path\n'
                'Path(os.environ["TEST_CALLS"]).write_text(json.dumps(sys.argv[1:]))\n'
                'sys.exit(23)\n'
            )
            uv.chmod(0o755)
            result = subprocess.run(
                ['sh', str(ROOT / 'uninstall.sh'), '--dry-run'],
                env={**os.environ, 'PATH': f'{tools}:/usr/bin:/bin', 'TEST_CALLS': str(capture)},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertEqual(json.loads(capture.read_text()), [
                'run', '--no-project', '--python', '3.11', 'python',
                str(ROOT / 'src/installer/uninstall.py'), '--dry-run',
            ])


class ResolveManifestTests(unittest.TestCase):
    def test_prefers_newer_checkout_manifest_over_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / 'checkout'
            data = Path(temp) / 'data'
            checkout.mkdir()
            (data / 'herdr-setup').mkdir(parents=True)
            bundled = checkout / 'dependencies.json'
            cached = data / 'herdr-setup' / 'dependencies.json'
            bundled.write_text('{"checkout": true}')
            cached.write_text('{"cached": true}')
            base = time.time() - 10
            os.utime(cached, (base, base))
            os.utime(bundled, (base + 5, base + 5))
            with patch.object(uninstall, 'ROOT', checkout), patch.dict(os.environ, {'XDG_DATA_HOME': str(data)}):
                self.assertEqual(uninstall.resolve_manifest(None), bundled.resolve())

    def test_prefers_cache_when_it_is_newer_than_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / 'checkout'
            data = Path(temp) / 'data'
            checkout.mkdir()
            (data / 'herdr-setup').mkdir(parents=True)
            bundled = checkout / 'dependencies.json'
            cached = data / 'herdr-setup' / 'dependencies.json'
            bundled.write_text('{}')
            cached.write_text('{}')
            base = time.time() - 10
            os.utime(bundled, (base, base))
            os.utime(cached, (base + 5, base + 5))
            with patch.object(uninstall, 'ROOT', checkout), patch.dict(os.environ, {'XDG_DATA_HOME': str(data)}):
                self.assertEqual(uninstall.resolve_manifest(None), cached.resolve())


if __name__ == '__main__':
    unittest.main()
