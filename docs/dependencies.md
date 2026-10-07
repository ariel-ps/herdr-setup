# Dependencies

Edit [`dependencies.json`](../dependencies.json), then run `./install.sh`.

| Field | Purpose |
| --- | --- |
| `packages.macos` | Homebrew formulae |
| `packages.linux` | Ubuntu/Debian packages |
| `packages.fedora` | Fedora packages or file providers, installed through dnf |
| `tools` | Installation scripts or argument-array commands for tools missing from PATH |
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

Fedora entries such as `/usr/bin/curl` and `/usr/bin/ffplay` let dnf choose the package providing that executable, while keeping a compatible installed provider.

Navigation helpers in the shell loader use fzf, eza, bat, and fd. Ubuntu/Debian name the last two executables `batcat` and `fdfind`; the shell loader handles these names. Lazygit uses delta for diffs. Homebrew supplies Lazygit on macOS; on Linux, the pinned `tools.lazygit.command` builds it with Go into `~/.local/bin`, without adding a package repository. Change that version in this manifest to select a different release for new installations. Existing executables are kept.

`ripgrep` is installed alongside `fd` for the [LazyVim](https://www.lazyvim.org/) Neovim config in [`config/nvim`](../config/nvim): Telescope's live grep needs `ripgrep`, and its file finder needs `fd`.

[Treehouse](https://github.com/kunchenguid/treehouse) (required by Journal Repo) is installed from upstream release binaries via `tools.treehouse.url`, not `go install`, because v3 tags still declare a pre–Go-module-v3 `go.mod` path and `go install` fails with “module path must match major version”.

The package lists are tested with Ubuntu 24.04 and Fedora 44; use Debian 13 or newer for the listed navigation packages. The pinned Lazygit build needs Go 1.25; Go 1.21+ automatically downloads the required toolchain when needed.

Every plugin is fetched from its repository at the selected revision. This repository contains the installer and defaults, not plugin source. Colors, Alerts, Layouts, Sessions, Doomface, Journal Repo, and Sidebar Menu can each be enabled independently. Journal Repo builds the `journal-repo` Rust binary into `libexec/` on install (ignored for git cleanliness checks).

If a plugin is already linked from a **local path** in Herdr, setup keeps that checkout and does not replace it with the GitHub pin.

Optional entry fields: `shell` names the plugin's zsh integration file; `shell_bash` names its bash integration file; `config` names its default configuration file. All are paths relative to the plugin root. Shell integration checks Herdr's enabled-plugin registry whenever a new shell starts.

For repositories requiring authentication, sign in with `gh auth login` or provide `GH_TOKEN`/`GITHUB_TOKEN`. Credentials are passed to Git for the download without changing global Git configuration.

The tiny bootstrap step installs Python if it is missing so the installer can read JSON. Herdr is downloaded for the detected OS/architecture and its checksum is verified before installation. A pre-existing Herdr installation is kept and checked for compatibility; upgrading an incompatible existing version remains the user's package-manager operation.
