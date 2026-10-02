# Development

Run checks with Python 3.11+:

```sh
python3 -m unittest discover -s tests -v
./install.sh --dry-run
shellcheck install.sh tests/desktop/*.sh
zsh -n src/herdr-kit/setup.zsh
```

Dependency changes belong in `dependencies.json`. Toolkit changes belong in `src/herdr-kit`. Keep runtime files independent of the repository's checkout location and use HOME/XDG paths rather than a contributor's directory layout.

## Clean Linux desktop

With Docker and Docker Compose available:

```sh
./tests/desktop/run.sh start
./tests/desktop/run.sh install
```

Open http://localhost:6080/vnc.html?autoconnect=true&resize=scale for the desktop. The base image provides a desktop and graphical terminal, but no Herdr, plugins, Rust, Go, uv, or jq. The normal installer must supply its prerequisites. No GitHub credential is provided to the container.

```sh
./tests/desktop/run.sh shell    # Inspect the test machine
./tests/desktop/run.sh reset    # Discard its files and start fresh
./tests/desktop/run.sh stop     # Remove the container
```

Set `HERDR_TEST_DOCKER_CONTEXT` to use a particular Docker context. The repository is mounted read-only; the host home and Docker socket are not mounted. The VNC endpoint is bound to localhost. Logs are written inside the container at `~/test-results/install.log`; save them before resetting.

noVNC does not forward audio to the browser. Test audio playback separately on a real desktop. Agent login and model calls are also separate from installation tests.

The installer has been exercised on Ubuntu 24.04 ARM64 without Herdr or GitHub credentials, including custom XDG/ZDOTDIR locations containing spaces, a second installation, and a live Herdr launch. macOS download selection and fresh-home behavior have automated coverage; a fresh macOS machine installation has not been run. Individual plugins may show their own first-run preferences, such as the sidebar's optional Nerd Font prompt.
