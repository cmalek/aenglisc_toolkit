#!/usr/bin/env python3
"""Build Apple Help Book assets from rendered help HTML pages."""

from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
from pathlib import Path

from oeapp.help.topics import DEFAULT_HTML_PAGE

#: Project root path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
#: Source directory containing rendered HTML help pages.
HTML_SOURCE_DIR = PROJECT_ROOT / "oeapp" / "help" / "assets"
#: Output root for generated macOS Help Book assets.
HELPBOOK_OUTPUT_ROOT = PROJECT_ROOT / "oeapp" / "help" / "macos"
#: Help Book folder name copied into the app bundle resources.
HELPBOOK_FOLDER_NAME = "AengliscToolkit.help"
#: Final generated Help Book path.
HELPBOOK_DIR = HELPBOOK_OUTPUT_ROOT / HELPBOOK_FOLDER_NAME
#: Path to Help Book ``Contents`` directory.
HELPBOOK_CONTENTS_DIR = HELPBOOK_DIR / "Contents"
#: Path to localized resource directory containing HTML files.
HELPBOOK_LOCALE_DIR = HELPBOOK_CONTENTS_DIR / "Resources" / "en.lproj"
#: Path to generated Apple Help search index.
HELPBOOK_INDEX_PATH = HELPBOOK_LOCALE_DIR / "search.helpindex"
#: Help Book bundle identifier.
HELPBOOK_BUNDLE_ID = "org.placodermi.aenglisc-toolkit.help"
#: Visible Apple Help Book title.
HELPBOOK_TITLE = "Ænglisc Toolkit Help"


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed namespace with runtime options.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip hiutil indexing even when the tool is available.",
    )
    return parser.parse_args()


def main() -> None:
    """
    Build the macOS Help Book folder and optional ``hiutil`` search index.

    Returns:
        None

    """
    args = parse_args()
    _validate_source_html()
    _prepare_output_directory()
    _copy_html_pages()
    _write_helpbook_info_plist()
    _build_help_index(skip_index=args.skip_index)
    print(f"macOS Help Book ready at: {HELPBOOK_DIR}")  # noqa: T201


def _validate_source_html() -> None:
    """
    Ensure generated help HTML exists before creating Help Book assets.

    Returns:
        None

    Raises:
        FileNotFoundError: If no rendered help HTML pages are present.

    """
    html_pages = list(HTML_SOURCE_DIR.glob("*.html"))
    if html_pages:
        return
    msg = (
        f"No rendered help HTML found under {HTML_SOURCE_DIR}. "
        "Run `python scripts/build_help.py` first."
    )
    raise FileNotFoundError(msg)


def _prepare_output_directory() -> None:
    """
    Recreate the Help Book output directory.

    Returns:
        None

    """
    if HELPBOOK_DIR.exists():
        shutil.rmtree(HELPBOOK_DIR)
    HELPBOOK_LOCALE_DIR.mkdir(parents=True, exist_ok=True)


def _copy_html_pages() -> None:
    """
    Copy rendered HTML pages into the Help Book locale directory.

    Returns:
        None

    """
    for html_path in HTML_SOURCE_DIR.glob("*.html"):
        shutil.copy2(html_path, HELPBOOK_LOCALE_DIR / html_path.name)


def _write_helpbook_info_plist() -> None:
    """
    Write Help Book metadata plist consumed by Help Viewer.

    Returns:
        None

    """
    info_plist = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleIdentifier": HELPBOOK_BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundlePackageType": "BNDL",
        "CFBundleShortVersionString": "1.0",
        "CFBundleSignature": "hbwr",
        "CFBundleVersion": "1.0",
        "HPDBookAccessPath": f"en.lproj/{DEFAULT_HTML_PAGE}",
        "HPDBookIndexPath": "en.lproj/search.helpindex",
        "HPDBookTitle": HELPBOOK_TITLE,
        "HPDBookType": "3",
    }
    output_path = HELPBOOK_CONTENTS_DIR / "Info.plist"
    with output_path.open("wb") as plist_file:
        plistlib.dump(info_plist, plist_file)


def _build_help_index(*, skip_index: bool) -> None:
    """
    Build ``search.helpindex`` using ``hiutil`` when available.

    Args:
        skip_index: Whether indexing is explicitly disabled.

    Returns:
        None

    """
    if skip_index:
        return

    hiutil_path = shutil.which("hiutil")
    if hiutil_path is None:
        print("Warning: hiutil not found; skipping Apple Help index build.")  # noqa: T201
        return

    subprocess.run(
        [
            hiutil_path,
            "-Caf",
            str(HELPBOOK_INDEX_PATH),
            str(HELPBOOK_LOCALE_DIR),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
