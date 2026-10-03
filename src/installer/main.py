#!/usr/bin/env python3
"""Install Herdr and the plugins selected in dependencies.json."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone

from output import detail, message, section

ROOT = Path(__file__).resolve().parents[2]
BEGIN = '# >>> herdr-setup >>>'
END = '# <<< herdr-setup <<<'


def run(*args, cwd=None, capture=False, env=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, check=True,
                            text=True, stdout=subprocess.PIPE if capture else None, env=env)
    return result.stdout.strip() if capture else None


def validate_manifest(lock):
    if lock['schema_version'] != 2:
        raise ValueError('Unsupported dependency manifest format')
    seen = set()
    for item in lock['plugins']:
        if item['id'] in seen or not re.fullmatch(r'[\w.-]+', item['id']):
            raise ValueError('Invalid or duplicate plugin ID')
        seen.add(item['id'])
        for field in ('shell', 'shell_bash', 'config', 'subdir'):
            path = item.get(field, '')
            if path and (Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path):
                raise ValueError(f'Invalid plugin {field} path')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', item['repository']):
            raise ValueError('Invalid GitHub repository')
        if not isinstance(item.get('enabled', True), bool):
            raise ValueError('Plugin enabled must be true or false')


def resolve_ref(repository, ref):
    if re.fullmatch(r'[0-9a-f]{40}', ref):
        return ref
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', ref) or ref.startswith('-'):
        raise ValueError(f'Invalid Git ref: {ref}')
    output = run('git', 'ls-remote', f'https://github.com/{repository}.git',
                 f'refs/tags/{ref}', f'refs/tags/{ref}^{{}}', f'refs/heads/{ref}', capture=True,
                 env=github_environment())
    refs = dict(line.split()[::-1] for line in output.splitlines())
    for name in [f'refs/tags/{ref}^{{}}', f'refs/tags/{ref}', f'refs/heads/{ref}']:
        if name in refs:
            return refs[name]
    raise ValueError(f'Cannot resolve {repository} @ {ref}')


def shell_block(text, loader, shell='zsh'):
    """Replace only our block; reject old manual loading instead of doubling it."""
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Malformed herdr-setup block in shell startup file; fix it first')
    if BEGIN in text:
        start, finish = text.index(BEGIN), text.index(END) + len(END)
        if finish < start:
            raise ValueError('Reversed herdr-setup markers in shell startup file')
        unmanaged = text[:start] + text[finish:]
    else:
        unmanaged = text
    if re.search(r'^\s*(?:source|\.)\s+[^\n]*herdr-kit/shell/herdr\.sh', unmanaged, re.M):
        raise ValueError('Existing manual herdr-kit source line in shell startup file. '
                         'Migrate those lines first, or use --no-shell; see README.')
    command = f'source {shlex.quote(str(loader))}'
    if shell == 'bash':
        command = f'if [ -n "${{BASH_VERSION:-}}" ] && ! shopt -oq posix; then\n  {command}\nfi'
    block = f'{BEGIN}\n{command}\n{END}'
    if BEGIN in text:
        return text[:start] + block + text[finish:]
    return text.rstrip('\n') + ('\n\n' if text else '') + block + '\n'


class Writer:
    def __init__(self, backup_root):
        self.backup_root = backup_root
        self.records = []

    def backup(self, path):
        if not path.exists() and not path.is_symlink():
            return
        key = hashlib.sha256(str(path).encode()).hexdigest()[:12]
        self.backup_root.mkdir(parents=True, exist_ok=True)
        backup = self.backup_root / f'{key}-{path.name}'
        if path.is_symlink():
            backup.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, backup)
        self.records.append({'original': str(path), 'backup': str(backup)})
        (self.backup_root / 'manifest.json').write_text(json.dumps(self.records, indent=2) + '\n')

    def write(self, path, data):
        if isinstance(data, str):
            data = data.encode()
        if path.exists() and path.read_bytes() == data:
            return
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
        fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def github_environment():
    """Pass GitHub credentials only to the plugin installation subprocess."""
    env = os.environ.copy()
    token = env.get('GH_TOKEN') or env.get('GITHUB_TOKEN')
    if not token and shutil.which('gh'):
        result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
        if result.returncode == 0:
            token = result.stdout.strip()
    if token:
        index = int(env.get('GIT_CONFIG_COUNT', '0'))
        env['GIT_CONFIG_COUNT'] = str(index + 1)
        env[f'GIT_CONFIG_KEY_{index}'] = 'http.https://github.com/.extraheader'
        credential = base64.b64encode(('x-access-token:' + token).encode()).decode()
        env[f'GIT_CONFIG_VALUE_{index}'] = 'Authorization: Basic ' + credential
    return env


def shell_loader(lock, registry, shell='zsh'):
    field = 'shell_bash' if shell == 'bash' else 'shell'
    scripts = {p['id']: p[field] for p in lock['plugins'] if p.get(field)}
    if shell == 'bash':
        prelude = ('[[ ${_HERDR_SETUP_LOADED:-} == 1 ]] && return 0\n'
                   '_HERDR_SETUP_LOADED=1\n'
                   'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"\n')
    else:
        prelude = ('typeset -U path\n'
                   'path=("$HOME/.local/bin" "$HOME/.cargo/bin" $path)\n')
    return (
        '# Generated by herdr-setup. Open a new shell after enabling/disabling plugins.\n'
        + prelude +
        f'if [[ -r {shlex.quote(str(registry))} ]]; then\n'
        '  while IFS= read -r plugin_script; do\n'
        '    [[ -r "$plugin_script" ]] && source "$plugin_script"\n'
        '  done < <(jq -r --argjson scripts ' + shlex.quote(json.dumps(scripts)) +
        ' \' .[] | select(.enabled and $scripts[.plugin_id]) | .plugin_root + "/" + $scripts[.plugin_id] \' ' +
        shlex.quote(str(registry)) + ')\n'
        'fi\n'
        'unset plugin_script\n'
        + (ROOT / 'config/shell-tools.sh').read_text()
    )


def with_lazygit_popup(content):
    """Add the popup without rewriting the user's TOML or taking an occupied key."""
    snippet = (ROOT / 'config/lazygit-popup.toml').read_text()
    binding = tomllib.loads(snippet)['keys']['command'][0]
    keys = tomllib.loads(content).get('keys', {})
    commands = keys.get('command', [])
    if any('lazygit' in entry.get('command', '') for entry in commands):
        return content
    occupied = set()
    for value in [v for k, v in keys.items() if k != 'command'] + [entry['key'] for entry in commands]:
        occupied.update([value] if isinstance(value, str) else value)
    if occupied.intersection(binding['key']):
        message('KEEP', 'Lazygit shortcut conflicts with an existing binding; run lazygit directly.')
        return content
    updated = content.rstrip() + '\n\n' + snippet
    try:
        tomllib.loads(updated)
    except tomllib.TOMLDecodeError:
        message('KEEP', 'Custom key table cannot be extended; run lazygit directly.')
        return content
    return updated


def shell_settings(requested):
    executable = os.environ.get('SHELL') or pwd.getpwuid(os.getuid()).pw_shell
    shell = requested or Path(executable).name
    if shell not in ('bash', 'zsh'):
        raise ValueError('Shell integration supports bash and zsh. Select one with --shell bash or --shell zsh.')
    if requested:
        executable = shutil.which(shell)
    if not executable or not os.access(executable, os.X_OK):
        raise ValueError(f'Shell executable is unavailable: {executable or shell}')
    if shell == 'zsh':
        files = [Path(os.environ.get('ZDOTDIR', str(Path.home()))).expanduser().resolve() / '.zshrc']
    else:
        # Bash reads only the first existing login file, independently of .bashrc.
        profiles = [Path.home() / name for name in ('.bash_profile', '.bash_login', '.profile')]
        files = [Path.home() / '.bashrc', next((p for p in profiles if p.exists()), profiles[0])]
    return shell, executable, files


def install_plugins(lock, registry_path):
    installed = json.loads(registry_path.read_text()) if registry_path.exists() else []
    by_id = {p['plugin_id']: p for p in installed}
    auth_env = None
    total = len(lock['plugins'])
    for index, plugin in enumerate(lock['plugins'], 1):
        name = plugin.get('name', plugin['id'])
        progress = f'[{index}/{total}]'
        old = by_id.get(plugin['id'], {})
        if not plugin.get('enabled', True):
            if old.get('enabled'):
                message(progress, f'{name} - disabling')
                run('herdr', 'plugin', 'disable', plugin['id'])
            else:
                message(progress, f'{name} - disabled')
            continue
        source = old.get('source', {})
        root = Path(old.get('plugin_root', '/nonexistent'))
        managed = source.get('managed_path')
        intact = False
        if managed and Path(managed).is_dir():
            if run('git', 'status', '--porcelain', cwd=managed, capture=True):
                raise ValueError(f"Plugin has local changes: {managed}. Preserve/move it before reinstalling.")
            intact = run('git', 'rev-parse', 'HEAD', cwd=managed, capture=True) == plugin['commit']
        if (source.get('resolved_commit') == plugin['commit'] and intact
                and (root / 'herdr-plugin.toml').is_file()):
            if not old.get('enabled'):
                run('herdr', 'plugin', 'enable', plugin['id'])
            message(progress, f'{name} - ready', color='32')
            continue
        spec = plugin['repository'] + ('/' + plugin['subdir'] if plugin['subdir'] else '')
        if auth_env is None:
            auth_env = github_environment()
        message(progress, f'{name} - installing')
        run('herdr', 'plugin', 'install', spec, '--ref', plugin['commit'], '--yes', env=auth_env)
        message('OK', f'{name} installed.', color='32')
    # Replace the old combined plugin only after all selected plugins install.
    legacy = by_id.get('dev.ariel.herdr-kit', {})
    if legacy.get('enabled'):
        stop = Path(legacy['plugin_root']) / 'doomface-hook.sh'
        if stop.is_file():
            run('zsh', stop, '--stop-all')
        run('herdr', 'plugin', 'disable', 'dev.ariel.herdr-kit')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print plan without writing or fetching')
    parser.add_argument('--no-shell', action='store_true', help='Leave shell startup files untouched')
    parser.add_argument('--shell', choices=['bash', 'zsh'], help='Shell integration and new pane default (otherwise login shell)')
    parser.add_argument('--replace-config', action='store_true', help='Back up and replace existing Herdr defaults')
    args = parser.parse_args(argv)
    lock = json.loads((ROOT / 'dependencies.json').read_text())
    validate_manifest(lock)
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))).expanduser().resolve()
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))).expanduser().resolve()
    data_root = data_home / 'herdr-setup'
    config = config_home / 'herdr'
    shell, shell_executable, shell_files = shell_settings(args.shell)
    loader = data_root / f'shell.{shell}'
    registry = config / 'plugins.json'
    section('Installation plan' if args.dry_run else 'Your installation')
    detail('Herdr', f"{lock['herdr']['version']} for new installations")
    detail('Plugins', f"{sum(p.get('enabled', True) for p in lock['plugins'])} enabled")
    detail('Configuration', config)
    detail('Shell', shell)
    detail('Startup files', 'unchanged' if args.no_shell else ', '.join(map(str, shell_files)))
    if args.dry_run:
        section('Dependencies')
        for target, packages in lock['packages'].items():
            detail(target, ', '.join(packages))
        section('Plugins')
        for item in lock['plugins']:
            message('ON' if item.get('enabled', True) else 'OFF', item['name'])
            detail('Revision', item['ref'])
        message('PREVIEW', 'No changes made.')
        return 0
    if platform.system() not in ('Darwin', 'Linux'):
        raise ValueError('This setup supports macOS and Linux.')
    missing = [tool for tool in ['git', 'herdr', 'jq', 'zsh', 'uv', 'lazygit'] if not shutil.which(tool)]
    if missing:
        raise ValueError('Missing prerequisites: ' + ', '.join(missing) + '. Run ./install.sh to bootstrap them.')
    version = run('herdr', '--version', capture=True)
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (0, 9, 3):
        raise ValueError('Herdr 0.9.3 or newer is required.')
    if version.strip() != 'herdr ' + lock['herdr']['version']:
        message('NOTE', f'Using {version}; this snapshot was captured with {lock["herdr"]["version"]}.', color='33')
    if os.environ.get('HERDR_CONFIG_PATH'):
        raise ValueError('Unset HERDR_CONFIG_PATH before installing into the standard XDG configuration.')
    rc_contents = {}
    if not args.no_shell:
        for shell_rc in shell_files:
            rc_contents[shell_rc] = shell_block(shell_rc.read_text() if shell_rc.exists() else '', loader, shell)
    for item in lock['plugins']:
        if item.get('enabled', True):
            item['commit'] = resolve_ref(item['repository'], item['ref'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    writer = Writer(data_root / 'backups' / stamp)
    writer.backup(registry)
    section('[3/4] Install plugins')
    install_plugins(lock, registry)
    section('[4/4] Configure your environment')
    defaults = with_lazygit_popup((ROOT / 'config/herdr.toml').read_text().replace('"@SHELL@"', json.dumps(shell_executable)))
    configurations = [(config / 'config.toml', defaults)]
    if any(p['id'] == 'cloudmanic.herdr-plus' and p.get('enabled', True) for p in lock['plugins']):
        panel = config / 'plugins/config/cloudmanic.herdr-plus/quick-actions'
        configurations.extend((panel / source.name, source.read_text())
                              for source in sorted((ROOT / 'config/quick-actions').glob('*.toml')))
    if os.environ.get('LG_CONFIG_FILE'):
        message('KEEP', 'LG_CONFIG_FILE selects your own Lazygit configuration.')
    else:
        lazygit_directory = Path(run('lazygit', '--print-config-dir', capture=True))
        if not lazygit_directory.is_absolute():
            raise ValueError('Lazygit returned an invalid configuration directory')
        configurations.append((lazygit_directory / 'config.yml', (ROOT / 'config/lazygit.yml').read_text()))
    installed = {p['plugin_id']: p for p in json.loads(registry.read_text())} if registry.exists() else {}
    legacy_config = config / 'plugins/config/dev.ariel.herdr-kit/config.sh'
    for item in lock['plugins']:
        if item.get('enabled', True) and item.get('config'):
            source = Path(installed[item['id']]['plugin_root']) / item['config']
            target = config / 'plugins/config' / item['id'] / 'config.sh'
            migrate = legacy_config.exists() and not target.exists() and not args.replace_config
            configurations.append((target, legacy_config.read_text() if migrate else source.read_text()))
    for target, content in configurations:
        if target.exists() and not args.replace_config:
            if target == config / 'config.toml':
                writer.write(target, with_lazygit_popup(target.read_text()))
            else:
                message('KEEP', str(target))
        else:
            writer.write(target, content)
    writer.write(loader, shell_loader(lock, registry, shell))
    for shell_rc, rc_content in rc_contents.items():
        writer.write(shell_rc, rc_content)
    section('Setup complete')
    message('OK', 'Plugins and shell integration are ready.', color='32')
    detail('Next', f'Open a new {shell}, then run herdr.')
    if any(p['id'] == 'cloudmanic.herdr-plus' and p.get('enabled', True) for p in lock['plugins']):
        detail('Control panel', 'Herdr Plus: Quick Actions in the plugin menu; default shortcut prefix+down.')
    detail('Git popup', 'Cmd+Shift+G or prefix+d; q closes it.')
    detail('Folders', 'Visit a project once with cd, then use z <name> or zi.')
    detail('Existing Herdr session', 'Reload its configuration through the menu.')
    if args.no_shell:
        detail('Load helpers manually', 'source ' + shlex.quote(str(loader)))
    if any(p['id'] == 'dev.ariel.herdr-alerts' and p.get('enabled', True) for p in lock['plugins']):
        detail('Test sound', 'herdr-sound play')
    detail('Herdr executable', shlex.quote(shutil.which('herdr')))
    if writer.records:
        detail('Backups', writer.backup_root)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        message('ERROR', f'Install stopped: {exc}', color='31', error=True)
        sys.exit(1)
