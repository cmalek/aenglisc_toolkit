"""Packaging smoke tests for bundled Tectonic integration."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    """Read file content as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def test_spec_includes_tectonic_assets() -> None:
    """PyInstaller spec should bundle Tectonic assets directory."""
    spec_path = PROJECT_ROOT / "aenglisc_toolkit.spec"
    content = read_text(spec_path)
    assert "assets/tectonic" in content


def test_spec_includes_alembic_runtime_assets() -> None:
    """PyInstaller spec should bundle Alembic config + migration scripts."""
    spec_path = PROJECT_ROOT / "aenglisc_toolkit.spec"
    content = read_text(spec_path)
    assert "oeapp/etc" in content
    assert "oeapp/models/alembic" in content


def test_macos_build_verifies_tectonic_assets() -> None:
    """macOS build script should verify bundled assets before packaging."""
    script_path = PROJECT_ROOT / "build_macos.sh"
    content = read_text(script_path)
    assert "python scripts/verify_tectonic_assets.py" in content
    assert "pyinstaller aenglisc_toolkit.spec" in content


def test_windows_build_verifies_tectonic_assets() -> None:
    """Windows build script should verify bundled assets before packaging."""
    script_path = PROJECT_ROOT / "build_windows.bat"
    content = read_text(script_path)
    assert "python scripts\\verify_tectonic_assets.py" in content
    assert "pyinstaller aenglisc_toolkit.spec" in content


def test_make_dmg_uses_single_applications_link_strategy() -> None:
    """`make dmg` should rely on create-dmg app-drop-link without precreating symlink."""
    makefile_path = PROJECT_ROOT / "Makefile"
    content = read_text(makefile_path)
    assert '--app-drop-link 600 185 "dist/Ænglisc Toolkit.dmg" "dist/dmg-root"' in content
    assert 'ln -sfn /Applications "dist/dmg-root/Applications"' not in content
