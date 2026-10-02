#!/usr/bin/env python3
"""Install platform dependencies from the single editable manifest."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import sys

from output import detail, message, section

ROOT = Path(__file__).resolve().parents[2]


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def install_herdr(herdr, system):
    current = subprocess.run(['herdr', '--version'], capture_output=True, text=True).stdout.strip() if shutil.which('herdr') else ''
    if current:
        message('OK', f'{current} found; compatibility will be checked during setup.', color='32')
        return
    arch = {'arm64': 'aarch64', 'aarch64': 'aarch64', 'x86_64': 'x86_64', 'amd64': 'x86_64'}.get(platform.machine())
    if arch is None:
        raise SystemExit(f'Unsupported architecture: {platform.machine()}')
    asset = f'herdr-{system}-{arch}'
    message('GET', f"Herdr {herdr['version']} for {system}/{arch}")
    entry = herdr['downloads'][f'{system}-{arch}']
    with tempfile.TemporaryDirectory() as temporary:
        binary = Path(temporary) / asset
        url = f"https://github.com/herdrdev/herdr/releases/download/v{herdr['version']}/{asset}"
        run('curl', '-fL', '--retry', '3', url, '-o', binary)
        if hashlib.sha256(binary.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('Herdr download checksum mismatch.')
        target = Path.home() / '.local/bin/herdr'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(binary, target)
        target.chmod(0o755)
        message('OK', f'Herdr {herdr["version"]} installed and checksum verified.', color='32')
        detail('Executable', target)


def main():
    manifest = json.loads((ROOT / 'dependencies.json').read_text())
    system = {'Darwin': 'macos', 'Linux': 'linux'}.get(platform.system())
    if system is None:
        raise SystemExit('Supported platforms: macOS, Ubuntu/Debian, Fedora.')
    section('Herdr Setup')
    detail('Platform', f'{system} / {platform.machine()}')
    section('[1/4] Prepare dependencies')
    os.environ['PATH'] = str(Path.home() / '.local/bin') + ':' + str(Path.home() / '.cargo/bin') + ':' + os.environ['PATH']
    if system == 'macos':
        packages = manifest['packages']['macos']
        if not shutil.which('brew'):
            raise SystemExit('Install Homebrew from https://brew.sh, then rerun ./install.sh.')
        installed = set(subprocess.check_output(['brew', 'list', '--formula', '-1'], text=True).split())
        missing = [p for p in packages if p not in installed]
        if missing:
            message('INSTALL', ', '.join(missing))
            run('brew', 'install', *missing)
    elif shutil.which('apt-get'):
        packages = manifest['packages']['linux']
        root_command = [] if os.geteuid() == 0 else ['sudo']
        missing = []
        for package in packages:
            result = subprocess.run(['dpkg-query', '-W', '-f=${Status}', package], capture_output=True, text=True)
            if result.returncode or result.stdout != 'install ok installed':
                missing.append(package)
        if missing:
            message('INSTALL', ', '.join(missing))
            run(*root_command, 'apt-get', 'update')
            run(*root_command, 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y', '--no-install-recommends', *missing)
    elif shutil.which('dnf'):
        root_command = [] if os.geteuid() == 0 else ['sudo']
        missing = [package for package in manifest['packages']['fedora']
                   if subprocess.run(['rpm', '-q', '--whatprovides', package],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode]
        if missing:
            message('INSTALL', ', '.join(missing))
            run(*root_command, 'dnf', 'install', '-y', '--setopt=install_weak_deps=False', *missing)
    else:
        raise SystemExit('Automatic Linux dependencies require apt-get (Ubuntu/Debian) or dnf (Fedora).')
    if not missing:
        message('OK', 'System packages are already installed.', color='32')
    for name, tool in manifest.get('tools', {}).items():
        if shutil.which(tool['check']):
            message('OK', f'{name} is available.', color='32')
            continue
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'install.sh'
            run('curl', '-fLsS', '--retry', '3', tool['url'], '-o', script)
            message('INSTALL', name)
            tool_env = {key: os.path.expandvars(value) for key, value in tool.get('env', {}).items()}
            run('sh', script, *tool.get('args', []), env={**os.environ, **tool_env})
    section('[2/4] Prepare Herdr')
    install_herdr(manifest['herdr'], system)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        message('ERROR', f'Dependency setup stopped: {exc}', color='31', error=True)
        sys.exit(1)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            message('ERROR', exc.code, color='31', error=True)
            sys.exit(1)
        raise
