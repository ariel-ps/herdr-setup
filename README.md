# Herdr Setup

A ready-to-use [Herdr](https://github.com/herdrdev/herdr) environment for running coding agents side by side. Distinguish panes by color, hear when an agent needs attention, and restore saved layouts.

**macOS · Ubuntu/Debian · Fedora · Bash and Zsh**

## What you get

| Feature | Component |
| --- | --- |
| Searchable, clickable control panel for tools, plugins, alerts, and help | Herdr Plus Quick Actions |
| A distinct color palette for each pane | [Colors](https://github.com/ariel-ps/herdr-colors) |
| Sound and flash alerts when agents finish or need input | [Alerts](https://github.com/ariel-ps/herdr-alerts) |
| Saved pane layouts, agent grids, and automatic `code` and `board` tabs | [Layouts](https://github.com/ariel-ps/herdr-layouts) |
| Agent launch shortcuts, inspection, and session naming | [Sessions](https://github.com/ariel-ps/herdr-sessions) |
| A Doom face that reflects Claude's context usage | [Doomface](https://github.com/ariel-ps/herdr-doomface) |
| Git-root investigation scratch notes in `.journal/` | [Journal Repo](https://github.com/ariel-ps/repo-journal) (`journal-repo` CLI, installed via setup) |
| Git popup with highlighted diffs and colored agent branches | Lazygit + delta |
| Jump to projects with `z` and pick a folder with `zi` | zoxide + fzf |

Also includes Herdr Plus, Board, Grid, memex, Plugin Manager, and Terminal Code. Sidebar and its menu toggle are disabled by default. Each plugin can be enabled independently in [`dependencies.json`](dependencies.json).

## Install

You do not need Herdr installed or an existing project directory. Setup installs Herdr when missing, prepares dependencies, and connects the plugins to your shell.

### Prerequisites

| Platform | Required before installation |
| --- | --- |
| macOS | Homebrew and command-line build tools |
| Ubuntu / Debian | `apt-get` and root or `sudo` access |
| Fedora | `dnf` and root or `sudo` access |

Use an ARM64 or x86-64 machine with a terminal, internet access, `curl`, and `tar`. Install and sign into coding-agent CLIs separately. An existing Herdr installation must be version **0.9.3 or newer**.

```sh
curl -fsSL https://raw.githubusercontent.com/ariel-ps/herdr-setup/main/install.sh | sh
```

Setup preserves existing settings, adds the Git popup when its shortcuts are free, and backs up files it changes. Bash and Zsh are supported; you do not need to switch shells.

<details>
<summary>Install from a clone or use GitHub authentication</summary>

From a cloned or downloaded copy, run `./install.sh`.

If GitHub requires authentication, sign in with `gh auth login` or provide `GH_TOKEN`. To download the installer with your GitHub login:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' \
  repos/ariel-ps/herdr-setup/contents/install.sh | sh
```

</details>

## First use

Open a **new terminal** after installation, then launch:

```sh
herdr
```

New panes receive their colors automatically. If Herdr is already running, reload its configuration through the menu.

Press **prefix+Down** (by default, Ctrl+B then Down) to open the control panel. Click a row or type to search: **Tools**, **Sound and visual alerts**, **Plugin actions**, **Installed plugins**, or **Quick guide**. New enabled plugins appear automatically in Plugin actions.

Or run `herdr plugin action invoke cloudmanic.herdr-plus.quick-actions`. Herdr 0.9.3 does not display plugin actions in its sidebar or right-click menus.

In a repository, press **Cmd+Shift+G** or **prefix+d** to open Lazygit; press **q** to close it. The default prefix is Ctrl+B. You can also run `lazygit` directly.

Visit a project once with `cd`, then use `z project` to return or `zi` to choose from visited folders. Interactive shells also get `ls`, `ll`, and `tree` through eza, and `cat` through bat; existing aliases are preserved.

Launch an installed coding agent with `claude-danger`, `codex-danger`,
`cursor-danger`, or `deepcode-danger`. These shortcuts bypass agent permission
prompts and forward your arguments. Install and sign into the agent CLI first;
[shortcut details](https://github.com/ariel-ps/herdr-sessions#agent-shortcuts).

Preview the bundled tone, flash, and sprite without downloading a pack:

```sh
herdr-alert play
```

| Sound command | What it does |
| --- | --- |
| `herdr-alert status` | Show alert settings and playback dependencies |
| `herdr-alert list` | List sound choices |
| `herdr-alert download mario` | Download the optional Mario pack |
| `herdr-alert set done 1up` | Use the downloaded `1up` sound for completed agents |
| `herdr-alert disable` | Mute automatic sound alerts |
| `herdr-alert enable` | Enable automatic sound alerts |

[Full sound guide](https://github.com/ariel-ps/herdr-alerts#commands)

## Customize

Edit [`dependencies.json`](dependencies.json) in your local copy, then rerun `./install.sh`:

- Set a plugin's `enabled` field to `false` to disable it.
- Change its `ref` to select a different revision.
- Run `./install.sh --dry-run` to preview your selection before installing.

Open a new terminal after changing enabled plugins. Preview mode requires Python 3.11+ or uv already installed.

[Installation options and paths](docs/installation.md) · [Dependency reference](docs/dependencies.md) · [Development and Docker/VNC testing](CONTRIBUTING.md)

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party code, themes, and game media retain their own terms.
