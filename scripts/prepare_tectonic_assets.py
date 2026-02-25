#!/usr/bin/env python3
"""Prepare bundled Tectonic assets for packaging."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_ROOT = PROJECT_ROOT / "assets" / "tectonic"
MANIFEST_NAME = "manifest.json"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--macos-arm64-binary", type=Path, default=None)
    parser.add_argument("--macos-x86_64-binary", type=Path, default=None)
    parser.add_argument("--windows-x86_64-binary", type=Path, default=None)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    """Return SHA-256 hash for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_binary(src: Path | None, dst: Path) -> bool:
    """Copy a single binary if provided."""
    if src is None:
        return False
    if not src.exists():
        msg = f"Binary does not exist: {src}"
        raise FileNotFoundError(msg)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.suffix != ".exe":
        dst.chmod(dst.stat().st_mode | 0o111)
    return True


def copy_bundle(bundle_src: Path, bundle_dst: Path) -> None:
    """Replace bundled TeX asset directory with provided source."""
    if not bundle_src.exists() or not bundle_src.is_dir():
        msg = f"Bundle directory does not exist: {bundle_src}"
        raise FileNotFoundError(msg)
    if bundle_dst.exists():
        shutil.rmtree(bundle_dst)
    shutil.copytree(bundle_src, bundle_dst)


def build_manifest(target_root: Path) -> dict[str, object]:
    """Build deterministic manifest data from target directory contents."""
    files: dict[str, str] = {}
    for path in sorted(target_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(target_root).as_posix()
        if relative.endswith(".gitkeep") or relative == MANIFEST_NAME:
            continue
        files[relative] = file_sha256(path)
    return {"version": 1, "files": files}


def main() -> None:
    """Prepare binaries/bundle and emit integrity manifest."""
    args = parse_args()
    target_root = args.target_root.resolve()
    binaries_root = target_root / "binaries"
    bundle_dst = target_root / "bundle" / "default"

    copied_any_binary = False
    copied_any_binary |= copy_binary(
        args.macos_arm64_binary, binaries_root / "macos" / "arm64" / "tectonic"
    )
    copied_any_binary |= copy_binary(
        args.macos_x86_64_binary, binaries_root / "macos" / "x86_64" / "tectonic"
    )
    copied_any_binary |= copy_binary(
        args.windows_x86_64_binary,
        binaries_root / "windows" / "x86_64" / "tectonic.exe",
    )

    if not copied_any_binary:
        msg = "At least one binary must be provided."
        raise ValueError(msg)

    copy_bundle(args.bundle_dir.resolve(), bundle_dst)
    manifest = build_manifest(target_root)
    manifest_path = target_root / MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote manifest: {manifest_path}")  # noqa: T201


if __name__ == "__main__":
    main()
