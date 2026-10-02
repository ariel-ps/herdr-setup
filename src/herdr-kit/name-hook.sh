#!/usr/bin/env zsh
# herdr event hook: keep a pane's agent name equal to the name its human gave
# the session, so `herdr agent prompt` and `herdr-agents send` have something to
# address other than w1:p6.
#
# The work is in bin/herdr-agent-name — this is only the adapter, for the same
# reason title-hook.sh is: the useful entry point has to be runnable by hand and
# by an agent shelling out, and an event hook is neither. Why the agent name and
# not the label, why only user-set names, and why this is not three entries in
# ~/.claude/settings.json are all in that file's header.
#
# pane.agent_status_changed is the trigger, which is indirect on purpose. The
# event that actually matters is `/rename`, and no such event exists — Claude
# writes the new name to ~/.claude/sessions/<pid>.json and tells nobody. But a
# rename is always followed by a prompt, and a prompt always moves the pane to
# working, so the next status change carries the new name in. The cost of that
# indirection is that a pane renamed and then left alone keeps its old herdr
# name until it is next used; run `herdr-agent-name` by hand if that matters.
#
# The pane comes from the event and is passed through as --pane, so this stays
# one pane's worth of work per status change — the same cost as title-hook —
# rather than re-syncing the whole grid every time any agent blinks.
#
# Env in: HERDR_PLUGIN_EVENT_JSON (pane_id, agent_status, agent, display_agent).
#   HERDR_AGENT_NAME_OFF=1     leave agent names alone

emulate -L zsh

# HERDR_PLUGIN_ROOT is set by herdr; the ${0:A:h} fallback keeps the hook
# runnable by hand, which is how it gets tested.
root="${HERDR_PLUGIN_ROOT:-${0:A:h}}"
command -v jq >/dev/null 2>&1 || exit 0

# Same config.sh the alert and title hooks read, and read here rather than in
# herdr-agent-name because the README documents that file as zsh while
# herdr-agent-name is sh.
config="${HERDR_PLUGIN_CONFIG_DIR:-$root}"
[[ -r "$config/config.sh" ]] && source "$config/config.sh"

[[ "${HERDR_AGENT_NAME_OFF:-0}" == 1 ]] && exit 0

pane=$(print -r -- "${HERDR_PLUGIN_EVENT_JSON:-}" | jq -r '.pane_id // empty' 2>/dev/null)
[[ -n "$pane" ]] || exit 0

# --quiet because a hook's stdout goes to the plugin command log, where one line
# per status change on nine panes buries everything else in it. Exit 0 always:
# a pane herdr refuses to rename is a collision, not a reason to make every
# subsequent status change look like a failing hook.
"$root/bin/herdr-agent-name" --quiet --pane "$pane" >/dev/null 2>&1

exit 0
