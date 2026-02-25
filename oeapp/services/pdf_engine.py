"""Bundled PDF engine resolution and LaTeX compilation helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from oeapp.utils import get_resource_path


class PDFEngineError(RuntimeError):
    """Raised when the bundled PDF engine cannot be located or executed."""


@dataclass(frozen=True)
class TectonicEnginePaths:
    """Resolved paths for a bundled Tectonic engine installation."""

    binary_path: Path
    bundle_path: Path | None


def _bundle_has_required_index(bundle_path: Path) -> bool:
    """Return whether a local Tectonic bundle directory looks valid."""
    return (bundle_path / "SHA256SUM").exists()


def _normalize_platform() -> tuple[str, str]:
    """Return normalized ``(platform, arch)`` values for asset lookup."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    platform_name = {
        "darwin": "macos",
        "windows": "windows",
        "linux": "linux",
    }.get(system)
    if not platform_name:
        msg = f"Unsupported platform: {system}"
        raise PDFEngineError(msg)

    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine)
    if not arch:
        msg = f"Unsupported architecture: {machine}"
        raise PDFEngineError(msg)

    return platform_name, arch


def resolve_tectonic_engine_paths() -> TectonicEnginePaths:
    """Resolve bundled Tectonic binary and offline bundle paths."""
    env_binary = os.environ.get("OE_ANNOTATOR_TECTONIC_BINARY")
    env_bundle = os.environ.get("OE_ANNOTATOR_TECTONIC_BUNDLE")
    if env_binary:
        binary = Path(env_binary)
        if not binary.exists():
            msg = f"OE_ANNOTATOR_TECTONIC_BINARY not found: {binary}"
            raise PDFEngineError(msg)
        bundle = None
        if env_bundle:
            bundle = Path(env_bundle)
            if not bundle.exists():
                msg = f"OE_ANNOTATOR_TECTONIC_BUNDLE not found: {bundle}"
                raise PDFEngineError(msg)
            if not _bundle_has_required_index(bundle):
                msg = (
                    "OE_ANNOTATOR_TECTONIC_BUNDLE is invalid: missing SHA256SUM. "
                    f"Bundle path: {bundle}"
                )
                raise PDFEngineError(msg)
        return TectonicEnginePaths(binary_path=binary, bundle_path=bundle)

    platform_name, arch = _normalize_platform()
    base = get_resource_path("assets/tectonic")

    binary_name = "tectonic.exe" if platform_name == "windows" else "tectonic"
    binary_path = base / "binaries" / platform_name / arch / binary_name
    bundle_path = base / "bundle" / "default"

    if not binary_path.exists():
        # Development fallback: allow a PATH-installed tectonic binary when the
        # bundled runtime is not present.
        fallback = shutil.which("tectonic")
        if fallback:
            binary_path = Path(fallback)
        else:
            msg = (
                "Bundled Tectonic binary is missing. Expected: "
                f"{binary_path}. Rebuild with prepared Tectonic assets or install "
                "tectonic on PATH for development."
            )
            raise PDFEngineError(msg)

    # For development, allow compilation with default bundle behavior if a
    # bundled offline bundle is not available. Production builds should include
    # assets/tectonic/bundle/default.
    if not bundle_path.exists():
        bundle_path = None
    elif not _bundle_has_required_index(bundle_path):
        # During source development, allow fallback to default Tectonic bundle
        # behavior when only placeholder bundle assets are present.
        if getattr(sys, "frozen", False):
            msg = (
                "Bundled Tectonic bundle is invalid: missing SHA256SUM. "
                f"Expected bundle at: {bundle_path}. Rebuild with prepared assets."
            )
            raise PDFEngineError(msg)
        bundle_path = None

    return TectonicEnginePaths(binary_path=binary_path, bundle_path=bundle_path)


def compile_latex_with_tectonic(
    tex_path: Path, output_dir: Path
) -> subprocess.CompletedProcess[str]:
    """
    Compile a LaTeX file to PDF using bundled Tectonic.

    This uses offline mode by pointing Tectonic to the bundled package set and
    enforcing ``--only-cached``.
    """
    engine = resolve_tectonic_engine_paths()
    cmd = [
        str(engine.binary_path),
        "-X",
        "compile",
        str(tex_path),
        "--outdir",
        str(output_dir),
        "--keep-logs",
        "--keep-intermediates",
    ]
    if engine.bundle_path is not None:
        cmd.extend(["--bundle", str(engine.bundle_path), "--only-cached"])
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
