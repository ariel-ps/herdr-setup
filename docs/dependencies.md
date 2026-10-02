# One dependency list

Edit [`dependencies.json`](../dependencies.json), then rerun:

```sh
./install.sh
```

There is no separate Brewfile or hand-maintained package list in the installer.

| Field | What it controls |
| --- | --- |
| `packages.macos` | Homebrew formulae |
| `packages.linux` | Ubuntu/Debian packages |
| `tools` | Tools installed by their official scripts when missing, including Rust and uv |
| `herdr.version` | Herdr release for a new installation |
| `herdr.downloads` | SHA256 checksums by operating system and architecture |
| `sources` | dev-env and herdr-kit source snapshots, with local patches |
| `plugins` | External Herdr plugins and the Git revisions to install |

## Add or update a plugin

Each plugin entry looks like this:

```json
{
  "id": "cloudmanic.herdr-plus",
  "name": "Herdr Plus",
  "version": "0.1.24",
  "repository": "cloudmanic/herdr-plus",
  "subdir": "",
  "ref": "v0.1.24"
}
```

`ref` is the installation source of truth: use a release tag, branch, or full commit SHA. A tag is resolved to its commit before installation. `version` is descriptive only; change `ref` to actually update a plugin. The initial snapshot uses exact commit hashes.

Add an entry to install a new plugin. Removing an entry stops managing that plugin; it does not uninstall an existing copy. Modified plugin checkouts cause installation to stop so local work is preserved.

## Add a prerequisite

Append the appropriate package name to `packages.macos` and/or `packages.linux`. Rerun the installer. Package-manager packages use the available repository version; this manifest pins Herdr and plugin source revisions, not every transitive operating-system package.

## Source snapshots

The source entries include a published base commit, a patch of local changes, a patch checksum, and the resulting Git tree hash. Those hashes verify the captured snapshot. Updating a base commit while retaining the patch requires regenerating and checking the patch/tree metadata; ordinary package and plugin edits do not.

## Scope

The prerequisites cover Herdr, the kit, and plugin builds. `--profile full` also loads personal dev-env integrations for other tools (cloud CLIs, corporate services, VMs); those tools and credentials are configured separately. The default `essentials` profile loads the agent and terminal helpers.

Python is the small bootstrap prerequisite used to read JSON. When absent, the launcher installs it through the platform package manager. Linux automatic dependency installation supports Ubuntu/Debian; other distributions need a package-manager adapter.
