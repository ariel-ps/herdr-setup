#!/bin/sh
# Remove Herdr Setup shell blocks; optionally uninstall enabled manifest plugins.
set -eu

setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)

if command -v python3 >/dev/null 2>&1 &&
   python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
  exec python3 "$setup_root/src/installer/uninstall.py" "$@"
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --python 3.11 python "$setup_root/src/installer/uninstall.py" "$@"
fi

echo 'uninstall.sh: Python 3.11+ or uv is required.' >&2
exit 1
