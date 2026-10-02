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

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def main():
    manifest = json.loads((ROOT / 'dependencies.json').read_text())
    system = {'Darwin': 'macos', 'Linux': 'linux'}.get(platform.system())
    if system is None:
        raise SystemExit('Supported platforms: macOS, Ubuntu/Debian Linux.')
    os.environ['PATH'] = str(Path.home() / '.local/bin') + ':' + str(Path.home() / '.cargo/bin') + ':' + os.environ['PATH']
    packages = manifest['packages'][system]
    if system == 'macos':
        if not shutil.which('brew'):
            raise SystemExit('Install Homebrew from https://brew.sh, then rerun ./install.sh.')
        installed = set(subprocess.check_output(['brew', 'list', '--formula', '-1'], text=True).split())
        missing = [p for p in packages if p not in installed]
        if missing:
            run('brew', 'install', *missing)
    else:
        if not shutil.which('apt-get'):
            raise SystemExit('Automatic Linux dependencies currently support Ubuntu/Debian (apt-get).')
        root_command = [] if os.geteuid() == 0 else ['sudo']
        missing = []
        for package in packages:
            result = subprocess.run(['dpkg-query', '-W', '-f=${Status}', package], capture_output=True, text=True)
            if result.returncode or result.stdout != 'install ok installed':
                missing.append(package)
        if missing:
            run(*root_command, 'apt-get', 'update')
            run(*root_command, 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y', '--no-install-recommends', *missing)
    for name, tool in manifest.get('tools', {}).items():
        if shutil.which(tool['check']):
            continue
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'install.sh'
            run('curl', '-fLsS', '--retry', '3', tool['url'], '-o', script)
            print('Installing ' + name, flush=True)
            run('sh', script, *tool.get('args', []), env={**os.environ, **tool.get('env', {})})
    herdr = manifest['herdr']
    current = subprocess.run(['herdr', '--version'], capture_output=True, text=True).stdout.strip() if shutil.which('herdr') else ''
    if current != 'herdr ' + herdr['version']:
        if current:
            print(f"Keeping existing {current}; captured version is {herdr['version']}.", flush=True)
            return
        arch = {'arm64': 'aarch64', 'aarch64': 'aarch64', 'x86_64': 'x86_64', 'amd64': 'x86_64'}[platform.machine()]
        asset = f'herdr-{system}-{arch}'
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


if __name__ == '__main__':
    main()
