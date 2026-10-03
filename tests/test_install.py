import importlib.util
import io
import sys
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'src/installer/main.py')
installer = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / "src/installer"))
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_popup_preserves_config_and_custom_shortcuts(self):
        original = '# user settings\nonboarding = true\n[keys]\nprefix = "ctrl+a"\n'
        updated = installer.with_lazygit_popup(original)
        self.assertTrue(updated.startswith(original))
        self.assertEqual(installer.with_lazygit_popup(updated), updated)
        self.assertTrue(tomllib.loads(updated)['onboarding'])
        self.assertEqual(tomllib.loads(updated)['keys']['command'][0]['key'], ['cmd+shift+g', 'prefix+d'])
        for custom in [original + 'zoom = "prefix+d"\n', original + 'command = []\n',
                       original + '[[keys.command]]\nkey = "prefix+d"\ncommand = "my-tool"\n']:
            self.assertEqual(installer.with_lazygit_popup(custom), custom)

    def test_lazygit_config_is_preserved_and_backed_up_on_replace(self):
        with tempfile.TemporaryDirectory(prefix='git user ') as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'config', root / 'config')
            (root / 'dependencies.json').write_text(json.dumps({
                'schema_version': 2, 'plugins': [], 'packages': {}, 'herdr': {'version': '0.9.3'}}))
            git_config = root / 'git preferences/config.yml'
            git_config.parent.mkdir()
            git_config.write_text('gui:\n  sidePanelWidth: 0.4\n')
            env = {'HOME': temp, 'SHELL': '/bin/bash', 'HERDR_CONFIG_PATH': '', 'LG_CONFIG_FILE': '',
                   'XDG_CONFIG_HOME': str(root / 'preferences'), 'XDG_DATA_HOME': str(root / 'data')}
            with patch.dict(os.environ, env), patch.object(installer, 'ROOT', root), \
                 patch.object(installer.shutil, 'which', return_value='/bin/bash'), \
                 patch.object(installer, 'run', side_effect=lambda *a, **kw:
                              str(git_config.parent) if a[0] == 'lazygit' else 'herdr 0.9.3'):
                installer.main(['--no-shell'])
                self.assertEqual(git_config.read_text(), 'gui:\n  sidePanelWidth: 0.4\n')
                installer.main(['--no-shell', '--replace-config'])
                self.assertEqual(git_config.read_text(), (root / 'config/lazygit.yml').read_text())
                backups = list((root / 'data/herdr-setup/backups').glob('*/*-config.yml'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(), 'gui:\n  sidePanelWidth: 0.4\n')

    def test_folder_helpers_work_in_bash_and_zsh_without_overriding_aliases(self):
        with tempfile.TemporaryDirectory(prefix='folder user ') as temp:
            root = Path(temp)
            tools = root / 'tools'
            tools.mkdir()
            for name in ('eza', 'batcat', 'fdfind'):
                tool = tools / name
                tool.write_text('#!/bin/sh\nexit 0\n')
                tool.chmod(0o755)
            tool = tools / 'zoxide'
            tool.write_text(r'''#!/bin/sh
printf '%s\n' 'z() { builtin cd "$@"; }' 'zi() { :; }'
''')
            tool.chmod(0o755)
            for shell in ('bash', 'zsh'):
                executable = shutil.which(shell)
                result = subprocess.run([executable, '-fic', '''
alias ll='echo preserved'
export BAT_THEME=custom
source "$1"
source "$1"
[[ $BAT_THEME == custom && $FZF_DEFAULT_COMMAND == fdfind* ]] || exit 2
[[ $(alias ll) == *preserved* && $(alias cat) == *batcat* ]] || exit 3
z "$2" || exit 4
[[ $PWD == "$2" ]] || exit 5
command -v zi
''', 'check', str(ROOT / 'config/shell-tools.sh'), str(root)],
                    env={**os.environ, 'HOME': temp, 'ZDOTDIR': temp, 'PATH': str(tools),
                         'FZF_DEFAULT_COMMAND': '', '_HERDR_FOLDER_TOOLS_LOADED': ''},
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (shell, result.stderr))

    def test_manifest_has_only_public_plugin_dependencies(self):
        manifest = json.loads((ROOT / 'dependencies.json').read_text())
        installer.validate_manifest(manifest)
        self.assertNotIn('sources', manifest)

    def test_shell_install_preserves_settings_and_is_repeatable(self):
        original = 'export EDITOR=vim\nalias ll="ls -l"\n'
        loader = Path('/home/a user/.local/share/herdr-setup/kit/setup.zsh')
        added = installer.shell_block(original, loader)
        self.assertTrue(added.startswith(original))
        self.assertEqual(installer.shell_block(added, loader), added)
        self.assertEqual(added.count(installer.BEGIN), 1)

    def test_existing_manual_loader_is_not_duplicated(self):
        with self.assertRaisesRegex(ValueError, 'manual'):
            installer.shell_block('source ~/custom/herdr-kit/shell/herdr.sh\n', Path('/tmp/kit/setup.zsh'))

    def test_malformed_shell_block_is_not_overwritten(self):
        for content in [installer.BEGIN, installer.END + '\n' + installer.BEGIN]:
            with self.assertRaises(ValueError):
                installer.shell_block(content, Path('/tmp/kit/setup.zsh'))

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
        with patch.object(installer, 'run', return_value=output), patch.object(installer, 'github_environment', return_value={}):
            self.assertEqual(installer.resolve_ref('owner/repo', 'v1.0'), 'b' * 40)

    def test_dry_run_does_not_run_commands(self):
        output = io.StringIO()
        with patch.object(installer, 'run', side_effect=AssertionError('unexpected command')), \
             patch('sys.stdout', output):
            self.assertEqual(installer.main(['--dry-run']), 0)
        self.assertIn('Installation plan', output.getvalue())
        self.assertIn('No changes made.', output.getvalue())
        self.assertNotIn('Setup complete', output.getvalue())
        self.assertNotIn('\033[', output.getvalue())

    def test_shell_loads_only_enabled_plugins_from_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='new user ') as temp:
            root = Path(temp)
            (root / 'shell.zsh').write_text('selected-feature() { printf loaded; }\n')
            (root / 'shell.bash').write_text('selected-feature() { printf loaded; }\n')
            registry = root / 'plugins.json'
            loader = root / 'loader.zsh'
            for shell in ['bash', 'zsh']:
                loader.write_text(installer.shell_loader({'plugins': [{'id': 'example', 'shell': 'shell.zsh',
                                                                      'shell_bash': 'shell.bash'}]}, registry, shell))
                for enabled in [True, False]:
                    registry.write_text(json.dumps([{'plugin_id': 'example', 'plugin_root': temp, 'enabled': enabled}]))
                    result = subprocess.run([shell, '-fc', 'source "$1"; command -v selected-feature', 'check', str(loader)],
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, enabled, result.stderr)

    def test_github_credentials_are_scoped_without_changing_parent_environment(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'test-token', 'GIT_CONFIG_COUNT': '1',
                                    'GIT_CONFIG_KEY_0': 'color.ui', 'GIT_CONFIG_VALUE_0': 'false'}, clear=True):
            env = installer.github_environment()
            self.assertEqual(env['GIT_CONFIG_COUNT'], '2')
            self.assertEqual(env['GIT_CONFIG_KEY_1'], 'http.https://github.com/.extraheader')
            self.assertEqual(env['GIT_CONFIG_VALUE_0'], 'false')
            self.assertNotIn('GIT_CONFIG_VALUE_1', os.environ)

    def test_legacy_plugin_is_disabled_after_successful_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'doomface-hook.sh').touch()
            registry = root / 'plugins.json'
            registry.write_text(json.dumps([{'plugin_id': 'dev.ariel.herdr-kit', 'enabled': True, 'plugin_root': temp}]))
            with patch.object(installer, 'run') as run:
                installer.install_plugins({'plugins': []}, registry)
                run.assert_called_once_with('herdr', 'plugin', 'disable', 'dev.ariel.herdr-kit')

    def test_plugin_paths_cannot_escape_the_checkout(self):
        for field in ['shell', 'shell_bash', 'config', 'subdir']:
            with self.assertRaisesRegex(ValueError, 'path'):
                installer.validate_manifest({'schema_version': 2, 'plugins': [
                    {'id': 'example', 'repository': 'owner/repo', field: '../outside'}]})

    def test_no_shell_installs_loader_without_editing_shell_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'config', root / 'config')
            (root / 'dependencies.json').write_text(json.dumps({
                'schema_version': 2, 'plugins': [], 'packages': {}, 'herdr': {'version': '0.9.3'}}))
            (root / '.zshrc').write_text('alias keep=true\n')
            env = {'XDG_CONFIG_HOME': str(root / 'preferences'), 'XDG_DATA_HOME': str(root / 'data'),
                   'ZDOTDIR': temp, 'HERDR_CONFIG_PATH': '', 'SHELL': '/bin/zsh'}
            with patch.dict(os.environ, env), patch.object(installer, 'ROOT', root), \
                 patch.object(installer.shutil, 'which', return_value='/usr/bin/zsh'), \
                 patch.object(installer, 'run', side_effect=lambda *a, **kw: str(root / 'lazygit') if a[0] == 'lazygit' else 'herdr 0.9.3'):
                self.assertEqual(installer.main(['--no-shell']), 0)
            self.assertEqual((root / '.zshrc').read_text(), 'alias keep=true\n')
            self.assertTrue((root / 'data/herdr-setup/shell.zsh').is_file())

    def test_bash_install_login_files_repeat_install_and_existing_config(self):
        with tempfile.TemporaryDirectory(prefix='bash user ') as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'config', root / 'config')
            (root / 'dependencies.json').write_text(json.dumps({
                'schema_version': 2, 'plugins': [], 'packages': {}, 'herdr': {'version': '0.9.3'}}))
            (root / '.bashrc').write_text('export KEEP_SETTING=yes\n')
            (root / '.profile').write_text('export LOGIN_SETTING=yes\n')
            env = {'HOME': temp, 'SHELL': '/bin/bash', 'HERDR_CONFIG_PATH': '',
                   'XDG_CONFIG_HOME': str(root / 'preferences'), 'XDG_DATA_HOME': str(root / 'data')}
            with patch.dict(os.environ, env), patch.object(installer, 'ROOT', root), \
                 patch.object(installer, 'run', side_effect=lambda *a, **kw: str(root / 'lazygit') if a[0] == 'lazygit' else 'herdr 0.9.3'):
                self.assertEqual(installer.main([]), 0)
                config = root / 'preferences/herdr/config.toml'
                self.assertEqual(tomllib.loads(config.read_text())['terminal']['default_shell'], '/bin/bash')
                config.write_text('onboarding = true\n')
                self.assertEqual(installer.main([]), 0)
                self.assertTrue(tomllib.loads(config.read_text())['onboarding'])
                self.assertEqual(len(tomllib.loads(config.read_text())['keys']['command']), 1)
            self.assertFalse((root / '.bash_profile').exists())
            self.assertFalse((root / '.zshrc').exists())
            for name in ['.bashrc', '.profile']:
                self.assertEqual((root / name).read_text().count(installer.BEGIN), 1)
            result = subprocess.run(['bash', '--noprofile', '--norc', '-c',
                                     'source "$HOME/.profile"; source "$HOME/.bashrc"; '
                                     'test "$KEEP_SETTING:$LOGIN_SETTING:$_HERDR_SETUP_LOADED" = yes:yes:1'],
                                    env={**os.environ, **env}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            # A shared .profile must remain safe when a POSIX shell reads it.
            result = subprocess.run(['sh', '-c', '. "$HOME/.profile"'], env={**os.environ, **env}, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_selection_and_bash_login_precedence(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'HOME': temp, 'SHELL': '/bin/zsh'}):
            root = Path(temp)
            shell, executable, files = installer.shell_settings('bash')
            self.assertEqual(shell, 'bash')
            self.assertEqual(Path(executable).name, 'bash')
            self.assertEqual(files, [root / '.bashrc', root / '.bash_profile'])
            (root / '.profile').touch()
            (root / '.bash_login').touch()
            self.assertEqual(installer.shell_settings('bash')[2][-1], root / '.bash_login')
            (root / '.bash_profile').touch()
            self.assertEqual(installer.shell_settings('bash')[2][-1], root / '.bash_profile')
            with patch.dict(os.environ, {'SHELL': '/bin/fish'}):
                with self.assertRaisesRegex(ValueError, '--shell'):
                    installer.shell_settings(None)

    def test_failed_install_keeps_legacy_plugin_enabled(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / 'plugins.json'
            registry.write_text(json.dumps([{'plugin_id': 'dev.ariel.herdr-kit', 'enabled': True, 'plugin_root': temp}]))
            plugin = {'id': 'new', 'repository': 'owner/repo', 'subdir': '', 'commit': 'a' * 40}
            output = io.StringIO()
            with patch('sys.stdout', output), patch.object(installer, 'github_environment', return_value={}), \
                 patch.object(installer, 'run', side_effect=OSError('download failed')) as run:
                with self.assertRaises(OSError):
                    installer.install_plugins({'plugins': [plugin]}, registry)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[:3], ('herdr', 'plugin', 'install'))
            self.assertIn('[1/1]  new - installing', output.getvalue())
            self.assertNotIn('OK', output.getvalue())

    def test_plugin_local_changes_stop_reinstallation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = root / 'plugins.json'
            registry.write_text(json.dumps([{'plugin_id': 'example', 'source': {'managed_path': temp}}]))
            commit = 'a' * 40

            def fake_run(*args, **kwargs):
                if args[:3] == ('git', 'rev-parse', 'HEAD'):
                    return commit
                if args[:3] == ('git', 'status', '--porcelain'):
                    return ' M user-file'
                return None

            with patch.object(installer, 'run', side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, 'local changes'):
                    installer.install_plugins({'plugins': [{'id': 'example', 'commit': commit}]}, registry)

    def test_plugin_build_artifacts_do_not_block_reinstall(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'herdr-plugin.toml').write_text('id = "example"\n')
            registry = root / 'plugins.json'
            registry.write_text(json.dumps([{
                'plugin_id': 'example',
                'enabled': True,
                'plugin_root': temp,
                'source': {'managed_path': temp, 'resolved_commit': 'b' * 40},
            }]))
            commit = 'a' * 40

            def fake_run(*args, **kwargs):
                if args[:3] == ('git', 'rev-parse', 'HEAD'):
                    return commit
                if args[:3] == ('git', 'status', '--porcelain'):
                    return ' M libexec/tool\n?? target/debug/foo'
                return None

            with patch.object(installer, 'github_environment', return_value={}), \
                 patch.object(installer, 'run', side_effect=fake_run) as run:
                installer.install_plugins({'plugins': [{
                    'id': 'example', 'repository': 'owner/repo', 'subdir': '', 'commit': commit,
                }]}, registry)
                self.assertIn(('herdr', 'plugin', 'install'), [c.args[:3] for c in run.call_args_list])

    def test_local_linked_plugin_skips_github_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'herdr-plugin.toml').write_text('id = "example"\n')
            registry = root / 'plugins.json'
            registry.write_text(json.dumps([{
                'plugin_id': 'example',
                'enabled': True,
                'plugin_root': temp,
                'source': {'kind': 'local'},
            }]))
            with patch.object(installer, 'run') as run:
                installer.install_plugins({'plugins': [{
                    'id': 'example', 'repository': 'owner/repo', 'subdir': '', 'commit': 'a' * 40,
                }]}, registry)
                self.assertFalse(any(c.args[:3] == ('herdr', 'plugin', 'install') for c in run.call_args_list))


if __name__ == '__main__':
    unittest.main()
