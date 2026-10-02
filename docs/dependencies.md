# Dependencies

Edit [`dependencies.json`](../dependencies.json), then run `./install.sh`.

| Field | Purpose |
| --- | --- |
| `packages.macos` | Homebrew formulae |
| `packages.linux` | Ubuntu/Debian packages |
| `tools` | Official installation scripts for tools missing from PATH |
| `herdr.version` | Herdr release to install when it is missing |
| `herdr.downloads` | SHA256 verification by OS and architecture |
| `plugins` | All selected plugins, each installed from its own repository |

A plugin entry:

```json
{
  "id": "cloudmanic.herdr-plus",
  "name": "Herdr Plus",
  "repository": "cloudmanic/herdr-plus",
  "subdir": "",
  "ref": "v0.1.24",
  "enabled": true
}
```

`ref` may be a release tag, branch, or full commit hash. Tags and branches are resolved to a commit before installation. To update a plugin, change `ref` and rerun the installer. Add an entry to install another plugin. Set `enabled` to `false` to disable it; deleting an entry simply stops managing it and does not uninstall anything.

To add a system prerequisite, append its name to the appropriate `packages` list. Package managers use available repository versions; plugin build scripts may download additional upstream assets.

Every plugin is fetched from its repository at the selected revision. This repository contains the installer and defaults, not plugin source. Colors, Alerts, Layouts, Sessions, Doomface, and Sidebar Menu can each be enabled independently.

Optional entry fields: `shell` names the plugin's zsh integration file; `config` names its default configuration file. Both are paths relative to the plugin root. Shell integration checks Herdr's enabled-plugin registry whenever a new zsh starts.

For repositories requiring authentication, sign in with `gh auth login` or provide `GH_TOKEN`/`GITHUB_TOKEN`. Credentials are passed to Git for the download without changing global Git configuration.

The tiny bootstrap step installs Python if it is missing so the installer can read JSON. Herdr is downloaded for the detected OS/architecture and its checksum is verified before installation. A pre-existing Herdr installation is kept and checked for compatibility; upgrading an incompatible existing version remains the user's package-manager operation.
