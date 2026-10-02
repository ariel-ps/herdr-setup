#!/usr/bin/env zsh
# herdr — agent multiplexer. Terse views over `herdr agent list`.
#
# The CLI answers in JSON on one line, which is right for scripts and unreadable
# at a glance. These collapse it to a column per question you actually ask.
#
#   herdr-agents              # every pane: id, kind, state, native session ref
#   herdr-whoami [--all]      # the name of the pane you are in (bin/, for agents)
#   herdr-unlinked            # panes herdr cannot resume after a server restart
#   herdr-link <pane> <id>    # attach a session ref by hand
#   herdr-themes-build [N]    # pick N distinct dark palettes, cache their OSC
#   herdr-colorize [pane...]  # repaint panes sitting at a shell prompt
#   herdr-layout-save <name>  # store the current tab's pane arrangement
#   herdr-layout-load <name>  # rebuild that arrangement as a fresh tab
#   herdr-layout-up <name>    # that tab, its workspace, and every agent resumed
#   herdr-layout-list         # what has been saved
#   herdr-grid-agents [n] [kind]  # a tab of n agent panes, herdr's kitty-grid
#
# layout.export and layout.apply are first-class socket methods with a published
# schema, but `herdr layout` is not a command — they have no CLI at all. These
# are that CLI, over `nc -U`, since the protocol is one JSON object per line.
#
# What comes back is structure only: splits, ratios, labels, cwd, env and launch
# commands. Not PTYs, not scrollback, not running processes. Loading a layout
# gives empty shells in the right shape; the agents that were in them come back
# through their own resume path, not this one.
#
# Colour is the other half, and herdr gives it no purchase: one client-wide
# theme, no per-pane setting. What it does give is a pane whose default colours
# it only resets when the bare shell owns the foreground off the alternate
# screen (src/pane/osc.rs, should_restore_host_terminal_theme). Agents hold the
# alternate screen, so a colour set once outlives the agent that took the pane.
#
# Slot comes from $HERDR_PANE_ID, which herdr injects into every managed pane.
# Picking maximally-distinct palettes is kitty-theme-ga's job over in `terminal`
# and far too slow to run per shell, so `herdr-themes-build` runs it once and
# caches finished OSC strings; applying one is a single `sed`.
#
# Colour has to be set while the pane is still a shell. OSC 11 changes the
# terminal's default background, and a full-screen agent paints its own across
# the whole viewport — so writing it to a pane already running Claude or Codex
# succeeds at the pty and changes nothing on screen. __herdr_apply_pane_theme
# runs at shell startup, before any agent takes the pane, which is why the
# colour survives: herdr only resets a pane's default colours when the bare
# shell owns the foreground off the alternate screen (src/pane/osc.rs,
# should_restore_host_terminal_theme), and an agent never gives that up.
#
# `herdr-colorize` is the same write for panes that are back at a prompt — after
# a rebuild, or once an agent exits. It cannot retrofit colour onto a running
# one; the alerts plugin composites a graphics layer for that instead.
#
# Applying at startup is a side effect at source time, which a file sourced into
# every interactive shell must not have (CONVENTIONS.md), so it stays a function
# here and is called from ~/.zshrc:
#
#   __herdr_apply_pane_theme   # no-op outside herdr and without a theme cache
#
# `herdr-unlinked` exists because a pane only restores its conversation when it
# reported a native session ref, and neither automatic path is dependable. Argv
# capture wants exactly `codex resume <id>` (src/agent_resume.rs,
# persisted_session_from_launch_args), so any extra flag defeats it. The
# integration hook usually fills the gap on the agent's next turn, but not
# always — observed a codex pane complete a full turn and stay unreported.
# So `herdr-link` is the fix, not prompting and hoping. Check before restarting
# the server, not after: an unlinked pane comes back a dead shell.
#
# `herdr-whoami` lives in bin/ rather than here because its callers are agents
# shelling out with `sh -c`, which never sourced this file — hence the PATH
# prepend below. It answers the one question a pane cannot answer about itself:
# herdr has three name fields — agent name, pane label, terminal title — each
# independently settable and frequently disagreeing, so the script tries them in
# order of addressability and reports which one won. Details in its header.

_HERDR_BIN_DIR="${0:A:h:h}/bin"
if [[ -d "$_HERDR_BIN_DIR" && ":$PATH:" != *":$_HERDR_BIN_DIR:"* ]]; then
  path=("$_HERDR_BIN_DIR" $path)
fi
unset _HERDR_BIN_DIR

# The kit root, from this file rather than an install prefix — the same anchor
# whether it was installed by herdr, linked from a checkout, or just sourced.
#
# Captured here, at source time, and not inside the function below. Inside a zsh
# function $0 is the function's own name, so ${0:A:h:h} evaluated at call time
# expands `__herdr_root` against $PWD and walks two directories up from wherever
# the caller happens to stand: /Users from $HOME, /private from /tmp. Nothing
# errors — the callers just build a path into a directory that does not exist
# and report the file missing, naming a path no one ever configured. Same
# source-time reason the bin prepend above works.
typeset -g _HERDR_KIT_ROOT="${0:A:h:h}"
__herdr_root() { print -r -- "${HERDR_KIT_ROOT:-$_HERDR_KIT_ROOT}"; }

__herdr_ready() {
  command -v herdr >/dev/null 2>&1 || { echo "herdr: not installed" >&2; return 1; }
  command -v jq >/dev/null 2>&1 || { echo "herdr: jq not found" >&2; return 1; }
  [ "$(herdr status server 2>/dev/null | awk '/^status:/{print $2}')" = running ] || {
    echo "herdr: server not running" >&2; return 1
  }
}

# `herdr-agents` is bin/herdr-agents, not a function here. It was one — the
# roster query above this comment — until the CLI grew send, read, broadcast and
# roles, which agents invoke by name through `sh -c`. A function and an
# executable of the same name are not a tie: the function wins in every
# interactive shell that sourced this file, so `herdr-agents send x "..."` would
# reach the four-line lister and fail on an argument it does not take, while the
# same command from an agent found the real one. Deleted rather than renamed,
# because the roster is `herdr-agents` with no arguments either way.

# usage: herdr-unlinked
#   Panes with no native session ref. These lose their conversation on restart.
herdr-unlinked() {
  __herdr_ready || return 1
  local rows
  rows=$(herdr agent list | jq -r '
    .result.agents[]
    | select(.agent_session.value == null)
    | [.pane_id, .agent, .terminal_title_stripped] | @tsv')
  [ -n "$rows" ] || { echo "all agent panes are linked"; return 0; }
  print -r -- "$rows" | column -t -s $'\t'
}

# usage: herdr-link <pane-id> <native-session-id>
#   Agent kind is read back from the pane, so only the ref has to be right.
herdr-link() {
  __herdr_ready || return 1
  local pane=$1 sid=$2 kind
  [ -n "$pane" ] && [ -n "$sid" ] || { echo "usage: herdr-link <pane-id> <session-id>" >&2; return 2; }
  kind=$(herdr agent list | jq -r --arg p "$pane" '.result.agents[] | select(.pane_id==$p) | .agent')
  [ -n "$kind" ] || { echo "herdr: no agent in $pane" >&2; return 1; }
  herdr pane report-agent-session "$pane" --source "herdr:$kind" --agent "$kind" \
    --agent-session-id "$sid" || return 1
  herdr agent list | jq -r --arg p "$pane" '
    .result.agents[] | select(.pane_id==$p)
    | "\(.pane_id) \(.agent) -> \(.agent_session.value // "STILL UNLINKED")"'
}

__herdr_theme_cache() { print -r -- "${XDG_CACHE_HOME:-$HOME/.cache}/herdr-pane-themes"; }

# Run one of the kit's python scripts. uv first, bare python3 only if it really
# executes — `command -v python3` is not evidence that it does. A shim earlier on
# PATH answers the lookup and then refuses the call: the modern-python Claude
# plugin installs exactly such a shim, and under it this kit failed with that
# guard's error rather than anything the kit could explain. uv also needs no
# system interpreter at all, which is why the redalert fetcher already used it.
__herdr_py() {
  if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "$@"
  elif python3 -c '' >/dev/null 2>&1; then
    python3 "$@"
  else
    echo "herdr: need uv, or a python3 that actually runs" >&2; return 1
  fi
}

# usage: herdr-themes-build [count] [--print]
#   Slow and deliberate; the result is what every new pane reads at startup.
herdr-themes-build() {
  __herdr_py "$(__herdr_root)/scripts/theme-cache.py" "$@"
}

# Resolve a pane id to its cached OSC payload. Silent on anything unexpected so
# a missing cache is never a broken prompt.
__herdr_payload_for() {
  local dir count slot
  dir=$(__herdr_theme_cache)
  [ -r "$dir/current" ] || return 1
  count=$(<"$dir/current")
  [ -r "$dir/$count.txt" ] || return 1
  # Pane ids run p1..p9 then pA, pB — base 36, not decimal. Checked by stripping
  # every alnum rather than a glob, since the sourcing emulate has no extendedglob.
  slot=${(U)1##*p}
  [ -n "$slot" ] && [ -z "${slot//[0-9A-Z]/}" ] || return 1
  slot=$(( 36#$slot ))
  sed -n "$(( (slot - 1) % count + 1 ))p" "$dir/$count.txt"
}

__herdr_apply_pane_theme() {
  [[ -o interactive ]] || return 0
  [ -n "${HERDR_PANE_ID:-}" ] || return 0
  local payload
  payload=$(__herdr_payload_for "$HERDR_PANE_ID") || return 0
  [ -n "$payload" ] && printf "$payload"
  return 0
}

# usage: herdr-colorize [pane-id ...]
#   Repaint existing panes without restarting them, by writing the sequence to
#   each pane's pty slave: those bytes surface on the master side as ordinary
#   pane output, which is the emulator's input, never the agent's.
#
#   Only panes at a shell prompt change visibly. A pane running a full-screen
#   agent accepts the write and looks identical, because that agent is painting
#   its own background over the viewport — the reported success is the pty
#   accepting bytes, not the screen changing. Use it after a rebuild or once an
#   agent exits; for a running one the alerts plugin composites a layer instead.
herdr-colorize() {
  __herdr_ready || return 1
  local -a panes
  if (( $# )); then
    panes=("$@")
  else
    panes=("${(@f)$(herdr pane list | jq -r '.result.panes[].pane_id')}")
  fi
  local pane pid tty payload
  for pane in $panes; do
    payload=$(__herdr_payload_for "$pane") || { echo "$pane: no cached theme" >&2; continue; }
    pid=$(herdr pane process-info --pane "$pane" 2>/dev/null | jq -r '.result.process_info.shell_pid // empty')
    [ -n "$pid" ] || { echo "$pane: no shell pid" >&2; continue; }
    tty=$(ps -o tty= -p "$pid" 2>/dev/null | tr -d ' ')
    [ -n "$tty" ] && [ -w "/dev/$tty" ] || { echo "$pane: no writable tty" >&2; continue; }
    printf "$payload" > "/dev/$tty" && echo "$pane -> /dev/$tty"
  done
}

__herdr_layout_dir() { print -r -- "${XDG_CONFIG_HOME:-$HOME/.config}/herdr/layouts"; }

# Claude encodes a project directory by replacing every / and . with -.
__herdr_project_dir() {
  print -r -- "$HOME/.claude/projects/${${1:A}//[\/.]/-}"
}

# One request, one response. The daemon speaks JSON lines over its unix socket,
# so nc is a complete client here — no token and no websocket, unlike Xirp.
__herdr_rpc() {
  local sock="${XDG_CONFIG_HOME:-$HOME/.config}/herdr/herdr.sock"
  [ -S "$sock" ] || { echo "herdr: no socket at $sock (is the server running?)" >&2; return 1; }
  command -v nc >/dev/null 2>&1 || { echo "herdr: nc not found" >&2; return 1; }
  printf '%s\n' "$1" | nc -U "$sock"
}

# usage: herdr-layout-save <name> [tab-id]
#   Defaults to the active tab. Overwrites an existing name without asking —
#   these are cheap to recreate and a prompt during a save is worse than a lost one.
herdr-layout-save() {
  __herdr_ready || return 1
  local name=$1 tab=$2 params='{}' out dir
  [ -n "$name" ] || { echo "usage: herdr-layout-save <name> [tab-id]" >&2; return 2; }
  [ -n "$tab" ] && params="{\"tab_id\":\"$tab\"}"

  out=$(__herdr_rpc "{\"id\":\"save\",\"method\":\"layout.export\",\"params\":$params}") || return 1
  print -r -- "$out" | jq -e '.result.layout' >/dev/null 2>&1 || {
    echo "herdr: export failed: $(print -r -- "$out" | jq -r '.error.code // .' 2>/dev/null)" >&2
    return 1
  }

  dir=$(__herdr_layout_dir); mkdir -p "$dir"
  print -r -- "$out" | jq '.result.layout' > "$dir/$name.json" || return 1
  echo "saved $name ($(print -r -- "$out" | jq '[.result.layout.root|..|objects|select(.type=="pane")]|length') panes) -> $dir/$name.json"
  __herdr_layout_snap_agents "$name" "$(print -r -- "$out" | jq -r '.result.layout.tab_id')"
}

# The conversation half of a layout: one entry per pane that is running an agent,
# holding the session id it is in and the opening line of that session.
#
# The id comes out of the pane's own process arguments. herdr has a session ref
# of its own, but it is only populated when herdr recognised the launch — the
# argv shape it looks for does not match every start, and `agent list` omits the
# field entirely when it is empty. Process arguments are there either way. A pane
# started without --resume has no id in them, so the newest session in its
# directory is the best available guess; two fresh agents in one directory are
# the case that guess gets wrong.
__herdr_layout_snap_agents() {
  local name=$1 tab=$2 pane label cwd pid sid prompt kind
  local sidecar="$(__herdr_layout_dir)/$name.agents.json" entries='{}'

  while IFS=$'\t' read -r pane label cwd kind; do
    [ -n "$label" ] && [ "$kind" != null ] || continue
    sid=$(herdr pane process-info --pane "$pane" \
      | jq -r --arg k "$kind" 'first(.result.process_info.foreground_processes[]
           | select(.argv0 == $k) | .argv | index("--resume") as $i
           | if $i then .[$i + 1] else empty end) // empty')
    [ -n "$sid" ] || sid=$(__herdr_py "$(__herdr_root)/bin/herdr-session-pick" newest "$cwd")
    [ -n "$sid" ] || continue
    prompt=$(__herdr_py "$(__herdr_root)/bin/herdr-session-pick" prompt "$cwd" "$sid")
    entries=$(print -r -- "$entries" | jq --arg l "$label" --arg s "$sid" --arg p "$prompt" \
      --arg k "$kind" '.[$l] = {kind: $k, session: $s, match: $p}')
  done < <(herdr pane list | jq -r --arg tab "$tab" \
    '.result.panes[] | select(.tab_id == $tab)
     | [.pane_id, (.label // empty), .cwd, (.agent // null)] | @tsv')

  [ "$entries" = '{}' ] && return 0
  print -r -- "$entries" | jq . > "$sidecar" || return 1
  echo "  agents: $(print -r -- "$entries" | jq -r 'keys | join(", ")') -> ${sidecar:t}"
}

# usage: herdr-layout-load <name> [workspace-id]
#   Always creates a new tab. Passing the saved tab_id back would make herdr
#   replace that tab, and a load is not worth destroying live panes over.
herdr-layout-load() {
  __herdr_ready || return 1
  local name=$1 ws=$2 file root params out
  [ -n "$name" ] || { echo "usage: herdr-layout-load <name> [workspace-id]" >&2; return 2; }
  file="$(__herdr_layout_dir)/$name.json"
  [ -r "$file" ] || { echo "herdr: no saved layout $name" >&2; return 1; }

  [ -n "$ws" ] || ws=$(jq -r '.workspace_id // empty' "$file")
  root=$(jq -c '.root' "$file") || return 1
  params=$(jq -nc --arg ws "$ws" --arg label "$name" --argjson root "$root" \
    '{workspace_id:$ws, tab_label:$label, focus:true, root:$root}')

  out=$(__herdr_rpc "{\"id\":\"load\",\"method\":\"layout.apply\",\"params\":$params}") || return 1
  print -r -- "$out" | jq -e '.result' >/dev/null 2>&1 || {
    echo "herdr: apply failed: $(print -r -- "$out" | jq -r '.error.code // .' 2>/dev/null)" >&2
    return 1
  }
  echo "loaded $name -> $(print -r -- "$out" | jq -r '.result.tab.tab_id // "new tab"')"
  echo "note: shells only — agents come back via herdr-link/resume, not this" >&2
}

# usage: herdr-layout-list
herdr-layout-list() {
  local dir; dir=$(__herdr_layout_dir)
  [ -d "$dir" ] || { echo "no saved layouts"; return 0; }
  # Listed with find rather than a glob qualifier: (N) depends on shell options
  # this file cannot assume, and an unmatched bare glob is a hard error.
  local f found=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    found=1
    printf "%-22s %s panes\n" "${${f:t}:r}" "$(jq '[.root|..|objects|select(.type=="pane")]|length' "$f" 2>/dev/null)"
  done < <(find "$dir" -maxdepth 1 -name '*.json' 2>/dev/null | sort)
  (( found )) || echo "no saved layouts"
}

# usage: herdr-layout-up <name> [kind]
#   Workspace, layout and agents in one line: find a workspace labelled <name> or
#   create one, load the layout into it, then start an agent in every pane under
#   the pane's own label.
#
#   Resolution is by label because a saved layout carries the workspace id it was
#   exported from, and those do not survive a server restart — a bare
#   herdr-layout-load of a layout saved weeks ago dies on workspace_not_found.
#
#   `workspace create` always brings an empty tab of its own and layout.apply
#   cannot fill an existing one without replacing it, so the layout arrives as a
#   second tab and the placeholder is closed afterwards.
#
#   The sidecar `<name>.agents.json` that herdr-layout-save writes alongside the
#   layout carries the conversations: per pane label, the session id it was in
#   and that session's opening line. The id is tried first and the opening line
#   is the fallback for when it no longer resolves. Panes with no entry, and
#   panes whose conversation is gone, start fresh.
herdr-layout-up() {
  __herdr_ready || return 1
  local name=$1 kind="${2:-claude}" ws='' placeholder='' created tab pane label cwd
  local sidecar match sid pane_kind
  [ -n "$name" ] || { echo "usage: herdr-layout-up <name> [kind]" >&2; return 2; }
  [ -r "$(__herdr_layout_dir)/$name.json" ] || { echo "herdr: no saved layout $name" >&2; return 1; }
  sidecar="$(__herdr_layout_dir)/$name.agents.json"

  # An agent name is unique among live agents, so a second run would half-fail
  # anyway — but it would still leave a stray tab, and any pane that did start
  # would open a second view of a conversation already running elsewhere.
  local live
  live=$(herdr agent list | jq -r '.result.agents[].name // empty' \
    | grep -Fx -f <(jq -r '[.root|..|objects|select(.type=="pane")|.label//empty][]' \
        "$(__herdr_layout_dir)/$name.json") 2>/dev/null | head -3)
  [ -n "$live" ] && {
    echo "herdr: $name is already up (${${(f)live}:0:3}) — close it first" >&2; return 1
  }

  ws=$(herdr workspace list | jq -r --arg l "$name" \
    'first(.result.workspaces[] | select(.label == $l) | .workspace_id) // empty') || return 1
  if [ -z "$ws" ]; then
    created=$(herdr workspace create --label "$name" --no-focus) || return 1
    ws=$(print -r -- "$created" | jq -r '.result.workspace.workspace_id')
    placeholder=$(print -r -- "$created" | jq -r '.result.tab.tab_id')
  fi

  herdr-layout-load "$name" "$ws" || return 1
  [ -n "$placeholder" ] && herdr tab close "$placeholder" >/dev/null 2>&1

  tab=$(herdr workspace get "$ws" | jq -r '.result.workspace.active_tab_id')
  local -a args
  while IFS=$'\t' read -r pane label cwd; do
    [ -n "$pane" ] || continue
    args=()
    pane_kind=$kind
    if [ -r "$sidecar" ]; then
      # A saved fleet can be mixed — the kind travels per pane, the argument is
      # only the default for panes the sidecar says nothing about.
      pane_kind=$(jq -r --arg l "$label" --arg k "$kind" '.[$l].kind // $k' "$sidecar")
      # The pinned id first, the opening line as the fallback: an id can be
      # deleted or archived, and then the prompt is what still finds the pane's
      # conversation.
      sid=$(jq -r --arg l "$label" '.[$l].session // empty' "$sidecar")
      [ -n "$sid" ] && [ ! -f "$(__herdr_project_dir "$cwd")/$sid.jsonl" ] && sid=''
      [ -n "$sid" ] || {
        match=$(jq -r --arg l "$label" '.[$l].match // empty' "$sidecar")
        [ -n "$match" ] && sid=$(__herdr_py "$(__herdr_root)/bin/herdr-session-pick" \
          match "$cwd" "$match" 2>/dev/null)
      }
      [ -n "$sid" ] && args+=(--resume "$sid")
    fi
    [ -n "$HERDR_AGENT_ARGS" ] && args+=(${=HERDR_AGENT_ARGS})

    if herdr agent start "$label" --kind "$pane_kind" --pane "$pane" \
         ${args:+--} "${args[@]}" >/dev/null 2>&1; then
      # Hand the id to herdr as well, or the pane comes back a dead shell after a
      # server restart. herdr only captures a resume id from argv in one exact
      # shape and misses ours, and it takes a reported one only under its own
      # source string — `herdr:<kind>`, which is what herdr-link sends.
      [ -n "$sid" ] && herdr-link "$pane" "$sid" >/dev/null 2>&1
      echo "$pane  $label  $pane_kind${sid:+  resumed ${sid[1,8]}}"
    else
      echo "$pane  $label  $pane_kind  FAILED (pane left at its prompt)" >&2
    fi
    sid=''
  done < <(herdr pane list | jq -r --arg tab "$tab" \
    '.result.panes[] | select(.tab_id == $tab)
     | [.pane_id, (.label // (.pane_id | sub("^.*:"; ""))), .cwd] | @tsv')
  echo "workspace $ws, tab $tab" >&2
}

# usage: herdr-grid-agents [count] [kind] [label]
#   The herdr answer to kitty-grid-claude-danger. kitty's version opens a tab of
#   N windows each running `zsh -lic claude-danger`; that cannot work here,
#   because `kitty @` does not see panes herdr owns.
#
#   Splitting and starting are separate in herdr on purpose: `agent start`
#   requires a pane already at its prompt and never creates layout. So build the
#   tab first, then start an agent in each pane, naming them <label>-1..N so
#   `herdr agent prompt <name>` works immediately and the session refs that
#   survive a restart have somewhere to attach.
#
#   Splits alternate right/down rather than repeating one direction, which
#   otherwise leaves unusably narrow columns past about four panes.
#
#   DANGER: each pane is an unsupervised agent. Flags come from
#   HERDR_AGENT_ARGS, empty by default — the caller decides whether to bypass
#   permission checks, not this helper.
herdr-grid-agents() {
  __herdr_ready || return 1
  local want="${1:-9}" kind="${2:-claude}" label="${3:-}"
  [[ "$want" == <-> ]] && (( want > 0 )) \
    || { echo "herdr-grid-agents: count must be a positive number, got: ${1:-}" >&2; return 2; }

  if [ -z "$label" ]; then
    [ "$PWD" = "$HOME" ] && label=home || label="${PWD:t}"
  fi
  # herdr names are [a-z][a-z0-9_-]{0,31} and must be unique among live agents.
  label=$(print -r -- "${label:l}" | tr -c 'a-z0-9_-' '-' | sed 's/^[^a-z]*//; s/-*$//')
  [ -n "$label" ] || { echo "herdr-grid-agents: could not derive a usable label; pass one" >&2; return 1; }

  local created tab root pane prev dir i name
  created=$(herdr tab create --label "$label" --cwd "$PWD") || return 1
  tab=$(print -r -- "$created" | jq -r '.result.tab.tab_id')
  root=$(print -r -- "$created" | jq -r '.result.root_pane.pane_id')
  local -a panes=("$root")

  prev=$root
  for (( i = 2; i <= want; i++ )); do
    (( i % 2 == 0 )) && dir=right || dir=down
    pane=$(herdr pane split "$prev" --direction "$dir" --no-focus --cwd "$PWD" \
      | jq -r '.result.pane.pane_id') || return 1
    [ -n "$pane" ] && [ "$pane" != null ] || break
    panes+=("$pane")
    prev=$pane
  done

  i=1
  for pane in $panes; do
    name="$label-$i"
    # Named before start so a failed launch still leaves an addressable pane.
    herdr pane rename "$pane" "$name" >/dev/null 2>&1
    if herdr agent start "$name" --kind "$kind" --pane "$pane" \
         ${HERDR_AGENT_ARGS:+-- ${=HERDR_AGENT_ARGS}} >/dev/null 2>&1; then
      echo "$pane  $name  $kind"
    else
      echo "$pane  $name  $kind  FAILED (pane left at its prompt)" >&2
    fi
    (( i++ ))
  done
  echo "tab $tab: ${#panes} panes in $PWD" >&2
}

# usage: herdr-sounds-sync [game ...]
#   Download the game sound and sprite packs the alert hook draws from.
#
#   Not committed, and deliberately so: the packs are ~150MB of ripped game
#   audio across seven titles, none of it ours to redistribute. They come from
#   archive.org on demand into XDG cache, which is the same arrangement the
#   dotfiles version used and the reason a plugin can carry the mapping without
#   carrying the media.
#
#   Everything degrades without them — the alert falls back to the two bundled
#   clips and skips the sprite — so this is optional, not setup.
herdr-sounds-sync() {
  local root; root=$(__herdr_root)
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/herdr-kit"
  local map="$root/sounds/packs.json"

  command -v jq >/dev/null 2>&1 || { echo "herdr: jq not found" >&2; return 1; }
  [ -r "$map" ] || { echo "herdr: pack map missing at $map" >&2; return 1; }

  local -a games
  if (( $# )); then games=("$@"); else games=(${(f)"$(jq -r '.games|keys[]' "$map")"}); fi

  local game id rc=0
  for game in $games; do
    # packs.json stores a scheme-tagged source per game ("archive:<item>"),
    # because sprites for the same game come from git instead. Only the
    # archive.org half is a sound pack.
    id=$(jq -r --arg g "$game" '.games[$g].sounds // "" | sub("^archive:"; "")' "$map")
    [ -n "$id" ] || { echo "herdr-sounds-sync: unknown game '$game'" >&2; rc=1; continue; }
    echo "herdr-sounds-sync: $game ($id)" >&2
    if [ "$game" = redalert ]; then
      # This game's clips live inside its own encrypted MIX archives, so it
      # needs a different fetcher and Blowfish — hence uv rather than python3.
      command -v uv >/dev/null 2>&1 \
        || { echo "herdr-sounds-sync: uv needed for $game" >&2; rc=1; continue; }
      uv run --no-project --with pycryptodome python \
        "$root/scripts/fetch-redalert-sounds.py" "$cache/sounds/$game" || rc=1
    else
      __herdr_py "$root/scripts/fetch-game-sounds.py" "$id" "$cache/sounds/$game" || rc=1
    fi
  done
  return $rc
}
