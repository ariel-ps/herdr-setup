# Interactive Bash/Zsh helpers, based on Datalumina's folder navigation guide.
# shellcheck disable=SC1090,SC1091
if [[ $- == *i* && ${_HERDR_FOLDER_TOOLS_LOADED:-} != 1 ]]; then
  _HERDR_FOLDER_TOOLS_LOADED=1
  export BAT_THEME="${BAT_THEME:-TwoDark}"
  export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS:---height 40% --layout=reverse --border --cycle}"
  if command -v fd >/dev/null 2>&1; then
    export FZF_DEFAULT_COMMAND="${FZF_DEFAULT_COMMAND:-fd --type f --hidden --follow --exclude .git}"
  elif command -v fdfind >/dev/null 2>&1; then
    export FZF_DEFAULT_COMMAND="${FZF_DEFAULT_COMMAND:-fdfind --type f --hidden --follow --exclude .git}"
  fi
  _herdr_tool_shell=zsh
  [[ -n ${BASH_VERSION:-} ]] && _herdr_tool_shell=bash
  if command -v fzf >/dev/null 2>&1 && [[ -t 0 && -t 1 ]]; then
    if _herdr_fzf_init=$(fzf --"$_herdr_tool_shell" 2>/dev/null); then
      eval "$_herdr_fzf_init"
    else
      # Older distro fzf packages ship integration as files instead of --bash/--zsh.
      for _herdr_fzf_dir in /usr/share/fzf/shell /usr/share/doc/fzf/examples; do
        if [[ -r "$_herdr_fzf_dir/key-bindings.$_herdr_tool_shell" ]]; then
          source "$_herdr_fzf_dir/key-bindings.$_herdr_tool_shell"
          [[ -r "$_herdr_fzf_dir/completion.$_herdr_tool_shell" ]] && source "$_herdr_fzf_dir/completion.$_herdr_tool_shell"
          break
        fi
      done
      if [[ $_herdr_tool_shell == bash && -r /usr/share/bash-completion/completions/fzf ]]; then
        source /usr/share/bash-completion/completions/fzf
      fi
    fi
  fi
  if command -v eza >/dev/null 2>&1; then
    alias ls >/dev/null 2>&1 || typeset -f ls >/dev/null 2>&1 || alias ls='eza'
    alias ll >/dev/null 2>&1 || typeset -f ll >/dev/null 2>&1 || alias ll='eza -la'
    alias tree >/dev/null 2>&1 || typeset -f tree >/dev/null 2>&1 || alias tree='eza --tree'
  fi
  if ! alias cat >/dev/null 2>&1 && ! typeset -f cat >/dev/null 2>&1; then
    if command -v bat >/dev/null 2>&1; then
      alias cat='bat'
    elif command -v batcat >/dev/null 2>&1; then
      alias cat='batcat'
    fi
  fi
  unset _herdr_tool_shell _herdr_fzf_init _herdr_fzf_dir
fi
