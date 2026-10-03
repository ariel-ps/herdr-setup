import importlib.util
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "plugin_structure", ROOT / "scripts/validate-plugin-layout.py"
)
plugin_structure = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin_structure
spec.loader.exec_module(plugin_structure)


class PluginStructureTests(unittest.TestCase):
    def make_plugin(self, root: Path):
        files = {
            ".gitignore": "\n",
            "CHANGELOG.md": "# Changelog\n",
            "LICENSE": "test\n",
            "README.md": "# Test\n",
            "SECURITY.md": "# Security\n",
            "herdr-plugin.toml": textwrap.dedent(
                """\
                id = "dev.example.test"
                name = "Test"
                version = "0.1.0"
                min_herdr_version = "0.9.3"
                description = "Test plugin."
                platforms = ["macos", "linux"]
                """
            ),
            "tests/test_manifest.py": "def test_placeholder():\n    assert True\n",
        }
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def messages(self, root: Path):
        return [finding.message for finding in plugin_structure.validate_repository(root)]

    def test_minimal_plugin_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            self.assertEqual(plugin_structure.validate_repository(root), [])

    def test_required_root_files_and_unknown_root_scripts_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / "SECURITY.md").unlink()
            (root / "event-hook.sh").write_text("#!/bin/sh\n")
            messages = self.messages(root)
            self.assertIn("required root file is missing", messages)
            self.assertTrue(any("non-standard root file" in message for message in messages))

    def test_manifest_paths_must_exist_and_remain_inside_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / "herdr-plugin.toml").write_text(
                (root / "herdr-plugin.toml").read_text()
                + textwrap.dedent(
                    """\

                    [[actions]]
                    id = "missing"
                    title = "Missing"
                    command = ["sh", "./actions/missing.sh"]

                    [[events]]
                    on = "pane.agent_status_changed"
                    command = ["sh", "../outside.sh"]

                    [[panes]]
                    id = "missing-dist"
                    title = "Missing dist"
                    command = ["node", "dist/missing.js"]
                    """
                )
            )
            messages = self.messages(root)
            self.assertGreaterEqual(
                sum("missing local path" in message for message in messages), 2
            )
            self.assertTrue(any("escapes plugin root" in message for message in messages))

    def test_malformed_manifest_command_sections_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / "herdr-plugin.toml").write_text(
                (root / "herdr-plugin.toml").read_text()
                + '\nactions = "not-an-array"\n'
            )
            messages = self.messages(root)
            self.assertTrue(any("actions must be an array" in message for message in messages))

            manifest = (root / "herdr-plugin.toml").read_text().replace(
                'actions = "not-an-array"', 'actions = [{id="empty", title="Empty", command=[]}]'
            )
            (root / "herdr-plugin.toml").write_text(manifest)
            self.assertTrue(
                any("command must not be empty" in message for message in self.messages(root))
            )

    def test_bin_commands_must_be_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            command = root / "bin/herdr-test"
            command.parent.mkdir()
            command.write_text("#!/bin/sh\n")
            self.assertIn("public command is not executable", self.messages(root))
            command.chmod(0o755)
            self.assertNotIn("public command is not executable", self.messages(root))

    def test_direct_manifest_commands_must_be_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            command = root / "libexec/worker"
            command.parent.mkdir()
            command.write_text("#!/bin/sh\n")
            (root / "herdr-plugin.toml").write_text(
                (root / "herdr-plugin.toml").read_text()
                + '\n[[actions]]\nid="run"\ntitle="Run"\ncommand=["./libexec/worker"]\n'
            )
            self.assertTrue(
                any("direct local command is not executable" in message for message in self.messages(root))
            )
            command.chmod(0o755)
            self.assertFalse(
                any("direct local command is not executable" in message for message in self.messages(root))
            )

            manifest = (root / "herdr-plugin.toml").read_text()
            (root / "herdr-plugin.toml").write_text(
                manifest.replace('"./libexec/worker"', '"./libexec"')
            )
            self.assertTrue(
                any("not a regular file" in message for message in self.messages(root))
            )

            command.chmod(0o644)
            (root / "herdr-plugin.toml").write_text(
                manifest.replace('"./libexec/worker"', '"libexec/worker"')
            )
            self.assertTrue(
                any("direct local command is not executable" in message for message in self.messages(root))
            )

            (root / "herdr-plugin.toml").write_text(
                manifest.replace('"./libexec/worker"', '"/tmp/worker"')
            )
            self.assertTrue(
                any("absolute host path" in message for message in self.messages(root))
            )

            (root / "herdr-plugin.toml").write_text(
                manifest.replace(
                    '"./libexec/worker"',
                    '"sh", "-c", "exec /tmp/host-tool"',
                )
            )
            self.assertTrue(
                any("absolute host path: /tmp/host-tool" in message for message in self.messages(root))
            )
            for shell_command, absolute_path in [
                ("cat </tmp/host-config", "/tmp/host-config"),
                ("printf x >/tmp/host-output", "/tmp/host-output"),
                ("PATH=$PATH:/tmp/bin exec tool", "/tmp/bin"),
            ]:
                with self.subTest(shell_command=shell_command):
                    (root / "herdr-plugin.toml").write_text(
                        manifest.replace(
                            '"./libexec/worker"',
                            f'"sh", "-c", "{shell_command}"',
                        )
                    )
                    self.assertTrue(
                        any(
                            f"absolute host path: {absolute_path}" in message
                            for message in self.messages(root)
                        )
                    )

    def test_git_worktree_marker_file_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / ".git").write_text("gitdir: /tmp/example\n")
            self.assertEqual(plugin_structure.validate_repository(root), [])

    def test_shell_loaders_are_paired_and_thin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / "shell.zsh").write_text("true\n")
            self.assertTrue(any("both shell.zsh and shell.bash" in message for message in self.messages(root)))
            (root / "shell.bash").write_text("true\n")
            (root / "shell.zsh").write_text("true\n" * 121)
            self.assertTrue(any("root shell loader exceeds" in message for message in self.messages(root)))

    def test_generated_files_require_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            generated = root / "generated/table.zsh"
            generated.parent.mkdir()
            generated.write_text("# ordinary file\n")
            self.assertTrue(any("generated file lacks" in message for message in self.messages(root)))
            generated.write_text("# GENERATED; do not edit.\n")
            self.assertFalse(any("generated file lacks" in message for message in self.messages(root)))

    def test_vendor_components_require_origin_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            component = root / "vendor/example"
            component.mkdir(parents=True)
            (component / "source.py").write_text("pass\n")
            self.assertTrue(any("lacks ORIGIN" in message for message in self.messages(root)))
            (component / "ORIGIN.md").write_text("# Origin\n")
            self.assertFalse(any("lacks ORIGIN" in message for message in self.messages(root)))

    def test_python_profile_requires_pyproject_and_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            (root / "src").mkdir()
            (root / "src/plugin.py").write_text("pass\n")
            messages = self.messages(root)
            self.assertIn("Python profile requires pyproject.toml", messages)
            self.assertTrue(any("herdr_<slug>" in message for message in messages))
            (root / "pyproject.toml").write_text("[project]\nname='herdr-test'\nversion='0.1.0'\n")
            (root / "src/herdr_test").mkdir()
            self.assertNotIn("Python profile requires pyproject.toml", self.messages(root))

    def test_typescript_profile_requires_packaging_lock_and_ignored_modules(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            source = root / "src/view.tsx"
            source.parent.mkdir()
            source.write_text("export const value = 1;\n")
            messages = self.messages(root)
            self.assertIn("TypeScript profile requires package.json", messages)
            self.assertIn("TypeScript profile requires tsconfig.json", messages)
            self.assertIn("TypeScript profile requires exactly one lock file", messages)

            (root / "package.json").write_text('{"name":"herdr-test","version":"0.1.0"}\n')
            (root / "tsconfig.json").write_text('{"compilerOptions":{"outDir":"dist"}}\n')
            (root / "bun.lock").write_text("\n")
            (root / ".gitignore").write_text("/node_modules/\n")
            self.assertFalse(
                any("TypeScript profile" in message for message in self.messages(root))
            )
            output = root / "dist/tests/plugin.test.js"
            output.parent.mkdir(parents=True)
            output.write_text("throw new Error('not distributable');\n")
            self.assertTrue(
                any("compiled test output" in message for message in self.messages(root))
            )

    def test_rust_profile_requires_manifest_lock_and_ignored_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_plugin(root)
            source = root / "src/main.rs"
            source.parent.mkdir()
            source.write_text("fn main() {}\n")
            messages = self.messages(root)
            self.assertIn("Rust profile requires Cargo.toml", messages)
            self.assertIn("Rust profile requires Cargo.lock", messages)

            (root / "Cargo.toml").write_text(
                '[package]\nname="herdr-test"\nversion="0.1.0"\n'
            )
            (root / "Cargo.lock").write_text("\n")
            (root / ".gitignore").write_text("target/\n")
            self.assertFalse(any("Rust profile" in message for message in self.messages(root)))


if __name__ == "__main__":
    unittest.main()
