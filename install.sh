#!/bin/sh
# The same entry point works from a clone and when piped from curl.
# Keep execution inside a function so a truncated download cannot start it.
herdr_setup_main() {
    set -eu
    if [ "$(uname -s)" = Darwin ]; then
        for setup_brew in /opt/homebrew/bin /opt/homebrew/sbin /usr/local/bin; do
            [ -d "$setup_brew" ] || continue
            case ":${PATH}:" in *":$setup_brew:"*) ;; *) PATH="$setup_brew:$PATH" ;; esac
        done
    fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    setup_root=''
    case "$0" in
        */install.sh|install.sh)
            setup_candidate=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
            if [ -f "$setup_candidate/src/installer/main.py" ]; then
                setup_root=$setup_candidate
            fi ;;
    esac

    if [ -z "$setup_root" ]; then
        command -v curl >/dev/null 2>&1 || { echo 'curl is required.' >&2; return 1; }
        command -v tar >/dev/null 2>&1 || { echo 'tar is required.' >&2; return 1; }
        setup_ref=${HERDR_SETUP_REF:-main}
        case "$setup_ref" in
            ''|*[!A-Za-z0-9._/-]*|-*|/*|*..*) echo 'Invalid HERDR_SETUP_REF.' >&2; return 1 ;;
        esac
        setup_tmp=$(mktemp -d)
        trap 'rm -rf "$setup_tmp"' 0
        trap 'exit 130' INT
        trap 'exit 143' TERM
        # Header file keeps the token out of curl process arguments.
        # GitHub CLI authentication is optional.
        setup_token=${GH_TOKEN:-${GITHUB_TOKEN:-}}
        if [ -z "$setup_token" ] && command -v gh >/dev/null 2>&1; then
            setup_token=$(gh auth token 2>/dev/null || true)
        fi
        if [ -n "$setup_token" ]; then
            (umask 077; printf 'Authorization: Bearer %s\n' "$setup_token" > "$setup_tmp/headers")
        else
            : > "$setup_tmp/headers"
        fi
        unset setup_token
        printf '\n  GET  Herdr Setup (%s)\n' "$setup_ref"
        if ! curl --fail --silent --show-error --location --retry 3 \
            --header "@$setup_tmp/headers" \
            "https://api.github.com/repos/ariel-ps/herdr-setup/tarball/$setup_ref" \
            --output "$setup_tmp/setup.tar.gz"; then
            echo 'Download failed. Check your connection and repository access; if authentication is required, use gh auth login or set GH_TOKEN.' >&2
            return 1
        fi
        rm -f "$setup_tmp/headers"
        # Reject absolute/traversing archive paths before extraction.
        tar -tzf "$setup_tmp/setup.tar.gz" > "$setup_tmp/entries"
        if ! awk '/^\// || /(^|\/)\.\.(\/|$)/ {bad=1} END {exit bad}' "$setup_tmp/entries"; then
            echo 'Archive contains unsafe paths.' >&2
            return 1
        fi
        mkdir "$setup_tmp/source"
        tar -xzf "$setup_tmp/setup.tar.gz" -C "$setup_tmp/source" --strip-components=1
        for setup_required in install.sh uninstall.sh dependencies.json src/installer/main.py src/installer/bootstrap.py src/installer/output.py src/installer/uninstall.py; do
            [ -f "$setup_tmp/source/$setup_required" ] || { echo "Incomplete archive: $setup_required" >&2; return 1; }
        done
        setup_persist=1
        for setup_arg in "$@"; do
            case "$setup_arg" in --dry-run|--help|-h) setup_persist=0 ;; esac
        done
        if [ "$setup_persist" = 1 ]; then
            setup_data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
            case "$HOME" in
                /*) ;;
                *) echo 'HOME must be an absolute path.' >&2; return 1 ;;
            esac
            case "$setup_data_home" in
                /*) ;;
                *) echo 'XDG_DATA_HOME must be an absolute path.' >&2; return 1 ;;
            esac
        fi
        sh "$setup_tmp/source/install.sh" "$@"
        if [ "$setup_persist" = 1 ]; then
            umask 077
            mkdir -p "$setup_data_home/herdr-setup/runtimes" "$HOME/.local/bin"
            setup_runtime_parent=$(CDPATH='' cd -- "$setup_data_home/herdr-setup/runtimes" && pwd -P)
            setup_bin=$(CDPATH='' cd -- "$HOME/.local/bin" && pwd -P)
            setup_runtime=$(mktemp -d "$setup_runtime_parent/runtime.XXXXXX")
            mkdir -p "$setup_runtime/src/installer"
            cp "$setup_tmp/source/uninstall.sh" "$setup_runtime/uninstall.sh"
            cp "$setup_tmp/source/dependencies.json" "$setup_runtime/dependencies.json"
            cp "$setup_tmp/source/src/installer/main.py" "$setup_runtime/src/installer/main.py"
            cp "$setup_tmp/source/src/installer/output.py" "$setup_runtime/src/installer/output.py"
            cp "$setup_tmp/source/src/installer/uninstall.py" "$setup_runtime/src/installer/uninstall.py"
            chmod 700 "$setup_runtime/uninstall.sh"
            setup_command_tmp=$(mktemp "$setup_bin/.herdr-setup-uninstall.XXXXXX")
            python3 - "$setup_runtime" "$setup_command_tmp" "$setup_bin/herdr-setup-uninstall" <<'PY'
import os
from pathlib import Path
import shlex
import sys

runtime = Path(sys.argv[1])
Path(sys.argv[2]).write_text(
    '#!/bin/sh\nexec ' + shlex.quote(str(runtime / 'uninstall.sh')) +
    ' --manifest ' + shlex.quote(str(runtime / 'dependencies.json')) + ' "$@"\n'
)
os.chmod(sys.argv[2], 0o700)
os.replace(sys.argv[2], sys.argv[3])
PY
        fi
        return 0
    fi

    setup_bootstrap=1
    for setup_arg in "$@"; do
        case "$setup_arg" in --dry-run|--help|-h) setup_bootstrap=0 ;; esac
    done
    if [ "$setup_bootstrap" = 1 ]; then
        # Bootstrap the JSON reader; other dependencies live in dependencies.json.
        if ! command -v python3 >/dev/null 2>&1; then
            case "$(uname -s)" in
                Darwin)
                    command -v brew >/dev/null 2>&1 || { echo 'Install Homebrew from https://brew.sh first.' >&2; return 1; }
                    brew install python ;;
                Linux)
                    setup_sudo=''
                    [ "$(id -u)" -eq 0 ] || setup_sudo=sudo
                    if command -v apt-get >/dev/null 2>&1; then
                        $setup_sudo apt-get update && $setup_sudo apt-get install -y python3
                    elif command -v dnf >/dev/null 2>&1; then
                        $setup_sudo dnf install -y python3
                    else
                        echo 'Automatic Linux bootstrap needs apt-get or dnf.' >&2
                        return 1
                    fi ;;
                *) echo 'Unsupported OS.' >&2; return 1 ;;
            esac
        fi
        python3 "$setup_root/src/installer/bootstrap.py"
    fi
    if command -v python3 >/dev/null 2>&1 &&
       python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        exec python3 "$setup_root/src/installer/main.py" "$@"
    fi
    if command -v uv >/dev/null 2>&1; then
        exec uv run --no-project --python 3.11 python "$setup_root/src/installer/main.py" "$@"
    fi
    echo 'Install Python 3.11+ or uv first.' >&2
    return 1
}
herdr_setup_main "$@"
