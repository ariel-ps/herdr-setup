# This file and its helpers are installed together; no checkout path is assumed.
typeset -U path
path=("$HOME/.local/bin" "$HOME/.cargo/bin" $path)
source "${0:A:h}/shell/herdr.sh"
__herdr_apply_pane_theme 2>/dev/null
