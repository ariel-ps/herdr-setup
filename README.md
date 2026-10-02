# Herdr Setup

Install Herdr, pane colors, status alerts, layout helpers, and a configurable selection of community plugins on macOS or Ubuntu/Debian Linux.

You do not need an existing Herdr installation or a particular project directory. The installer creates its directories, downloads Herdr when missing, and installs the bundled toolkit. Existing Herdr configuration is preserved by default.

**Private preview:** the repository is still private. Public release and licensing are not finalized. The toolkit has no private source-repository dependencies.

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

The installer handles system packages and toolchains. macOS requires Homebrew; Ubuntu/Debian requires package-installation privileges through root or sudo. Start Herdr using the command printed when installation finishes. New panes use zsh, where the toolkit's helpers are loaded.

## Choose your plugins

Edit **[`dependencies.json`](dependencies.json)** and rerun `./install.sh`. It is the single list of operating-system packages, tool installers, Herdr downloads, and optional plugins.

Set a plugin's `enabled` field to `false` to skip installing it, or disable an existing installation. Change `ref` to select a release tag or commit. See [dependency configuration](docs/dependencies.md).

The default selection includes Herdr Plus, Board, Grid, Sidebar, memex, Plugin Manager, and Terminal Code. The bundled toolkit adds:

- A distinct color for each pane.
- Flash and sound alerts when an agent is blocked or finishes.
- Layout save/load and agent grids.
- Agent names and session helpers.
- Optional Doom context-usage indicators for Claude panes.

Agent CLIs and their account logins are separate. Optional sound/sprite packs are downloaded by the toolkit's helpers; the default audio fallback is a generated tone.

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
dev/desktop/            Disposable Ubuntu + VNC test environment
docs/                   Configuration and development guides
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and the clean desktop test. Docker is for development/testing; customers install the tool directly on their machine.
