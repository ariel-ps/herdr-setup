import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/installer'))
from output import message


class OutputTests(unittest.TestCase):
    def test_color_only_on_capable_terminal_and_errors_use_stderr(self):
        for tty, env, colored in [
            (True, {'TERM': 'xterm-256color'}, True),
            (False, {'TERM': 'xterm-256color'}, False),
            (True, {'TERM': 'dumb'}, False),
            (True, {'TERM': 'xterm', 'NO_COLOR': ''}, False),
        ]:
            with self.subTest(tty=tty, env=env):
                stdout, stderr = io.StringIO(), io.StringIO()
                stdout.isatty = stderr.isatty = lambda: tty
                with patch.dict(os.environ, env, clear=True), \
                     patch('sys.stdout', stdout), patch('sys.stderr', stderr):
                    message('OK', 'Ready')
                    message('ERROR', 'Download failed', error=True, color='31')
                self.assertEqual('\033[' in stdout.getvalue(), colored)
                self.assertEqual('\033[' in stderr.getvalue(), colored)
                self.assertNotIn('Download failed', stdout.getvalue())
                self.assertIn('Download failed', stderr.getvalue())
