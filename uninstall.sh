#!/bin/sh
# Remove Herdr Setup shell blocks; optionally uninstall enabled manifest plugins.
set -eu

setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)

if ! command -v python3 >/dev/null 2>&1; then
  echo 'uninstall.sh: python3 is required.' >&2
  exit 1
fi

exec python3 "$setup_root/src/installer/uninstall.py" "$@"
