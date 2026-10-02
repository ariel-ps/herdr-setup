#!/usr/bin/env zsh
# herdr event hook: keep each pane's label saying what that pane is and what it
# is doing right now.
#
# The work is in bin/herdr-title — this is only the adapter, for the same reason
# bin/herdr-whoami is a script and not a function: the useful entry point has to
# be callable by hand and by an agent shelling out, and an event hook is neither.
# Everything about *why* the label rather than the terminal title, and why no
# counterpart undo hook, is in that file's header.
#
# pane.agent_status_changed is the whole trigger. The dotfiles ancestor needed
# eight Claude Code hook entries plus five Codex ones to see the same transitions,
# each wired by absolute path through a ~/.local/bin symlink, and each silently
# dead when that symlink dangled. herdr watches the pane instead of the agent, so
# one subscription covers every agent kind it supports, present and future.
#
# Env in: HERDR_PLUGIN_EVENT_JSON (pane_id, agent_status, agent, display_agent).
#   HERDR_TITLE_OFF=1          leave labels alone
#   HERDR_TITLE_SEP=' · '      stem/derived separator
#   HERDR_TITLE_BRANCH=0       repo without the branch
#   HERDR_TITLE_MAX_BRANCH=24  truncate longer branch names

emulate -L zsh

# HERDR_PLUGIN_ROOT is set by herdr; the ${0:A:h} fallback keeps the hook
# runnable by hand, which is how it gets tested.
root="${HERDR_PLUGIN_ROOT:-${0:A:h}}"
command -v jq >/dev/null 2>&1 || exit 0

# Same config.sh the alert hook reads, and read here rather than in herdr-title
# because the README documents that file as zsh while herdr-title is sh.
config="${HERDR_PLUGIN_CONFIG_DIR:-$root}"
[[ -r "$config/config.sh" ]] && source "$config/config.sh"
export HERDR_TITLE_OFF HERDR_TITLE_SEP HERDR_TITLE_BRANCH HERDR_TITLE_MAX_BRANCH

[[ "${HERDR_TITLE_OFF:-0}" == 1 ]] && exit 0

# Status and agent are passed through rather than re-read: this payload is the
# event, and the pane record herdr-title fetches a moment later is whatever the
# server has settled on since — which on a fast working/done pair is the next
# state, not this one.
#
# `pane_status`, not `status`: $status is a read-only special in zsh, an alias
# for $?, so assigning it aborts the hook at this line every single time. Under
# `emulate -L zsh` too — emulation does not make the specials writable. Nothing
# reported it because the hook had no [[events]] entry, so the two faults hid
# each other: a hook that never ran and would have failed if it had.
pane=$(print -r -- "${HERDR_PLUGIN_EVENT_JSON:-}" | jq -r '.pane_id // empty' 2>/dev/null)
pane_status=$(print -r -- "${HERDR_PLUGIN_EVENT_JSON:-}" | jq -r '.agent_status // .status // empty' 2>/dev/null)
agent=$(print -r -- "${HERDR_PLUGIN_EVENT_JSON:-}" | jq -r '.agent // .display_agent // empty' 2>/dev/null)

[[ -n "$pane" ]] || exit 0

# Built as an array, because `${x:+--status "$x"}` is a bash idiom and this is
# zsh: zsh does not word-split an unquoted expansion, so that form passes the
# single argument `--status working` and herdr-title rejects it as an unknown
# option. With stderr redirected below, the rejection is invisible and the hook
# still exits 0 — the pane simply never gets a label.
args=(--quiet --pane "$pane")
[[ -n "$pane_status" ]] && args+=(--status "$pane_status")
[[ -n "$agent" ]]       && args+=(--agent "$agent")

# --quiet because a hook's stdout goes to the plugin command log, where one line
# per status change on nine panes buries everything else in it.
"$root/bin/herdr-title" "${args[@]}" >/dev/null 2>&1

exit 0
