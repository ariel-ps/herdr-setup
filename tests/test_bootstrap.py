import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'src/installer/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_missing_herdr_installs_into_new_home_on_both_platforms(self):
        binary = b'#!/bin/sh\necho herdr\n'
        checksum = hashlib.sha256(binary).hexdigest()
        herdr = {'version': '0.9.3', 'downloads': {
            'linux-aarch64': {'sha256': checksum},
            'macos-aarch64': {'sha256': checksum},
        }}
        def download(*args):
            Path(args[-1]).write_bytes(binary)
        for system in ['linux', 'macos']:
            with self.subTest(system=system), tempfile.TemporaryDirectory(prefix='fresh user ') as temp:
                with patch.dict(os.environ, {'HOME': temp}), patch.object(bootstrap.shutil, 'which', return_value=None), \
                     patch.object(bootstrap.platform, 'machine', return_value='arm64'), patch.object(bootstrap, 'run', side_effect=download):
                    bootstrap.install_herdr(herdr, system)
                installed = Path(temp) / '.local/bin/herdr'
                self.assertEqual(installed.read_bytes(), binary)
                self.assertTrue(os.access(installed, os.X_OK))

    def test_bad_download_is_never_installed(self):
        herdr = {'version': '0.9.3', 'downloads': {'linux-aarch64': {'sha256': 'invalid'}}}
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {'HOME': temp}), patch.object(bootstrap.shutil, 'which', return_value=None), \
                 patch.object(bootstrap.platform, 'machine', return_value='arm64'), \
                 patch.object(bootstrap, 'run', side_effect=lambda *args: Path(args[-1]).write_bytes(b'incomplete')):
                with self.assertRaisesRegex(SystemExit, 'checksum'):
                    bootstrap.install_herdr(herdr, 'linux')
            self.assertFalse((Path(temp) / '.local/bin/herdr').exists())
