import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'src/installer/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_fedora_installs_missing_providers_and_uses_linux_binary(self):
        manifest = {'packages': {'fedora': ['/usr/bin/curl', 'jq']}, 'tools': {}, 'herdr': {'version': '0.9.3'}}
        for uid in [0, 1000]:
            with self.subTest(uid=uid), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'dependencies.json').write_text(json.dumps(manifest))
                with patch.dict(os.environ), patch.object(bootstrap, 'ROOT', root), \
                     patch.object(bootstrap.platform, 'system', return_value='Linux'), \
                     patch.object(bootstrap.os, 'geteuid', return_value=uid, create=True), \
                     patch.object(bootstrap.shutil, 'which', side_effect=lambda name: '/usr/bin/dnf' if name == 'dnf' else None), \
                     patch.object(bootstrap.subprocess, 'run', side_effect=lambda args, **kw: SimpleNamespace(returncode=0 if args[-1] == '/usr/bin/curl' else 1)), \
                     patch.object(bootstrap, 'run') as run, patch.object(bootstrap, 'install_herdr') as install:
                    bootstrap.main()
                    run.assert_called_once_with(*([] if uid == 0 else ['sudo']), 'dnf', 'install', '-y', '--setopt=install_weak_deps=False', 'jq')
                    install.assert_called_once_with(manifest['herdr'], 'linux')

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
