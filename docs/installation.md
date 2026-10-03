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
./install.sh --shell bash       # Choose bash explicitly (or --shell zsh)
./install.sh --no-shell         # Leave shell startup files untouched
./install.sh --replace-config   # Back up and replace existing defaults
```

`--dry-run` and `--help` skip bootstrapping and require Python 3.11+ or uv already available.

Installation shows four stages: dependencies, Herdr, plugins, and configuration.
Plugin progress and the final next steps appear alongside package-manager and
build output. Status colors are enabled only in an interactive terminal; set
`NO_COLOR=1` to disable them. Redirected output remains plain text.

The installer detects your login shell from `SHELL` (or your account settings). Bash and zsh are supported. Bash setup loads helpers from `.bashrc` and the first existing login file (`.bash_profile`, `.bash_login`, or `.profile`); if none exists, it creates `.bash_profile`. Zsh remains a runtime dependency for plugin scripts and is installed automatically on Linux. You do not need to switch your shell.

For curl installation, pass options using `| sh -s -- --dry-run`. Set `HERDR_SETUP_REF` on the shell running the installer to select a branch, commit, or release tag; the default is `main`.

## Files and backups

| Files | Default | Override |
| --- | --- | --- |
| Shell loader and backups | `~/.local/share/herdr-setup` | `XDG_DATA_HOME` |
| Herdr configuration | `~/.config/herdr` | `XDG_CONFIG_HOME` |
| Installed plugins | `~/.config/herdr/plugins` | `XDG_CONFIG_HOME` |
| Cached media | `~/.cache/herdr-kit` | `XDG_CACHE_HOME` |
| Bash integration | `~/.bashrc` and the active login file | `HOME` |
| Zsh integration | `~/.zshrc` | `ZDOTDIR` |
| Herdr binary, if missing | `~/.local/bin/herdr` | Existing compatible binary on `PATH` |
| Lazygit settings | Directory reported by `lazygit --print-config-dir` | `XDG_CONFIG_HOME`; existing `LG_CONFIG_FILE` is respected |

For custom locations, export the variables before installation and keep them set when running Herdr:

```sh
export XDG_DATA_HOME="$HOME/my data"
export XDG_CONFIG_HOME="$HOME/preferences"
./install.sh
```

Existing configuration is preserved unless you use `--replace-config`. Setup adds the Lazygit popup to an existing Herdr configuration only when neither shortcut is occupied. Backups include a manifest of original file paths. `--replace-config` replaces Herdr, plugin, and Lazygit defaults; a custom `LG_CONFIG_FILE` remains untouched.

## Git and folder navigation

The defaults follow Datalumina's [Lazygit](https://learn.datalumina.com/docs/herdr/lazygit) and [folder navigation](https://learn.datalumina.com/docs/herdr/folders) guides, adapted for Bash and Zsh on macOS and Linux.

- **Cmd+Shift+G** or **prefix+d** opens Lazygit in the focused pane's directory. Press **q** to close it. Linux users can use prefix+d; the default prefix is Ctrl+B.
- Lazygit uses a compact file view, agent branch colors, and delta's TwoDark syntax highlighting. Press `|` to switch to word-level diffs. Its config is installed only when missing.
- After visiting a directory with `cd`, use `z name` to return or `zi` to search visited directories with fzf.
- Interactive shells initialize zoxide and fzf, including older distro fzf versions. eza supplies `ls`, `ll`, and `tree`; bat supplies `cat`. Existing aliases, functions, `BAT_THEME`, and fzf settings take precedence.

The shell loader contains these helpers, so removing the downloaded installer does not break them. `--no-shell` still generates the loader but leaves startup files unchanged. Open a new shell to load updated helpers. Icons require a Nerd Font in your terminal; terminal and font installation remain your choice.

## Control panel

Herdr Plus supplies a mouse-driven overlay with search, descriptions, and keyboard navigation. Open it with **prefix+Down** (Ctrl+B then Down by default), or run `herdr plugin action invoke cloudmanic.herdr-plus.quick-actions`. Herdr 0.9.3 does not display plugin actions in its sidebar or right-click menus. Click or press Enter to select; Esc goes back or closes the panel.

Setup adds five menus: Tools (Git, Neovim, Board, and Grid), Sound and visual alerts, Plugin actions, Installed plugins, and Quick guide. Plugin actions reads the live plugin registry each time and includes only enabled actions for your operating system. Installed plugins opens the existing Plugin Manager for plugin state and management.

The defaults live in `quick-actions/herdr-setup-*.toml` under the directory reported by `herdr plugin config-dir cloudmanic.herdr-plus`. Edit them there; rerunning Setup preserves edits unless `--replace-config` is selected. Other Quick Actions files remain untouched. Disabling Herdr Plus in `dependencies.json` skips these defaults. Bootstrap installs **Neovim** (`neovim` / Homebrew `neovim`) for the Tools → Code quick action; sound settings control the split Herdr Alerts plugin.

## Defaults and optional features

New configurations use your selected shell, the Catppuccin theme, terminal notifications, and Herdr's experimental Kitty graphics support. Existing Herdr settings are preserved, including its pane shell; change `terminal.default_shell` in your Herdr configuration if you want existing installations to use bash. `prefix+up` opens Herdr Plus projects; `prefix+down` opens quick actions.

The palette cache is prepared during installation. New panes apply the colors automatically; run `herdr-themes-build` to rebuild it later.

Optional sound and sprite packs are fetched through the Alerts plugin's helpers. Alerts use a bundled tone when the selected sound is unavailable. Doom indicators require their assets and Claude session data.

## Upgrading from Herdr Kit

The installer replaces the combined Herdr Kit with independently selectable plugins. After successful installation, it stops the old Doom overlays and disables the old plugin to avoid duplicate hooks. Existing `config.sh` settings are copied into each new hook plugin's configuration directory when it has no settings yet. The old files remain available, and the plugin registry is backed up.

Open a new terminal to load the enabled plugins' helpers. Disabling Doomface stops its overlay within the polling interval; close any standalone Doom widget panes separately.
