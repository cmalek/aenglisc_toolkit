"""Unit tests for bundled PDF engine helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from oeapp.services.pdf_engine import (
    PDFEngineError,
    TectonicEnginePaths,
    compile_latex_with_tectonic,
    resolve_tectonic_engine_paths,
)


def test_compile_uses_bundle_and_offline_flags(monkeypatch, tmp_path):
    """Compile command should include bundle and only-cached when bundle exists."""
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        captured.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("oeapp.services.pdf_engine.subprocess.run", fake_run)
    monkeypatch.setattr(
        "oeapp.services.pdf_engine.resolve_tectonic_engine_paths",
        lambda: TectonicEnginePaths(
            binary_path=Path("/tmp/tectonic"),
            bundle_path=Path("/tmp/bundle"),
        ),
    )

    tex_path = tmp_path / "in.tex"
    tex_path.write_text("x", encoding="utf-8")
    compile_latex_with_tectonic(tex_path, tmp_path)

    assert captured
    cmd = captured[0]
    assert "--bundle" in cmd
    assert "/tmp/bundle" in cmd
    assert "--only-cached" in cmd


def test_compile_omits_bundle_flags_when_bundle_missing(monkeypatch, tmp_path):
    """Compile command should omit offline bundle flags when bundle is None."""
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        captured.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("oeapp.services.pdf_engine.subprocess.run", fake_run)
    monkeypatch.setattr(
        "oeapp.services.pdf_engine.resolve_tectonic_engine_paths",
        lambda: TectonicEnginePaths(
            binary_path=Path("/tmp/tectonic"),
            bundle_path=None,
        ),
    )

    tex_path = tmp_path / "in.tex"
    tex_path.write_text("x", encoding="utf-8")
    compile_latex_with_tectonic(tex_path, tmp_path)

    assert captured
    cmd = captured[0]
    assert "--bundle" not in cmd
    assert "--only-cached" not in cmd


def test_resolve_ignores_placeholder_bundle_in_development(monkeypatch, tmp_path):
    """Resolver should ignore placeholder bundle dirs lacking SHA256SUM."""
    binary_path = tmp_path / "assets" / "tectonic" / "binaries" / "macos" / "arm64" / "tectonic"
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    binary_path.write_text("binary", encoding="utf-8")

    bundle_path = tmp_path / "assets" / "tectonic" / "bundle" / "default"
    bundle_path.mkdir(parents=True, exist_ok=True)
    (bundle_path / ".gitkeep").write_text("", encoding="utf-8")

    monkeypatch.setattr("oeapp.services.pdf_engine._normalize_platform", lambda: ("macos", "arm64"))
    monkeypatch.setattr("oeapp.services.pdf_engine.get_resource_path", lambda _: tmp_path / "assets" / "tectonic")
    monkeypatch.setattr("oeapp.services.pdf_engine.shutil.which", lambda _: None)
    monkeypatch.setattr("oeapp.services.pdf_engine.sys.frozen", False, raising=False)

    paths = resolve_tectonic_engine_paths()
    assert paths.binary_path == binary_path
    assert paths.bundle_path is None


def test_resolve_rejects_invalid_env_bundle(monkeypatch, tmp_path):
    """Explicit env bundle path must include SHA256SUM metadata index."""
    binary_path = tmp_path / "tectonic"
    binary_path.write_text("binary", encoding="utf-8")
    bundle_path = tmp_path / "bundle"
    bundle_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AENGLISC_TOOLKIT_TECTONIC_BINARY", str(binary_path))
    monkeypatch.setenv("AENGLISC_TOOLKIT_TECTONIC_BUNDLE", str(bundle_path))

    with pytest.raises(PDFEngineError, match="missing SHA256SUM"):
        resolve_tectonic_engine_paths()
