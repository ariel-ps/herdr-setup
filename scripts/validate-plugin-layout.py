#!/usr/bin/env python3
"""Validate standalone Herdr plugin repositories against the shared layout."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import stat
import sys
import tomllib


REQUIRED_ROOT_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "herdr-plugin.toml",
}

OPTIONAL_ROOT_FILES = {
    ".editorconfig",
    ".npmrc",
    ".shellcheckrc",
    "Cargo.lock",
    "Cargo.toml",
    "CONTRIBUTING.md",
    "THIRD_PARTY_NOTICES.md",
    "bun.lock",
    "config.sh",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "shell.bash",
    "shell.zsh",
    "tsconfig.json",
    "uv.lock",
    "yarn.lock",
}

ALLOWED_ROOT_DIRECTORIES = {
    ".github",
    "actions",
    "assets",
    "bin",
    "data",
    "dist",
    "docs",
    "examples",
    "generated",
    "hooks",
    "libexec",
    "scripts",
    "skills",
    "src",
    "tests",
    "vendor",
}

IGNORED_ROOT_ENTRIES = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "target",
}

LOCAL_PATH_RE = re.compile(
    r"""(?:^|[\s"'=])(
        (?:\./|\.\./)
        [A-Za-z0-9_.@+/-]+
        |
        (?:actions|assets|bin|data|generated|hooks|libexec|scripts|skills|src|vendor)/
        [A-Za-z0-9_.@+/-]+
        |
        dist/
        [A-Za-z0-9_.@+/-]+
    )""",
    re.VERBOSE,
)

ABSOLUTE_PATH_TOKEN_RE = re.compile(
    r"""(?:^|[\s"'=;|&()<>:])(/[^\s"'`;|&()<>]*)"""
)

GENERATED_MARKERS = ("generated", "do not edit")
VENDOR_ORIGIN_FILES = ("ORIGIN.md", "ORIGIN.toml")
MAX_ROOT_LOADER_LINES = 120


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str

    def render(self, root: Path) -> str:
        try:
            relative = self.path.relative_to(root)
        except ValueError:
            relative = self.path
        shown = "." if str(relative) == "." else str(relative)
        return f"{shown}: {self.message}"


def manifest_commands(manifest: dict) -> tuple[list[list[str]], list[str]]:
    commands: list[list[str]] = []
    errors: list[str] = []
    for section in ("build", "events", "actions", "panes"):
        entries = manifest.get(section, [])
        if not isinstance(entries, list):
            errors.append(f"{section} must be an array of tables")
            continue
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                errors.append(f"{section}[{index}] must be a table")
                continue
            command = item.get("command")
            if command is None:
                continue
            if not isinstance(command, list) or not all(
                isinstance(part, str) for part in command
            ):
                errors.append(f"{section}[{index}].command must be an array of strings")
                continue
            if not command:
                errors.append(f"{section}[{index}].command must not be empty")
                continue
            commands.append(command)
    return commands, errors


def referenced_local_paths(command: list[str]) -> set[str]:
    paths: set[str] = set()
    for part in command:
        for match in LOCAL_PATH_RE.finditer(part):
            candidate = match.group(1).rstrip(";,)")
            paths.add(candidate)
    return paths


def is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def meaningful_line_count(path: Path) -> int:
    try:
        return sum(
            1
            for line in path.read_text(errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    except OSError:
        return MAX_ROOT_LOADER_LINES + 1


def validate_root(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for name in sorted(REQUIRED_ROOT_FILES):
        if not (root / name).is_file():
            findings.append(Finding(root / name, "required root file is missing"))

    try:
        entries = list(root.iterdir())
    except OSError as error:
        return [Finding(root, f"cannot read repository: {error}")]

    for entry in entries:
        name = entry.name
        if name in IGNORED_ROOT_ENTRIES:
            continue
        if entry.is_dir():
            if not any(path.is_file() for path in entry.rglob("*")):
                continue
            if name not in ALLOWED_ROOT_DIRECTORIES:
                findings.append(Finding(entry, "non-standard root directory"))
        elif name not in REQUIRED_ROOT_FILES | OPTIONAL_ROOT_FILES:
            findings.append(
                Finding(entry, "non-standard root file; move implementation below a named directory")
            )

    loaders = [root / name for name in ("shell.zsh", "shell.bash")]
    if any(path.exists() for path in loaders) and not all(
        path.is_file() for path in loaders
    ):
        findings.append(
            Finding(root, "shell integration must provide both shell.zsh and shell.bash")
        )
    for loader in loaders:
        if loader.is_file() and meaningful_line_count(loader) > MAX_ROOT_LOADER_LINES:
            findings.append(
                Finding(
                    loader,
                    f"root shell loader exceeds {MAX_ROOT_LOADER_LINES} meaningful lines; "
                    "move implementation to libexec",
                )
            )
    return findings


def load_manifest(root: Path) -> tuple[dict | None, list[Finding]]:
    path = root / "herdr-plugin.toml"
    if not path.is_file():
        return None, []
    try:
        return tomllib.loads(path.read_text()), []
    except (OSError, tomllib.TOMLDecodeError) as error:
        return None, [Finding(path, f"cannot parse manifest: {error}")]


def validate_manifest_paths(root: Path, manifest: dict) -> list[Finding]:
    findings: list[Finding] = []
    resolved_root = root.resolve()
    manifest_path = root / "herdr-plugin.toml"
    commands, errors = manifest_commands(manifest)
    findings.extend(Finding(manifest_path, error) for error in errors)
    for command in commands:
        for part in command:
            for match in ABSOLUTE_PATH_TOKEN_RE.finditer(part):
                if match.group(1).startswith("//"):
                    continue
                findings.append(
                    Finding(
                        manifest_path,
                        f"command contains an absolute host path: {match.group(1)}",
                    )
                )
        for reference in sorted(referenced_local_paths(command)):
            candidate = (root / reference).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError:
                findings.append(
                    Finding(root / "herdr-plugin.toml", f"path escapes plugin root: {reference}")
                )
                continue
            if not candidate.exists():
                findings.append(
                    Finding(
                        root / "herdr-plugin.toml",
                        f"command references missing local path: {reference}",
                    )
                )
        executable = command[0]
        local_prefixes = (
            "./",
            "../",
            "actions/",
            "bin/",
            "hooks/",
            "libexec/",
            "scripts/",
            "dist/",
        )
        if executable.startswith(local_prefixes):
            candidate = (root / executable).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError:
                continue
            if not candidate.is_file():
                findings.append(
                    Finding(
                        manifest_path,
                        f"direct local command is not a regular file: {executable}",
                    )
                )
            elif not is_executable(candidate):
                findings.append(
                    Finding(
                        manifest_path,
                        f"direct local command is not executable: {executable}",
                    )
                )
    return findings


def validate_bin(root: Path) -> list[Finding]:
    directory = root / "bin"
    if not directory.is_dir():
        return []
    findings: list[Finding] = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix not in {".ts", ".tsx"} and not is_executable(path):
            findings.append(Finding(path, "public command is not executable"))
    return findings


def validate_generated(root: Path) -> list[Finding]:
    directory = root / "generated"
    if not directory.is_dir():
        return []
    findings: list[Finding] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        try:
            prefix = "\n".join(path.read_text(errors="replace").splitlines()[:5]).lower()
        except OSError as error:
            findings.append(Finding(path, f"cannot inspect generated file: {error}"))
            continue
        if not all(marker in prefix for marker in GENERATED_MARKERS):
            findings.append(
                Finding(path, "generated file lacks a generated/do-not-edit marker")
            )
    return findings


def validate_vendor(root: Path) -> list[Finding]:
    directory = root / "vendor"
    if not directory.is_dir():
        return []
    findings: list[Finding] = []
    for component in directory.iterdir():
        if component.name.startswith("."):
            continue
        if not component.is_dir():
            findings.append(
                Finding(component, "vendored source must live in a component directory")
            )
            continue
        if not any((component / name).is_file() for name in VENDOR_ORIGIN_FILES):
            findings.append(
                Finding(component, "vendored component lacks ORIGIN.md or ORIGIN.toml")
            )
    return findings


def validate_tests(root: Path) -> list[Finding]:
    directory = root / "tests"
    if not directory.is_dir():
        return [Finding(directory, "every plugin requires contract tests")]
    candidates = [
        path
        for path in directory.rglob("*")
        if path.is_file()
        and (
            path.name.startswith("test_")
            or path.name.endswith("_test.py")
            or path.name.endswith(".test.ts")
            or path.name.endswith(".test.tsx")
            or path.suffix in {".sh", ".bats"}
        )
    ]
    if not candidates:
        return [Finding(directory, "no discoverable test files found")]
    return []


def validate_python_profile(root: Path) -> list[Finding]:
    source = root / "src"
    pyproject = root / "pyproject.toml"
    python_sources = list(source.rglob("*.py")) if source.is_dir() else []
    if not python_sources and not pyproject.exists():
        return []
    findings: list[Finding] = []
    if not source.is_dir():
        findings.append(Finding(source, "Python profile requires src/"))
    if not pyproject.is_file():
        findings.append(Finding(pyproject, "Python profile requires pyproject.toml"))
    if source.is_dir() and not any(
        path.is_dir() and path.name.startswith("herdr_") for path in source.iterdir()
    ):
        findings.append(Finding(source, "Python package must use a herdr_<slug> directory"))
    return findings


def validate_typescript_profile(root: Path) -> list[Finding]:
    package = root / "package.json"
    tsconfig = root / "tsconfig.json"
    source = root / "src"
    typescript_sources = (
        [*source.rglob("*.ts"), *source.rglob("*.tsx")]
        if source.is_dir()
        else []
    )
    if not typescript_sources and not package.exists() and not tsconfig.exists():
        return []

    findings: list[Finding] = []
    if not package.is_file():
        findings.append(Finding(package, "TypeScript profile requires package.json"))
    if not tsconfig.is_file():
        findings.append(Finding(tsconfig, "TypeScript profile requires tsconfig.json"))
    if not typescript_sources:
        findings.append(Finding(source, "TypeScript profile requires source files under src/"))

    lock_files = [
        root / name
        for name in ("bun.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock")
        if (root / name).is_file()
    ]
    if len(lock_files) != 1:
        findings.append(Finding(root, "TypeScript profile requires exactly one lock file"))

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        ignored = {
            line.strip().strip("/")
            for line in gitignore.read_text(errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if "node_modules" not in ignored:
            findings.append(Finding(gitignore, "TypeScript profile must ignore node_modules/"))
    for test_output in (root / "dist/test", root / "dist/tests"):
        if test_output.is_dir() and any(path.is_file() for path in test_output.rglob("*")):
            findings.append(Finding(test_output, "compiled test output does not belong in dist/"))
    return findings


def validate_rust_profile(root: Path) -> list[Finding]:
    manifest = root / "Cargo.toml"
    lock = root / "Cargo.lock"
    rust_sources = list((root / "src").rglob("*.rs")) if (root / "src").is_dir() else []
    if not rust_sources and not manifest.exists() and not lock.exists():
        return []

    findings: list[Finding] = []
    if not manifest.is_file():
        findings.append(Finding(manifest, "Rust profile requires Cargo.toml"))
    if not lock.is_file():
        findings.append(Finding(lock, "Rust profile requires Cargo.lock"))
    if not rust_sources:
        findings.append(Finding(root / "src", "Rust profile requires source files under src/"))

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        ignored = {
            line.strip().strip("/")
            for line in gitignore.read_text(errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if "target" not in ignored:
            findings.append(Finding(gitignore, "Rust profile must ignore target/"))
    return findings


def validate_repository(root: Path) -> list[Finding]:
    root = root.resolve()
    findings = validate_root(root)
    manifest, manifest_findings = load_manifest(root)
    findings.extend(manifest_findings)
    if manifest is not None:
        findings.extend(validate_manifest_paths(root, manifest))
    findings.extend(validate_bin(root))
    findings.extend(validate_generated(root))
    findings.extend(validate_vendor(root))
    findings.extend(validate_tests(root))
    findings.extend(validate_python_profile(root))
    findings.extend(validate_typescript_profile(root))
    findings.extend(validate_rust_profile(root))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Herdr plugin repository structure."
    )
    parser.add_argument("plugins", nargs="+", type=Path, help="plugin repository path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    failed = False
    for root in args.plugins:
        findings = validate_repository(root)
        if findings:
            failed = True
            print(f"{root}: FAIL")
            for finding in findings:
                print(f"  {finding.render(root.resolve())}")
        else:
            print(f"{root}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
