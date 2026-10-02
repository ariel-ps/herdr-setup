#!/bin/sh
# The same entry point works from a clone and when piped from curl.
# Keep execution inside a function so a truncated download cannot start it.
herdr_setup_main() {
    set -eu
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
        printf 'Downloading Herdr Setup (%s)...\n' "$setup_ref"
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
        for setup_required in install.sh dependencies.json src/installer/main.py src/installer/bootstrap.py; do
            [ -f "$setup_tmp/source/$setup_required" ] || { echo "Incomplete archive: $setup_required" >&2; return 1; }
        done
        # The installer copies runtime files into the user's data directory.
        sh "$setup_tmp/source/install.sh" "$@"
        return $?
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
                    command -v apt-get >/dev/null 2>&1 || { echo 'Automatic Linux bootstrap needs Ubuntu/Debian.' >&2; return 1; }
                    if [ "$(id -u)" -eq 0 ]; then
                        apt-get update && apt-get install -y python3
                    else
                        sudo apt-get update && sudo apt-get install -y python3
                    fi ;;
                *) echo 'Unsupported OS.' >&2; return 1 ;;
            esac
        fi
        python3 "$setup_root/src/installer/bootstrap.py"
    fi
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
        exec python3 "$setup_root/src/installer/main.py" "$@"
    fi
    if command -v uv >/dev/null 2>&1; then
        exec uv run --no-project --python 3.11 python "$setup_root/src/installer/main.py" "$@"
    fi
    echo 'Install Python 3.11+ or uv first.' >&2
    return 1
}
herdr_setup_main "$@"
