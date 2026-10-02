# Development

Run checks with Python 3.11+:

```sh
python3 -m unittest discover -s tests -v
./install.sh --dry-run
shellcheck install.sh tests/desktop/*.sh
```

Dependency changes belong in `dependencies.json`. Plugin changes belong in their individual repositories; update the corresponding `ref` after pushing a change. Keep runtime files independent of checkout locations and use HOME/XDG paths.

## Clean Linux desktop

With Docker and Docker Compose available:

```sh
./tests/desktop/run.sh start
./tests/desktop/run.sh install
```

Open http://localhost:6080/vnc.html?autoconnect=true&resize=scale for the desktop. The base image provides a desktop and graphical terminal, but no Herdr, plugins, Rust, Go, uv, or jq. The normal installer must supply its prerequisites.

For authenticated plugin downloads, pass a token only to the installation command:

```sh
GH_TOKEN="$(gh auth token)" ./tests/desktop/run.sh install
```

```sh
./tests/desktop/run.sh shell    # Inspect the test machine
./tests/desktop/run.sh reset    # Discard its files and start fresh
./tests/desktop/run.sh stop     # Remove the container
```

Set `HERDR_TEST_DOCKER_CONTEXT` to use a particular Docker context. The repository is mounted read-only; the host home and Docker socket are not mounted. The VNC endpoint is bound to localhost. Logs are written inside the container at `~/test-results/install.log`; save them before resetting.

noVNC does not forward audio to the browser. Test audio playback separately on a real desktop. Agent login and model calls are also separate from installation tests.

For a fresh Fedora installation test without a desktop:

```sh
GH_TOKEN="$(gh auth token)" docker run --rm -it -e GH_TOKEN \
  -v "$PWD:/opt/herdr-setup:ro" fedora:44 sh /opt/herdr-setup/install.sh
```

The Fedora image starts without Herdr or the plugin toolchains; the installer supplies them through dnf and the dependency manifest. Fedora 44 ARM64 has been tested with all 13 plugins, a repeat installation, standalone plugin checks, audio dependencies, and Unix-socket communication. The VNC environment above uses Ubuntu.

The installer has been exercised on Ubuntu 24.04 ARM64, including installation without pre-existing Herdr, custom XDG/ZDOTDIR locations containing spaces, a second installation, and a live Herdr launch. The plugin split was tested with authenticated GitHub downloads, settings migration, and independent enable/disable behavior. macOS download selection and fresh-home behavior have automated coverage; a fresh macOS machine installation has not been run. Individual plugins may show their own first-run preferences, such as the sidebar's optional Nerd Font prompt.
