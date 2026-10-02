# Ariel's Herdr setup

Private, reproducible configuration for Herdr, its plugins, and the dev-env shell helpers used alongside it.

**Work in progress:** the configuration and source snapshots are captured. The installer is being validated; a clean Linux desktop with browser-accessible VNC is being added for end-to-end installation testing. Use the read-only preview below until that testing is complete.

```sh
git clone https://github.com/ariel-ps/herdr-setup.git
cd herdr-setup
./install.sh --dry-run
```

GitHub access to both `ariel-ps/dev-env` and `prompt-security/herdr-kit` is required. Authenticate Git before installing, for example with `gh auth login` and `gh auth setup-git`.

## Organization

```text
ariel-ps/herdr-setup          Installation, configuration, dependency snapshots
ariel-ps/dev-env             General shell helper development
prompt-security/herdr-kit   Herdr enhancement development
```

This repository assembles the other two. `plugins.lock.json` records reachable base commits and source tree hashes. The patches preserve the local source changes present at capture time, including unpublished Doom face and layout/session helpers, without changing either working repository.

```text
config/                     Theme, sidebar, shortcuts, alert preferences
shell/setup.zsh             Shell integration
scripts/install.py          Installer
patches/                    Captured source changes against pinned commits
plugins.lock.json           Source and external plugin versions
Brewfile                    macOS prerequisites
```

## Captured plugins

| Plugin | Version |
| --- | --- |
| Herdr Plus | 0.1.24 |
| herdr-kit | 0.1.0 plus local source changes |
| Herdr Board | 0.18.0 |
| herdr-grid | 0.6.0 |
| herdr-sidebar | 0.15.0 |
| memex | 0.19.7 |
| Plugin Manager | 0.4.0 |
| Terminal Code | 0.1.1 |

Captured with Herdr 0.9.3. Plugin source commits are pinned; upstream build scripts may still download moving toolchains or external assets.

## Installer behavior under development

- Installs source snapshots into separate, verified checkouts under `~/.local/share/herdr-setup/sources`.
- Supports `--profile full` (default) and `--profile essentials` (agent and terminal helpers).
- Backs up configuration before replacement, with a restoration manifest under `~/.local/share/herdr-setup/backups`.
- Adds one managed block to `.zshrc`; `--no-shell` leaves that file alone.
- Stops when existing manual source lines or modified managed checkouts would conflict.

When migrating an existing `.zshrc`, replace the old `source .../dev-env/init.zsh` and `source .../herdr-kit/shell/herdr.sh` lines and the old standalone `__herdr_apply_pane_theme` call with the managed setup source. Keep unrelated shell settings. Alternatively use `--no-shell` and perform that integration manually.

The snapshot includes tracked dev-env changes and new source files under `scripts/`. It excludes its untracked agent configuration directories, skills lock file, and archive. Credentials, personal `.zshrc`, session databases, transcripts, running panes, and downloaded media are not part of this repository. Media is fetched separately by the kit's helpers.

## Linux testing

The existing kit assumes macOS for sound playback and some terminal operations. Linux compatibility and a disposable Docker/noVNC desktop are being implemented and have **not yet passed end-to-end testing**.
