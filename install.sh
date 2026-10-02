#!/bin/sh
set -eu
setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
    exec python3 "$setup_root/scripts/install.py" "$@"
fi
if command -v uv >/dev/null 2>&1; then
    exec uv run --no-project --python 3.11 python "$setup_root/scripts/install.py" "$@"
fi
echo 'Install Python 3.11+ or uv first (brew install uv).' >&2
exit 1
