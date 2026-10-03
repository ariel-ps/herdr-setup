import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/quick-actions'
sys.path.insert(0, str(ROOT / 'src/installer'))
import main as installer


class ControlPanelTests(unittest.TestCase):
    def test_install_preserves_custom_menus_and_skips_disabled_plus(self):
        for enabled in (True, False):
            with tempfile.TemporaryDirectory(prefix='panel install ') as temp:
                root = Path(temp)
                shutil.copytree(ROOT / 'config', root / 'config')
                (root / 'dependencies.json').write_text(json.dumps({
                    'schema_version': 2, 'packages': {}, 'herdr': {'version': '0.9.3'},
                    'plugins': [{'id': 'cloudmanic.herdr-plus', 'name': 'Herdr Plus',
                                 'repository': 'cloudmanic/herdr-plus', 'ref': 'a' * 40, 'enabled': enabled}]}))
                panel = root / 'preferences/herdr/plugins/config/cloudmanic.herdr-plus/quick-actions'
                panel.mkdir(parents=True)
                custom = panel / 'herdr-setup-tools.toml'
                custom.write_text('name = "My tools"\ncommand = "true"\n')
                env = {'HOME': temp, 'SHELL': '/bin/bash', 'HERDR_CONFIG_PATH': '', 'LG_CONFIG_FILE': '',
                       'XDG_CONFIG_HOME': str(root / 'preferences'), 'XDG_DATA_HOME': str(root / 'data')}
                with patch.dict(os.environ, env), patch.object(installer, 'ROOT', root), \
                     patch.object(installer, 'install_plugins'), \
                     patch.object(installer.shutil, 'which', return_value='/bin/bash'), \
                     patch.object(installer, 'run', side_effect=lambda *a, **kw:
                                  str(root / 'lazygit') if a[0] == 'lazygit' else 'herdr 0.9.3'):
                    installer.main(['--no-shell'])
                    installer.main(['--no-shell'])
                self.assertEqual(custom.read_text(), 'name = "My tools"\ncommand = "true"\n')
                self.assertEqual(len(list(panel.glob('*.toml'))), 5 if enabled else 1)

    def test_templates_and_live_action_filtering(self):
        templates = {p.stem: tomllib.loads(p.read_text()) for p in CONFIG.glob('*.toml')}
        self.assertEqual(len(templates), 5)
        for config in templates.values():
            self.assertTrue(config['name'] and config['description'])
            subprocess.run(['sh', '-n', '-c', config['command']], check=True)
        with tempfile.TemporaryDirectory(prefix='panel user ') as temp:
            root = Path(temp)
            tool = root / 'herdr'
            tool.write_text(f'#!{sys.executable}\n' + '''import json,os,sys
from pathlib import Path
if sys.argv[1:3] == ['plugin', 'list']:
    print(Path(os.environ['TEST_PLUGINS']).read_text())
else:
    Path(os.environ['TEST_CALL']).write_text(json.dumps(sys.argv[1:]))
    sys.exit(int(os.environ.get('TEST_EXIT', '0')))
''')
            tool.chmod(0o755)
            sound = root / 'herdr-sound'
            sound.write_bytes(tool.read_bytes())
            sound.chmod(0o755)
            plugins = root / 'plugins.json'
            platforms = ['macos', 'linux']
            plugins.write_text(json.dumps({'result': {'plugins': [
                {'plugin_id': 'ready', 'name': 'Ready', 'enabled': True, 'platforms': platforms,
                 'actions': [{'id': 'open', 'title': 'Open tool'},
                             {'id': 'windows', 'title': 'Windows only', 'platforms': ['windows']}]},
                {'plugin_id': 'disabled', 'name': 'Disabled', 'enabled': False,
                 'actions': [{'id': 'open', 'title': 'Should not appear'}]},
            ]}}))
            env = {**os.environ, 'HOME': temp, 'HERDR_BIN_PATH': str(tool),
                   'PATH': temp + ':' + os.environ['PATH'],
                   'TEST_PLUGINS': str(plugins), 'TEST_CALL': str(root / 'call.json')}
            action = templates['herdr-setup-actions']
            result = subprocess.run(['sh', '-c', action['options_command']], env=env,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, 'ready.open\tReady / Open tool\n')
            plugins.write_text(json.dumps({'result': {'plugins': []}}))
            self.assertEqual(subprocess.check_output(['sh', '-c', action['options_command']], env=env), b'')
            # Selection is a literal argument, never executable shell input.
            value = 'ready.open; touch unexpected'
            result = subprocess.run(['sh', '-c', action['command'] + ' ' + shlex.quote(value)],
                                    env=env, cwd=root, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads((root / 'call.json').read_text()), ['plugin', 'action', 'invoke', value])
            self.assertFalse((root / 'unexpected').exists())
            sound = templates['herdr-setup-sounds']
            for option, expected in [('flash-on', ['set', 'flash', 'on']),
                                     ('sprite-off', ['set', 'sprite', 'off']), ('disable', ['disable'])]:
                result = subprocess.run(['sh', '-c', sound['command'] + ' ' + shlex.quote(option)],
                                        env=env, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(json.loads((root / 'call.json').read_text()), expected)
            result = subprocess.run(['sh', '-c', sound['command'] + ' status'],
                                    env={**env, 'TEST_EXIT': '7'}, capture_output=True)
            self.assertEqual(result.returncode, 7)


if __name__ == '__main__':
    unittest.main()
