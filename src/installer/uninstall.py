#!/usr/bin/env python3
"""Remove Herdr Setup shell integration; optionally uninstall enabled manifest plugins."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from output import detail, message, section

from main import BEGIN, END, ROOT, shell_settings, validate_manifest

TOOLS_BEGIN = '# >>> herdr-setup tools >>>'
TOOLS_END = '# <<< herdr-setup tools <<<'


def strip_block(text: str, begin: str, end: str) -> tuple[str, bool]:
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError(f'Malformed setup block ({begin!r}); fix the file manually.')
    if begin not in text:
        return text, False
    start = text.index(begin)
    finish = text.index(end) + len(end)
    tail = text[finish:]
    if tail.startswith('\n'):
        finish += 1
    new = (text[:start] + text[finish:]).rstrip('\n')
    if new:
        new += '\n'
    return new, True


def resolve_manifest(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'Manifest not found: {path}')
        return path
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))).expanduser()
    cached = data / 'herdr-setup' / 'dependencies.json'
    if cached.is_file():
        return cached
    bundled = ROOT / 'dependencies.json'
    if bundled.is_file():
        return bundled
    raise ValueError(
        'Cannot find dependencies.json (set --manifest or run from a herdr-setup checkout).'
    )


def remove_shell_blocks(files, *, include_tools: bool) -> list[Path]:
    changed: list[Path] = []
    for path in files:
        original = path.read_text() if path.exists() else ''
        text, main_removed = strip_block(original, BEGIN, END)
        tools_removed = False
        if include_tools:
            text, tools_removed = strip_block(text, TOOLS_BEGIN, TOOLS_END)
        if main_removed or tools_removed:
            path.write_text(text)
            changed.append(path)
    return changed


def enabled_plugin_ids(manifest_path: Path) -> list[str]:
    lock = json.loads(manifest_path.read_text())
    validate_manifest(lock)
    return [p['id'] for p in lock['plugins'] if p.get('enabled', True)]


def uninstall_plugins(ids: list[str]) -> None:
    if not shutil.which('herdr'):
        raise ValueError('herdr is not on PATH; cannot uninstall plugins.')
    for plugin_id in ids:
        message('UNINSTALL', plugin_id)
        subprocess.run(['herdr', 'plugin', 'uninstall', plugin_id], check=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--plugins',
        action='store_true',
        help='Also herdr plugin uninstall each enabled entry in dependencies.json',
    )
    parser.add_argument('--yes', action='store_true', help='Required with --plugins (non-interactive)')
    parser.add_argument(
        '--all-shell-blocks',
        action='store_true',
        help='Remove the herdr-setup tools block as well as the main loader block',
    )
    parser.add_argument('--shell', choices=['bash', 'zsh'], help='Shell startup files (default: login shell)')
    parser.add_argument('--manifest', type=Path, help='Path to dependencies.json')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without writing or uninstalling')
    args = parser.parse_args(argv)

    if args.plugins and not args.yes and not args.dry_run:
        raise ValueError('Pass --yes to uninstall enabled plugins, or use --dry-run.')

    _, _, shell_files = shell_settings(args.shell)
    section('Herdr Setup uninstall')
    detail('Shell files', ', '.join(str(p) for p in shell_files))

    if args.dry_run:
        for path in shell_files:
            text = path.read_text() if path.exists() else ''
            message('CHECK', f'{path}: main block={"yes" if BEGIN in text else "no"}')
            if args.all_shell_blocks:
                message('CHECK', f'{path}: tools block={"yes" if TOOLS_BEGIN in text else "no"}')
        if args.plugins:
            manifest = resolve_manifest(args.manifest)
            ids = enabled_plugin_ids(manifest)
            detail('Manifest', manifest)
            detail('Enabled plugins', ', '.join(ids) or '(none)')
        message('PREVIEW', 'No changes made.')
        return 0

    changed = remove_shell_blocks(shell_files, include_tools=args.all_shell_blocks)
    if changed:
        message('OK', 'Removed setup shell block(s).', color='32')
        for path in changed:
            detail('Updated', path)
    else:
        message('OK', 'No setup shell blocks found.', color='32')

    if args.plugins:
        manifest = resolve_manifest(args.manifest)
        ids = enabled_plugin_ids(manifest)
        if not ids:
            message('OK', 'No enabled plugins in manifest.', color='32')
        else:
            section('Plugins')
            detail('Manifest', manifest)
            uninstall_plugins(ids)
            message('OK', f'Uninstalled {len(ids)} plugin(s).', color='32')

    detail('Note', 'System packages (brew/apt), Herdr, and ~/.config/herdr are unchanged.')
    detail('Next', 'Open a new shell.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        message('ERROR', str(exc), color='31', error=True)
        sys.exit(1)
