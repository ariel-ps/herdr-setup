#!/bin/sh
# Bootstrap only the JSON reader; application dependencies live in dependencies.json.
set -eu
setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    case "$(uname -s)" in
      Darwin)
        command -v brew >/dev/null 2>&1 || { echo 'Install Homebrew from https://brew.sh first.' >&2; exit 1; }
        brew install python ;;
      Linux)
        command -v apt-get >/dev/null 2>&1 || { echo 'Automatic Linux bootstrap needs Ubuntu/Debian.' >&2; exit 1; }
        if [ "$(id -u)" -eq 0 ]; then
            apt-get update && apt-get install -y python3
        else
            sudo apt-get update && sudo apt-get install -y python3
        fi ;;
      *) echo 'Unsupported OS.' >&2; exit 1 ;;
    esac
fi
exec python3 "$setup_root/src/installer/bootstrap.py"
