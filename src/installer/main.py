#!/usr/bin/env python3
"""Install the bundled Herdr toolkit and selected public plugins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
BEGIN = '# >>> herdr-setup >>>'
END = '# <<< herdr-setup <<<'


def run(*args, cwd=None, capture=False):
    result = subprocess.run([str(x) for x in args], cwd=cwd, check=True,
                            text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def validate_manifest(lock):
    if lock['schema_version'] != 2:
        raise ValueError('Unsupported dependency manifest format')
    for item in lock['plugins']:
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
                 f'refs/tags/{ref}', f'refs/tags/{ref}^{{}}', f'refs/heads/{ref}', capture=True)
    refs = dict(line.split()[::-1] for line in output.splitlines())
    for name in [f'refs/tags/{ref}^{{}}', f'refs/tags/{ref}', f'refs/heads/{ref}']:
        if name in refs:
            return refs[name]
    raise ValueError(f'Cannot resolve {repository} @ {ref}')


def shell_block(text, loader):
    """Replace only our block; reject old manual loading instead of doubling it."""
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Malformed herdr-setup block in .zshrc; fix it first')
    if BEGIN in text:
        start, finish = text.index(BEGIN), text.index(END) + len(END)
        if finish < start:
            raise ValueError('Reversed herdr-setup markers in .zshrc')
        unmanaged = text[:start] + text[finish:]
    else:
        unmanaged = text
    if re.search(r'^\s*(?:source|\.)\s+[^\n]*herdr-kit/shell/herdr\.sh', unmanaged, re.M):
        raise ValueError('Existing manual herdr-kit source line in .zshrc. '
                         'Migrate those lines first, or use --no-shell; see README.')
    block = f'{BEGIN}\nsource {shlex.quote(str(loader))}\n{END}'
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


def kit_destination(data_root):
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'src/herdr-kit').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return data_root / 'kits' / digest.hexdigest()[:20]


def install_kit(destination):
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.kit-', dir=destination.parent) as temporary:
            staging = Path(temporary) / 'kit'
            shutil.copytree(ROOT / 'src/herdr-kit', staging, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            staging.rename(destination)
    return destination


def install_plugins(lock, registry_path, kit):
    installed = json.loads(registry_path.read_text()) if registry_path.exists() else []
    by_id = {p['plugin_id']: p for p in installed}
    for plugin in lock['plugins']:
        old = by_id.get(plugin['id'], {})
        if not plugin.get('enabled', True):
            if old.get('enabled'):
                run('herdr', 'plugin', 'disable', plugin['id'])
            continue
        source = old.get('source', {})
        root = Path(old.get('plugin_root', '/nonexistent'))
        managed = source.get('managed_path')
        intact = False
        if managed and Path(managed).is_dir():
            intact = not run('git', 'status', '--porcelain', cwd=managed, capture=True)
            intact = intact and run('git', 'rev-parse', 'HEAD', cwd=managed, capture=True) == plugin['commit']
        if (source.get('resolved_commit') == plugin['commit'] and intact
                and (root / 'herdr-plugin.toml').is_file()):
            if not old.get('enabled'):
                run('herdr', 'plugin', 'enable', plugin['id'])
            continue
        if managed and Path(managed).is_dir() and not intact:
            if run('git', 'status', '--porcelain', cwd=managed, capture=True):
                raise ValueError(f"Plugin has local changes: {managed}. Preserve/move it before reinstalling.")
        spec = plugin['repository'] + ('/' + plugin['subdir'] if plugin['subdir'] else '')
        run('herdr', 'plugin', 'install', spec, '--ref', plugin['commit'], '--yes')
    # Linking does not run build steps, so execute the kit's declared build first.
    manifest = tomllib.loads((kit / 'herdr-plugin.toml').read_text())
    for step in manifest.get('build', []):
        target_platform = 'macos' if platform.system() == 'Darwin' else 'linux'
        if 'platforms' not in step or target_platform in step['platforms']:
            run(*step['command'], cwd=kit)
    run('herdr', 'plugin', 'link', kit, '--enabled', capture=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print plan without writing or fetching')
    parser.add_argument('--no-shell', action='store_true', help='Leave .zshrc untouched')
    parser.add_argument('--replace-config', action='store_true', help='Back up and replace existing Herdr defaults')
    args = parser.parse_args(argv)
    lock = json.loads((ROOT / 'dependencies.json').read_text())
    validate_manifest(lock)
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))).expanduser().resolve()
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))).expanduser().resolve()
    data_root = data_home / 'herdr-setup'
    config = config_home / 'herdr'
    shell_rc = Path(os.environ.get('ZDOTDIR', str(Path.home()))).expanduser().resolve() / '.zshrc'
    kit = kit_destination(data_root)
    print(f"Herdr version for new installations: {lock['herdr']['version']}")
    for target, packages in lock['packages'].items():
        print(f'Packages ({target}): ' + ', '.join(packages))
    for item in lock['plugins']:
        print(f"Plugin: {item['name']} @ {item['ref']} ({'enabled' if item.get('enabled', True) else 'disabled'})")
    print(f'Toolkit: {kit}\nConfiguration: {config}')
    print(f'Shell: {"unchanged" if args.no_shell else shell_rc}')
    if args.dry_run:
        return 0
    if platform.system() not in ('Darwin', 'Linux'):
        raise ValueError('This setup supports macOS and Linux.')
    missing = [tool for tool in ['git', 'herdr', 'jq', 'zsh', 'uv'] if not shutil.which(tool)]
    if missing:
        raise ValueError('Missing prerequisites: ' + ', '.join(missing) + '. Run ./install.sh to bootstrap them.')
    version = run('herdr', '--version', capture=True)
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (0, 9, 3):
        raise ValueError('Herdr 0.9.3 or newer is required.')
    if version.strip() != 'herdr ' + lock['herdr']['version']:
        print(f'Using {version}; this snapshot was captured with {lock["herdr"]["version"]}.')
    if os.environ.get('HERDR_CONFIG_PATH'):
        raise ValueError('Unset HERDR_CONFIG_PATH before installing into the standard XDG configuration.')
    rc_content = None
    if not args.no_shell:
        rc_content = shell_block(shell_rc.read_text() if shell_rc.exists() else '', kit / 'setup.zsh')
    for item in lock['plugins']:
        if item.get('enabled', True):
            item['commit'] = resolve_ref(item['repository'], item['ref'])
    install_kit(kit)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    writer = Writer(data_root / 'backups' / stamp)
    registry = config / 'plugins.json'
    writer.backup(registry)
    install_plugins(lock, registry, kit)
    defaults = (ROOT / 'config/herdr.toml').read_text().replace('"@ZSH@"', json.dumps(shutil.which('zsh')))
    for target, content in [
        (config / 'config.toml', defaults),
        (config / 'plugins/config/dev.ariel.herdr-kit/config.sh', (ROOT / 'config/herdr-kit.sh').read_text()),
    ]:
        if target.exists() and not args.replace_config:
            print(f'Keeping existing configuration: {target}')
        else:
            writer.write(target, content)
    if rc_content is not None:
        writer.write(shell_rc, rc_content)
    print('Installed. Open a new zsh and reload Herdr configuration through its menu.')
    if args.no_shell:
        print('Shell integration: source ' + shlex.quote(str(kit / 'setup.zsh')))
    print('Start Herdr: ' + shlex.quote(shutil.which('herdr')))
    if writer.records:
        print(f'Backups: {writer.backup_root}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Install stopped: {exc}', file=sys.stderr)
        sys.exit(1)
