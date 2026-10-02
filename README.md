# Ariel's Herdr setup

Private, reproducible configuration for Herdr, its plugins, and the dev-env shell helpers used alongside it.

**Validation in progress:** the installer supports macOS and Ubuntu/Debian Linux. A clean Ubuntu desktop with browser-accessible VNC is included, and the first complete Linux installation test is running. Use the read-only preview to inspect the plan.

```sh
git clone https://github.com/ariel-ps/herdr-setup.git
cd herdr-setup
./install.sh --dry-run
# Install dependencies, plugins, configuration, and shell integration:
./install.sh
```

GitHub access to both `ariel-ps/dev-env` and `prompt-security/herdr-kit` is required. Authenticate Git before installing, for example with `gh auth login` and `gh auth setup-git`.

## Organization

```text
ariel-ps/herdr-setup          Installation, configuration, dependency snapshots
ariel-ps/dev-env             General shell helper development
prompt-security/herdr-kit   Herdr enhancement development
```

This repository assembles the other two. **[`dependencies.json`](dependencies.json) is the single dependency list**: macOS packages, Linux packages, tool installers, Herdr versions/checksums, source snapshots, and external plugins. Edit that file and rerun `./install.sh`. See [dependency editing examples](docs/dependencies.md).

The source patches preserve the local changes present at capture time, including unpublished Doom face and layout/session helpers, without changing either working repository. The kit snapshot also includes Linux audio and terminal compatibility changes.

```text
config/                     Theme, sidebar, shortcuts, alert preferences
shell/setup.zsh             Shell integration
scripts/install.py          Installer
patches/                    Captured source changes against pinned commits
dependencies.json           All application dependencies and plugin revisions
layouts/                    Portable pane arrangements
docker/ + compose.yaml      Clean Ubuntu desktop with noVNC
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
- Defaults to `--profile essentials` (agent and terminal helpers); `--profile full` loads all personal dev-env profiles.
- Backs up configuration before replacement, with a restoration manifest under `~/.local/share/herdr-setup/backups`.
- Adds one managed block to `.zshrc`; `--no-shell` leaves that file alone.
- Stops when existing manual source lines or modified managed checkouts would conflict.

When migrating an existing `.zshrc`, replace the old `source .../dev-env/init.zsh` and `source .../herdr-kit/shell/herdr.sh` lines and the old standalone `__herdr_apply_pane_theme` call with the managed setup source. Keep unrelated shell settings. Alternatively use `--no-shell` and perform that integration manually.

The snapshot includes tracked dev-env changes and new source files under `scripts/`. It excludes its untracked agent configuration directories, skills lock file, and archive. Credentials, personal `.zshrc`, session databases, transcripts, running panes, and downloaded media are not part of this repository. Media is fetched separately by the kit's helpers.

## Clean Linux installation test

With Docker and Docker Compose running:

```sh
./scripts/test-desktop.sh start
./scripts/test-desktop.sh auth
./scripts/test-desktop.sh install
```

Open **http://localhost:6080/vnc.html?autoconnect=true&resize=scale** for the desktop. The image contains a graphical terminal and VNC infrastructure, but no Herdr, plugins, Rust, Go, uv, or jq. The normal installer installs the missing dependencies during the test.

`auth` streams your GitHub CLI credential into a temporary in-memory file in the container, needed for the private source repositories. It is not part of the image, Compose configuration, or Git repository. Your host home directory and Docker socket are not mounted. The setup repository is mounted read-only. The desktop port is bound to localhost only.

```sh
./scripts/test-desktop.sh shell    # Inspect the installed Linux environment
./scripts/test-desktop.sh reset    # Discard it and get a clean desktop
./scripts/test-desktop.sh stop     # Remove the test container
```

To use a specific Docker context, prefix commands with `HERDR_TEST_DOCKER_CONTEXT=<context>`. Installation logs live in the container at `~/test-results/install.log`; copy them out before resetting. noVNC displays the desktop but does not forward sound to your browser. Audio backend checks and listening to alerts on a real desktop are separate checks.

The Linux installation test is still in progress; a working VNC page alone does not establish that every plugin works.
