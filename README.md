# Herdr Setup

Herdr Setup turns a fresh macOS or Ubuntu/Debian machine into a terminal workspace for running multiple coding agents with Herdr. It installs Herdr, a bundled enhancement toolkit, and a configurable selection of community plugins.

You do not need an existing Herdr installation or a particular project directory. The installer creates its directories, downloads Herdr when missing, and installs the bundled toolkit. Existing Herdr configuration is preserved by default.

**Private preview:** the repository is still private. Public release and licensing are not finalized. The toolkit has no private source-repository dependencies.

## What you get

Herdr manages the workspaces, tabs, panes, and agent sessions. This setup adds the configuration and helpers around them:

| Feature | What it does |
| --- | --- |
| Pane colors | Give panes distinct palettes so they are easier to tell apart. Build the palette cache with `herdr-themes-build`. |
| Status alerts | Flash a pane and play a sound when an agent is blocked or finishes. Optional media packs add named sounds and sprites. |
| Layout helpers | Save and restore pane arrangements with `herdr-layout-save` and `herdr-layout-load`; create agent grids with `herdr-grid-agents`. |
| Session helpers | Inspect agents, synchronize their names, and link panes to existing agent sessions. |
| Doom indicators | Show Claude context usage as a Doom face when the required assets and session data are available. |

The default selection enables seven community plugins: **Herdr Plus, Board, Grid, Sidebar, memex, Plugin Manager, and Terminal Code**. The bundled **Herdr Kit** is the eighth plugin. Their source repositories and pinned revisions are listed in [`dependencies.json`](dependencies.json).

For a new installation, the supplied configuration uses zsh, the Catppuccin theme, terminal notifications, and Herdr's experimental Kitty graphics support. It also binds `prefix+up` to Herdr Plus projects and `prefix+down` to quick actions. Existing configuration is kept unless you request replacement.

This setup does not install coding-agent CLIs or sign into their accounts. Install and authenticate the agents you want to run separately. Optional sound/sprite packs are fetched through the toolkit's helpers; alerts use a bundled tone when the selected sound is unavailable.

## Prerequisites

| Platform | Have ready before running the installer |
| --- | --- |
| macOS, Apple Silicon or Intel | Homebrew available as `brew` in your terminal, including its command-line build tools. |
| Ubuntu/Debian Linux, ARM64 or x86-64 | `apt-get` and permission to install packages through `sudo` or root. Other Linux package managers are not automated. |

On either platform, you need:

- Internet access for package repositories, Herdr, plugins, and their build dependencies.
- A writable home directory and a terminal application for running Herdr. The installer does not install a terminal emulator; the Linux desktop test uses Kitty.
- `curl`, `tar`, and a POSIX shell for the curl installation method. Minimal Linux images may need `curl` and CA certificates installed first.
- Access to this GitHub repository while the preview is private. The private download command below uses an authenticated GitHub CLI (`gh`).

**Installed automatically:** Herdr when missing, required packages, Python, uv, Rust/Cargo, Go, and the selected plugins. The exact platform dependency lists live in [`dependencies.json`](dependencies.json); you do not need to install those tools individually. If Herdr is already installed, it must be version 0.9.3 or newer; the installer keeps that binary and rejects older versions.

No existing Herdr configuration, project folder structure, or Docker installation is required. `--dry-run` and `--help` skip bootstrapping, so those modes require Python 3.11+ or uv already available.

## Install

From a downloaded or cloned copy, run:

```sh
./install.sh
```

After the repository becomes public, the same entry point supports:

```sh
curl -fsSL https://raw.githubusercontent.com/ariel-ps/herdr-setup/main/install.sh | sh
```

While private, fetch the script through your authenticated GitHub CLI:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' \
  repos/ariel-ps/herdr-setup/contents/install.sh | sh
```

Authentication is needed to download this private preview, not to install its public dependencies. A local copy can be installed without GitHub credentials.

When installation finishes, open a new zsh and start Herdr using the printed command. New panes use zsh, where the toolkit's helpers are loaded. Run `herdr-themes-build` once to generate the pane palettes; new panes then apply them automatically.

## Choose your plugins

Edit **[`dependencies.json`](dependencies.json)** and rerun `./install.sh`. It is the single list of operating-system packages, tool installers, Herdr downloads, and optional plugins.

Set a plugin's `enabled` field to `false` to skip installing it, or disable an existing installation. Change `ref` to select a release tag or commit. See [dependency configuration](docs/dependencies.md).

## Options

```sh
./install.sh --dry-run          # Show the plan without installing
./install.sh --no-shell         # Leave .zshrc untouched
./install.sh --replace-config   # Back up and replace existing defaults
```

For curl installation, pass options using `| sh -s -- --dry-run`. `HERDR_SETUP_REF` can select a branch, commit, or release tag; it defaults to `main` during the preview.

Paths are based on the current user's home and standard environment variables:

| Files | Default | Override |
| --- | --- | --- |
| Toolkit and backups | `~/.local/share/herdr-setup` | `XDG_DATA_HOME` |
| Herdr configuration | `~/.config/herdr` | `XDG_CONFIG_HOME` |
| Cached media | `~/.cache/herdr-kit` | `XDG_CACHE_HOME` |
| Shell integration | `~/.zshrc` | `ZDOTDIR` |
| Herdr binary, if missing | `~/.local/bin/herdr` | Existing compatible binary on `PATH` |

For example:

```sh
XDG_DATA_HOME="$HOME/my data" XDG_CONFIG_HOME="$HOME/preferences" ./install.sh
```

Keep custom XDG variables exported when running Herdr as well. No `Documents/projects` directory or original checkout is needed after installation; the toolkit is copied to its managed location. Backups include a manifest identifying the original file paths.

## Develop and test

```text
install.sh              Clone and curl installation entry point
dependencies.json       Editable dependency list
src/installer/          Installation implementation
src/herdr-kit/          Bundled enhancement source
config/                 Default settings
examples/               Generic layout examples
tests/                  Automated installer tests
tests/desktop/          Disposable Ubuntu + VNC test environment
docs/                   Configuration and development guides
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and the clean desktop test. Docker is for development/testing; customers install the tool directly on their machine.
