# ruff: noqa: S101
"""Tests for QtHelp path resolution and runtime sync."""

from pathlib import Path

import pytest
from oeapp.help import help_paths


def _bundle_dir(tmp_path: Path) -> Path:
    return tmp_path / "bundle" / "oeapp" / "help" / "assets"


def test_resolve_help_paths_uses_resource_and_app_data_locations(tmp_path, monkeypatch):
    """resolve_help_paths should compose expected bundled/runtime paths."""
    monkeypatch.setattr(
        help_paths,
        "get_resource_path",
        lambda relative: tmp_path / "bundle" / relative,
    )
    monkeypatch.setattr(help_paths, "get_app_data_path", lambda: tmp_path / "appdata")

    paths = help_paths.resolve_help_paths()

    assert paths.bundled_assets_dir == _bundle_dir(tmp_path)
    assert paths.bundled_qch_file == _bundle_dir(tmp_path) / "aenglisc_toolkit_help.qch"
    assert paths.bundled_qhc_file == _bundle_dir(tmp_path) / "aenglisc_toolkit_help.qhc"
    assert paths.runtime_help_dir == tmp_path / "appdata" / "help"
    assert (
        paths.runtime_qch_file
        == paths.runtime_help_dir / "aenglisc_toolkit_help.qch"
    )
    assert (
        paths.runtime_collection_file
        == paths.runtime_help_dir / "aenglisc_toolkit_help.qhc"
    )


def test_ensure_runtime_help_assets_raises_when_bundled_artifacts_missing(
    tmp_path, monkeypatch
):
    """ensure_runtime_help_assets should fail with clear error if files are missing."""
    monkeypatch.setattr(
        help_paths,
        "get_resource_path",
        lambda relative: tmp_path / "bundle" / relative,
    )
    monkeypatch.setattr(help_paths, "get_app_data_path", lambda: tmp_path / "appdata")

    with pytest.raises(FileNotFoundError):
        help_paths.ensure_runtime_help_assets()


def test_ensure_runtime_help_assets_copies_qch_and_qhc(
    tmp_path, monkeypatch
):
    """Runtime qch and qhc should sync from bundled assets."""
    bundled_assets_dir = _bundle_dir(tmp_path)
    bundled_assets_dir.mkdir(parents=True)
    bundled_qch = bundled_assets_dir / "aenglisc_toolkit_help.qch"
    bundled_qch.write_bytes(b"new-help-bytes")
    bundled_qhc = bundled_assets_dir / "aenglisc_toolkit_help.qhc"
    bundled_qhc.write_bytes(b"new-collection-bytes")

    runtime_help_dir = tmp_path / "appdata" / "help"
    runtime_help_dir.mkdir(parents=True)
    runtime_qch = runtime_help_dir / "aenglisc_toolkit_help.qch"
    runtime_qch.write_bytes(b"old-help-bytes")
    runtime_qhc = runtime_help_dir / "aenglisc_toolkit_help.qhc"
    runtime_qhc.write_bytes(b"stale-collection")

    monkeypatch.setattr(
        help_paths,
        "get_resource_path",
        lambda relative: tmp_path / "bundle" / relative,
    )
    monkeypatch.setattr(help_paths, "get_app_data_path", lambda: tmp_path / "appdata")

    paths = help_paths.ensure_runtime_help_assets()

    assert paths.runtime_qch_file.read_bytes() == b"new-help-bytes"
    assert runtime_qhc.read_bytes() == b"new-collection-bytes"

    runtime_qhc.write_bytes(b"new-collection-bytes")
    _ = help_paths.ensure_runtime_help_assets()
    assert runtime_qhc.exists()


def test_search_guide_markdown_exists():
    """Search guide markdown topic should exist in source topics."""
    topic_path = Path("oeapp/help/topics/search-guide.md")
    assert topic_path.exists()


def test_remembered_annotations_markdown_exists():
    """Remembered annotations help topic should exist in source topics."""
    topic_path = Path("oeapp/help/topics/remembered-annotations.md")
    assert topic_path.exists()
