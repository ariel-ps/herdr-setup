import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurlInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='new user ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.archive = self.root / 'fixture.tar.gz'
        self.env = {**os.environ, 'HOME': str(self.root), 'XDG_DATA_HOME': str(self.root / 'data'),
                    'PATH': str(self.bin) + ':' + os.environ['PATH'], 'GH_TOKEN': '', 'GITHUB_TOKEN': '',
                    'HERDR_SETUP_REF': 'main', 'TEST_ARCHIVE': str(self.archive),
                    'TEST_CALLS': str(self.root / 'curl-args.json')}
        self.script = (ROOT / 'install.sh').read_text()
        self.write_executable('gh', '#!/bin/sh\nexit 1\n')
        self.write_executable('curl', f'#!{sys.executable}\n' + '''import json, os, shutil, sys
from pathlib import Path
Path(os.environ['TEST_CALLS']).write_text(json.dumps(sys.argv[1:]))
if os.environ.get('TEST_DOWNLOAD_FAIL'):
    sys.exit(22)
shutil.copyfile(os.environ['TEST_ARCHIVE'], sys.argv[sys.argv.index('--output') + 1])
''')

    def write_executable(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def archive_files(self, files=None):
        files = files or {
            'release/install.sh': self.script,
            'release/dependencies.json': '{}',
            'release/src/installer/bootstrap.py': '',
            'release/src/installer/main.py': 'import json,sys\nfrom pathlib import Path\nprint(json.dumps({"file":str(Path(__file__).resolve()),"args":sys.argv[1:]}))\n',
        }
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, contents in files.items():
                data = contents.encode()
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))

    def invoke(self, *args):
        return subprocess.run(['sh', '-s', '--', *args], input=self.script, text=True,
                              cwd=self.root, env=self.env, capture_output=True)

    def test_pipe_install_cleans_source_and_forwards_arguments(self):
        self.archive_files()
        result = self.invoke('--no-shell')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout.splitlines()[-1])
        self.assertFalse(Path(output['file']).exists())
        self.assertFalse((self.root / 'data').exists())
        self.assertEqual(output['args'], ['--no-shell'])

    def test_preview_does_not_create_persistent_installation(self):
        self.archive_files()
        result = self.invoke('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'data').exists())

    def test_download_failure_does_not_run_installer(self):
        self.env['TEST_DOWNLOAD_FAIL'] = '1'
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'data').exists())

    def test_archive_traversal_is_rejected(self):
        self.archive_files({'../outside': 'unexpected'})
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unsafe paths', result.stderr)

    def test_private_token_not_in_curl_arguments(self):
        self.archive_files()
        self.env['GH_TOKEN'] = 'test-only-token'
        self.env['HERDR_SETUP_REF'] = 'v0.1.0'
        result = self.invoke('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.root / 'curl-args.json').read_text()
        self.assertNotIn(self.env['GH_TOKEN'], calls)
        self.assertIn('/tarball/v0.1.0', calls)

    def test_truncated_pipe_does_not_start_download(self):
        result = subprocess.run(['sh'], input=self.script[:len(self.script)//2], text=True,
                                cwd=self.root, env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'curl-args.json').exists())


if __name__ == '__main__':
    unittest.main()
