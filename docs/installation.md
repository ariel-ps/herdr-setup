# Installation details

The installer creates its own directories under your home. No existing project layout or Docker installation is needed. The original checkout can be removed after installation.

## Requirements

On macOS, Homebrew must be available as `brew`. Linux installation uses `apt-get` on Ubuntu/Debian or `dnf` on Fedora, with root or sudo privileges.

The curl method needs a POSIX shell, `curl`, `tar`, and CA certificates. A minimal Linux image may need these installed first. You also need a writable home directory and network access to package repositories and plugin build dependencies.

The installer supplies Python, uv, Rust/Cargo, Go, and other packages listed in [`dependencies.json`](../dependencies.json). An existing Herdr binary is kept and must be version 0.9.3 or newer.

Your terminal application and coding-agent CLIs are installed separately. The Linux desktop test uses Kitty.

## Options

```sh
./install.sh --dry-run          # Show the plan without installing
./install.sh --no-shell         # Leave .zshrc untouched
./install.sh --replace-config   # Back up and replace existing defaults
```

`--dry-run` and `--help` skip bootstrapping and require Python 3.11+ or uv already available.

For curl installation, pass options using `| sh -s -- --dry-run`. Set `HERDR_SETUP_REF` on the shell running the installer to select a branch, commit, or release tag; the default is `main`.

## Files and backups

| Files | Default | Override |
| --- | --- | --- |
| Shell loader and backups | `~/.local/share/herdr-setup` | `XDG_DATA_HOME` |
| Herdr configuration | `~/.config/herdr` | `XDG_CONFIG_HOME` |
| Installed plugins | `~/.config/herdr/plugins` | `XDG_CONFIG_HOME` |
| Cached media | `~/.cache/herdr-kit` | `XDG_CACHE_HOME` |
| Shell integration | `~/.zshrc` | `ZDOTDIR` |
| Herdr binary, if missing | `~/.local/bin/herdr` | Existing compatible binary on `PATH` |

For custom locations, export the variables before installation and keep them set when running Herdr:

```sh
export XDG_DATA_HOME="$HOME/my data"
export XDG_CONFIG_HOME="$HOME/preferences"
./install.sh
```

Existing configuration is preserved unless you use `--replace-config`. Backups include a manifest of original file paths.

## Defaults and optional features

New configurations use zsh, the Catppuccin theme, terminal notifications, and Herdr's experimental Kitty graphics support. `prefix+up` opens Herdr Plus projects; `prefix+down` opens quick actions.

Run `herdr-themes-build` once to build the palette cache. New panes apply the colors automatically.

Optional sound and sprite packs are fetched through the Alerts plugin's helpers. Alerts use a bundled tone when the selected sound is unavailable. Doom indicators require their assets and Claude session data.

## Upgrading from Herdr Kit

The installer replaces the combined Herdr Kit with independently selectable plugins. After successful installation, it stops the old Doom overlays and disables the old plugin to avoid duplicate hooks. Existing `config.sh` settings are copied into each new hook plugin's configuration directory when it has no settings yet. The old files remain available, and the plugin registry is backed up.

Open a new zsh to load only the enabled plugins' helpers. Disabling Doomface stops its overlay within the polling interval; close any standalone Doom widget panes separately.
