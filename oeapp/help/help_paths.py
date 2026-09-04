"""Resolve and synchronize QtHelp runtime paths."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from oeapp.utils import get_app_data_path, get_resource_path

#: Help assets relative dir.
HELP_ASSETS_RELATIVE_DIR: Final[str] = "oeapp/help/assets"
#: Help package dirname.
HELP_PACKAGE_DIRNAME: Final[str] = "help"
#: Help qch filename.
HELP_QCH_FILENAME: Final[str] = "aenglisc_toolkit_help.qch"
#: Help qhc filename.
HELP_QHC_FILENAME: Final[str] = "aenglisc_toolkit_help.qhc"


@dataclass(frozen=True, slots=True)
class HelpPaths:
    """Bundled and runtime file locations for QtHelp assets."""

    #: Bundled assets dir.
    bundled_assets_dir: Path
    #: Bundled qch file.
    bundled_qch_file: Path
    #: Bundled qhc file.
    bundled_qhc_file: Path
    #: Runtime help dir.
    runtime_help_dir: Path
    #: Runtime qch file.
    runtime_qch_file: Path
    #: Runtime collection file.
    runtime_collection_file: Path


def resolve_help_paths() -> HelpPaths:
    """
    Return canonical bundled/runtime locations for help assets.

    Returns:
        The computed value.

    """
    bundled_assets_dir = get_resource_path(HELP_ASSETS_RELATIVE_DIR)
    bundled_qch_file = bundled_assets_dir / HELP_QCH_FILENAME
    bundled_qhc_file = bundled_assets_dir / HELP_QHC_FILENAME

    runtime_help_dir = get_app_data_path() / HELP_PACKAGE_DIRNAME
    runtime_qch_file = runtime_help_dir / HELP_QCH_FILENAME
    runtime_collection_file = runtime_help_dir / HELP_QHC_FILENAME

    return HelpPaths(
        bundled_assets_dir=bundled_assets_dir,
        bundled_qch_file=bundled_qch_file,
        bundled_qhc_file=bundled_qhc_file,
        runtime_help_dir=runtime_help_dir,
        runtime_qch_file=runtime_qch_file,
        runtime_collection_file=runtime_collection_file,
    )


def ensure_runtime_help_assets() -> HelpPaths:
    """
    Ensure runtime QtHelp assets exist in writable storage.

    Returns:
        Resolved help paths for the current runtime.

    Raises:
        FileNotFoundError: If bundled help artifacts are missing.

    """
    paths = resolve_help_paths()
    if not paths.bundled_qch_file.exists() or not paths.bundled_qhc_file.exists():
        msg = (
            "QtHelp artifacts are missing. Run "
            "`source .venv/bin/activate && python scripts/build_help.py`."
        )
        raise FileNotFoundError(msg)

    paths.runtime_help_dir.mkdir(parents=True, exist_ok=True)
    _sync_file(paths.bundled_qch_file, paths.runtime_qch_file)
    _sync_file(paths.bundled_qhc_file, paths.runtime_collection_file)

    return paths


def _sync_file(source: Path, destination: Path) -> bool:
    """
    Copy a file if content differs.

    Args:
        source: Source.
        destination: Destination.

    Returns:
        The computed value.

    """
    if destination.exists() and _sha256(source) == _sha256(destination):
        return False
    shutil.copy2(source, destination)
    return True


def _sha256(path: Path) -> str:
    """
    Return SHA-256 hash for a file.

    Args:
        path: Path.

    Returns:
        The computed value.

    """
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
