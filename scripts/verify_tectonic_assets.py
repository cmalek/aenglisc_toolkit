#!/usr/bin/env python3
"""Verify bundled Tectonic assets required for packaging."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

#: Path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
#: Default path to the target directory
DEFAULT_TARGET_ROOT = PROJECT_ROOT / "assets" / "tectonic"
#: Name of the manifest file
MANIFEST_NAME = "manifest.json"


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.

    Returns:
        argparse.Namespace: The parsed arguments.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    """
    Return SHA-256 hash for a file.

    Args:
        path: The path to the file.

    Returns:
        The SHA-256 hash of the file.

    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_required_layout(target_root: Path, errors: list[str]) -> None:
    """
    Verify minimum cross-platform payload requirements.

    Side Effects:
        Adds errors to the list of error messages.

    Args:
        target_root: The path to the target directory.
        errors: A list of error messages.

    """
    windows_bin = target_root / "binaries" / "windows" / "x86_64" / "tectonic.exe"
    mac_arm = target_root / "binaries" / "macos" / "arm64" / "tectonic"
    mac_x86 = target_root / "binaries" / "macos" / "x86_64" / "tectonic"
    bundle_dir = target_root / "bundle" / "default"

    if not windows_bin.exists():
        errors.append(f"Missing Windows binary: {windows_bin}")
    if not mac_arm.exists() and not mac_x86.exists():
        errors.append("Missing macOS binary: expected arm64 and/or x86_64 payload")
    if not bundle_dir.exists():
        errors.append(f"Missing bundle directory: {bundle_dir}")
    else:
        bundle_files = [
            path
            for path in bundle_dir.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        if not bundle_files:
            errors.append(f"Bundle directory is empty: {bundle_dir}")


def verify_manifest(target_root: Path, errors: list[str]) -> None:
    """
    Verify that manifest entries exist and match expected hashes.

    Side Effects:
        Adds errors to the list of error messages.

    Args:
        target_root: The path to the target directory.
        errors: A list of error messages.

    """
    manifest_path = target_root / MANIFEST_NAME
    if not manifest_path.exists():
        errors.append(f"Missing manifest: {manifest_path}")
        return

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid manifest JSON: {exc}")
        return

    files = payload.get("files")
    if not isinstance(files, dict):
        errors.append("Manifest has invalid 'files' map.")
        return
    if not files:
        errors.append("Manifest has no tracked files.")
        return

    for relative, expected_hash in sorted(files.items()):
        file_path = target_root / relative
        if not file_path.exists():
            errors.append(f"Missing file from manifest: {file_path}")
            continue
        observed_hash = file_sha256(file_path)
        if observed_hash != expected_hash:
            errors.append(f"Hash mismatch for {file_path}")


def main() -> None:
    """Entry point."""
    args = parse_args()
    target_root = args.target_root.resolve()
    errors: list[str] = []

    verify_required_layout(target_root, errors)
    verify_manifest(target_root, errors)

    if errors:
        print("Tectonic asset verification failed:")  # noqa: T201
        for err in errors:
            print(f" - {err}")  # noqa: T201
        sys.exit(1)

    print("Tectonic asset verification passed.")  # noqa: T201


if __name__ == "__main__":
    main()
