# Source from an interactive zsh; installer writes the local paths file.
typeset -U path
path=("$HOME/.local/bin" "$HOME/.cargo/bin" $path)
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/herdr-setup/paths.zsh" ]]; then
  source "${XDG_CONFIG_HOME:-$HOME/.config}/herdr-setup/paths.zsh"
fi

if [[ -n "$HERDR_SETUP_DEV_ENV" && -z "$DEV_ENV_ROOT" ]]; then
  if [[ "$HERDR_SETUP_PROFILE" == full ]]; then
    source "$HERDR_SETUP_DEV_ENV/init.zsh"
  else
    typeset -g DEV_ENV_ROOT="$HERDR_SETUP_DEV_ENV"
    autoload -Uz compinit
    compinit
    __herdr_setup_source() { emulate -L zsh; source "$1"; }
    for setup_tool in ai/agents terminal/alert terminal/term terminal/navigation; do
      for setup_file in "$DEV_ENV_ROOT/scripts/$setup_tool/"*.sh(N); do
        __herdr_setup_source "$setup_file"
      done
    done
    unfunction __herdr_setup_source
    unset setup_tool setup_file
  fi
fi

if [[ -n "$HERDR_SETUP_KIT" && -r "$HERDR_SETUP_KIT/shell/herdr.sh" ]]; then
  source "$HERDR_SETUP_KIT/shell/herdr.sh"
  __herdr_apply_pane_theme 2>/dev/null
fi
