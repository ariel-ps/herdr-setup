# Layouts

The layout example contains pane geometry and labels, without machine paths or saved agent sessions. To use it, fill in the directory you want the panes to open in:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/herdr/layouts"
jq --arg cwd "$PWD" \
  'walk(if type == "object" and .type == "pane" then .cwd = $cwd else . end)' \
  examples/layouts/four-panes.json \
  > "${XDG_CONFIG_HOME:-$HOME/.config}/herdr/layouts/four-panes.json"
```

Inside Herdr, run `herdr-layout-load four-panes <workspace-id>`, using the workspace ID shown by `herdr workspace list`.
