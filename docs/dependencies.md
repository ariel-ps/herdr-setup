# Dependencies

Edit [`dependencies.json`](../dependencies.json), then run `./install.sh`.

| Field | Purpose |
| --- | --- |
| `packages.macos` | Homebrew formulae |
| `packages.linux` | Ubuntu/Debian packages |
| `tools` | Official installation scripts for tools missing from PATH |
| `herdr.version` | Herdr release to install when it is missing |
| `herdr.downloads` | SHA256 verification by OS and architecture |
| `plugins` | Optional community plugins |

A plugin entry:

```json
{
  "id": "cloudmanic.herdr-plus",
  "name": "Herdr Plus",
  "repository": "cloudmanic/herdr-plus",
  "subdir": "",
  "ref": "v0.1.24",
  "enabled": true
}
```

`ref` may be a release tag, branch, or full commit hash. Tags and branches are resolved to a commit before installation. To update a plugin, change `ref` and rerun the installer. Add an entry to install another plugin. Set `enabled` to `false` to disable it; deleting an entry simply stops managing it and does not uninstall anything.

To add a system prerequisite, append its name to the appropriate `packages` list. Package managers use available repository versions; plugin build scripts may download additional upstream assets.

The bundled toolkit lives in `src/herdr-kit` and is maintained directly.

The tiny bootstrap step installs Python if it is missing so the installer can read JSON. Herdr is downloaded for the detected OS/architecture and its checksum is verified before installation. A pre-existing Herdr installation is kept and checked for compatibility; upgrading an incompatible existing version remains the user's package-manager operation.
