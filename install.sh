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
        # Header file avoids putting a private token in curl process arguments.
        # GitHub CLI authentication is optional and only used for private access.
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
            echo 'Download failed. While the repository is private, authenticate with gh auth login or set GH_TOKEN.' >&2
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
        for setup_required in install.sh dependencies.json src/installer/main.py src/installer/bootstrap.sh; do
            [ -f "$setup_tmp/source/$setup_required" ] || { echo "Incomplete archive: $setup_required" >&2; return 1; }
        done
        setup_preview=0
        for setup_arg in "$@"; do
            case "$setup_arg" in --dry-run|--help|-h) setup_preview=1 ;; esac
        done
        if [ "$setup_preview" = 1 ]; then
            sh "$setup_tmp/source/install.sh" "$@"
            return $?
        fi
        # Shell integration references these files after installation. Keep the
        # downloaded release in a persistent directory, not the temporary one.
        if command -v shasum >/dev/null 2>&1; then
            setup_digest=$(shasum -a 256 "$setup_tmp/setup.tar.gz" | awk '{print $1}')
        elif command -v sha256sum >/dev/null 2>&1; then
            setup_digest=$(sha256sum "$setup_tmp/setup.tar.gz" | awk '{print $1}')
        else
            echo 'shasum or sha256sum is required.' >&2
            return 1
        fi
        setup_releases="${XDG_DATA_HOME:-$HOME/.local/share}/herdr-setup/releases"
        setup_root="$setup_releases/$setup_digest"
        mkdir -p "$setup_releases"
        if [ ! -d "$setup_root" ]; then
            # Stage on the destination filesystem so the final rename is atomic.
            setup_stage=$(mktemp -d "$setup_releases/.staging.XXXXXX")
            trap 'rm -rf "$setup_tmp" "$setup_stage"' 0
            cp -R "$setup_tmp/source/." "$setup_stage/"
            mv "$setup_stage" "$setup_root"
        fi
        sh "$setup_root/install.sh" "$@"
        return $?
    fi

    setup_bootstrap=1
    for setup_arg in "$@"; do
        case "$setup_arg" in --dry-run|--help|-h) setup_bootstrap=0 ;; esac
    done
    if [ "$setup_bootstrap" = 1 ]; then
        sh "$setup_root/src/installer/bootstrap.sh"
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
