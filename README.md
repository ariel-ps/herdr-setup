# Herdr Setup

**Install Herdr with plugins to manage several coding agents side by side in your terminal.**

Give each pane its own color, get an alert when an agent needs attention, and save layouts to use again. Works on macOS, Ubuntu/Debian, and Fedora.

You don't need Herdr installed already. Works with bash or zsh; existing settings are preserved.

## What it adds

- **[Pane colors](https://github.com/ariel-ps/herdr-colors)** — tell your agents apart at a glance.
- **[Sound and flash alerts](https://github.com/ariel-ps/herdr-alerts)** — notice when an agent finishes or needs help.
- **[Saved layouts and grids](https://github.com/ariel-ps/herdr-layouts)** — arrange your panes and reuse the layout.
- **[Session helpers](https://github.com/ariel-ps/herdr-sessions)** — inspect agents and synchronize their names.
- **[Doom face indicators](https://github.com/ariel-ps/herdr-doomface)** — visualize Claude's context usage.

Each feature is a separate plugin. Also includes Herdr Plus, Board, Grid, Sidebar, memex, Plugin Manager, Terminal Code, and a [sidebar menu toggle](https://github.com/ariel-ps/herdr-sidebar-menu).

## Prerequisites

- **macOS:** Homebrew and its command-line build tools.
- **Ubuntu/Debian:** `apt-get` and `sudo` or root access.
- **Fedora:** `dnf` and `sudo` or root access.
- A terminal, internet access, and `curl`/`tar` for the command below.

Apple Silicon/ARM64 and Intel/x86-64 are supported. Herdr and build dependencies are installed automatically. Install and sign into your coding-agent CLIs separately.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/ariel-ps/herdr-setup/main/install.sh | sh
```

From a downloaded or cloned copy, run `./install.sh`.

<details>
<summary>If GitHub requires authentication</summary>

Sign in with `gh auth login`, then run:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' \
  repos/ariel-ps/herdr-setup/contents/install.sh | sh
```

</details>

For plugin downloads that require authentication, sign in with `gh auth login` or set `GH_TOKEN` before installing.

Open a new terminal, run `herdr-themes-build` once to create the pane colors, then launch `herdr`.

Manage sounds with `herdr-sound`: `play` tests the included tone, `list` shows available sounds, and `sync mario` downloads a pack. Then run `herdr-sound play 1up` or `herdr-sound set done 1up`. Use `off`/`on` to mute or enable automatic alerts, and `status` to check settings.

## Customize

Edit [`dependencies.json`](dependencies.json) and rerun the installer. Set any plugin's `enabled` field to `false` to disable it, or change `ref` to update its version. Open a new terminal after changing enabled plugins.

[Installation options and paths](docs/installation.md) · [Dependency reference](docs/dependencies.md) · [Development and Docker/VNC testing](CONTRIBUTING.md)

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party code and media retain their own terms; this license does not grant rights to game assets, downloaded themes, or other third-party content.
