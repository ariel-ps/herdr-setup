# Plugin repository structure

First-party Herdr plugins use one profile-based repository format. The format
keeps host-facing contracts easy to find while separating public commands,
private runtime code, build tooling, generated data, and third-party material.

Directories are capability-based and optional. Do not add empty directories or
placeholder files merely to match the tree.

## Canonical tree

```text
herdr-<slug>/
├── herdr-plugin.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── SECURITY.md
├── .gitignore
├── shell.zsh
├── shell.bash
├── config.sh
├── pyproject.toml
├── package.json / bun.lock / tsconfig.json
├── Cargo.toml / Cargo.lock
├── bin/
├── hooks/
├── actions/
├── libexec/
├── src/
│   └── herdr_<slug>/
├── scripts/
│   ├── build/
│   ├── dev/
│   └── release/
├── data/
├── generated/
├── dist/
├── assets/
├── vendor/
├── skills/
├── docs/
├── examples/
└── tests/
```

Every plugin requires `herdr-plugin.toml`, `README.md`, `LICENSE`,
`CHANGELOG.md`, `SECURITY.md`, and `.gitignore`. The remaining entries appear
only when that plugin needs them.

## Profiles

Profiles are additive rather than exclusive language silos.

### Minimal

A manifest-only plugin contains no local runtime implementation. Its manifest
may delegate to Herdr or another declared plugin. It still has repository
metadata and at least one manifest contract test.

Example: Sidebar Menu.

### Shell

Shell plugins may expose root `shell.zsh` and `shell.bash` loaders. These files
are public integration contracts consumed by Herdr Setup, so they stay at the
repository root and should remain thin. Put stable user-facing commands in
`bin/`, event adapters in `hooks/`, action-only adapters in `actions/`, and
private helpers in `libexec/`.

Examples: Colors, Layouts, Sessions, and Journal.

### Python or hybrid

Plugins whose runtime implementation is Python use an importable
`src/herdr_<slug>/` package and a `pyproject.toml`. Files in `bin/`, `hooks/`,
`actions/`, and `libexec/` are thin entrypoints. Commit a lock file when the
runtime has third-party Python dependencies.

Example: Doomface. A plugin may retain shell adapters where Herdr's event or
action interface makes shell the simplest boundary. Plugins with private Python
helpers but no importable Python runtime may keep those helpers in `libexec/`
without creating packaging metadata.

### TypeScript or hybrid

TypeScript plugins keep `package.json`, one lock file, and `tsconfig.json` at
the root. Source lives in `src/`, tests live in `tests/`, and committed compiler
output lives in `dist/` when installation must work without a Node toolchain.
`node_modules/` is always ignored. Root shell loaders and bundled skills remain
valid additive capabilities.

Example: Journal.

### Rust or hybrid

Rust plugins keep `Cargo.toml` and `Cargo.lock` at the root, implementation in
`src/`, and ignore `target/`. A manifest build adapter may place the release
binary in the plugin's ignored `bin/` path, while tracked compatibility
launchers remain the stable commands referenced by actions and documentation.

Examples: Alerts and Colors.

### Optional capabilities

- `assets/` contains immutable files intentionally redistributed with the
  plugin.
- `data/` contains hand-authored catalogs, schemas, and mappings.
- `generated/` contains deterministic committed output.
- `dist/` is reserved for compiled Node/TypeScript distribution output.
- `vendor/` contains third-party source with origin and license records.
- `skills/` contains bundled agent skills in their discovery layout.

Downloaded themes, optional media, rendered frames, PIDs, saved layouts, and
user-generated state belong under XDG config or cache paths, not in these
repository directories.

## Directory contracts

### Repository root

The root contains only:

- Herdr and packaging contracts: `herdr-plugin.toml`, optional shell loaders,
  optional `config.sh`, and optional Python packaging files.
- Repository metadata: README, license, changelog, security policy, ignore
  rules, and optional contribution or third-party notices.
- Standard directories from the canonical tree.

Feature hooks and action scripts do not live at root.

`config.sh` is a safe declarative template. It must not contain secrets, inspect
host state, or perform work when sourced.

### `bin/`

`bin/` contains stable executable commands intended for users or `PATH`.
Commands are extensionless and named `herdr-<noun>[-<verb>]`. Moving a command
out of `bin/` is a compatibility change.

### `hooks/`

Hooks are fast Herdr event adapters. Name them
`on-<event-name>-<purpose>.zsh`, replacing event dots with hyphens. A hook
validates event input, loads configuration, delegates substantive work, and
returns promptly.

### `actions/`

`actions/` contains scripts used only by manifest actions. An action should call
a public `bin/` command directly when no adapter is necessary.

### `libexec/`

`libexec/` contains private runtime executables and subprocess helpers. Its
contents are not added to `PATH` and carry no public command compatibility
promise.

### `src/`

`src/herdr_<slug>/` contains importable Python implementation. Executable
launchers remain thin and do not duplicate package logic.

### `scripts/`

- `scripts/build/` is used by manifest build steps and deterministic
  generation.
- `scripts/dev/` is maintainer-only tooling and is never called at normal
  runtime.
- `scripts/release/` contains release automation.

Runtime fetchers and workers belong in `libexec/`, not `scripts/`.

### `data/`, `generated/`, and `assets/`

`data/` is hand-authored source of truth. `generated/` is reproducible output
and every generated file starts with a generator marker. CI regenerates it and
requires a clean diff. `assets/` is distributable media with documented origin
and license.

`dist/` is also generated, but compilers are not required to insert per-file
headers. CI rebuilds it and requires a clean diff. Source maps and test output
do not belong in the committed distribution.

### `vendor/`

Each vendored component has an adjacent `ORIGIN.md` or `ORIGIN.toml` recording:

- Upstream name and URL.
- Exact revision or release.
- License and license-file location.
- Local modifications.

### `skills/`

Bundled skills retain their discovery shape:
`skills/<skill-name>/SKILL.md`. A plugin may combine the skill capability with
any runtime profile.

### `tests/`

Tests are discoverable by the project's standard runner. Split into `unit/`,
`contract/`, `integration/`, and `fixtures/` only when the volume warrants it.
Every plugin has at least a manifest contract test. Tests cover installation
from a relocated path containing spaces.

## Path and naming rules

Manifest paths are explicit and relative to the plugin root:

```toml
command = ["zsh", "./hooks/on-pane-agent-status-changed-alert.zsh"]
command = ["zsh", "./actions/open-widget.zsh"]
command = ["./bin/herdr-sound", "list"]
command = ["sh", "./scripts/build/sync-themes.sh"]
```

Avoid substantial `sh -c` or `zsh -c` expressions in manifests. Use a named
adapter when an operation needs branching, environment setup, or more than one
command.

Every entrypoint derives the plugin root from `HERDR_PLUGIN_ROOT` or its own
resolved location. Internal paths are absolute paths derived from that root,
never from the caller's working directory.

Naming conventions:

- Repository: `herdr-<kebab-slug>`.
- Python package: `herdr_<snake_slug>`.
- Public command: `herdr-<noun>[-<verb>]`.
- Manifest IDs: stable kebab-case.
- Internal shell symbols: `__herdr_<plugin>_...`.
- Imported Python modules have `.py`; executable launchers are extensionless.

## Compatibility rules

A structural migration must not change:

- Plugin IDs, action IDs, event subscriptions, or public command names.
- Existing user configuration and XDG cache paths.
- Shell loader and config template paths consumed by Herdr Setup.
- Exit-status behavior except where correcting a documented defect.

Move a file and update its manifest references, root resolution, tests, and
documentation in the same repository change.

Run `python3 scripts/validate-plugin-layout.py <plugin>...` from Herdr Setup to
check repositories against this standard.
