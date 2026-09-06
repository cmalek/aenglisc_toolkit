"""Unit tests for database setup."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from oeapp.db import (
    Base,
    SessionLocal,
    create_engine_with_path,
    get_project_db_path,
    run_pragma_optimize,
    table_to_model_name,
)


class TestBase:
    """Test cases for Base declarative base."""

    def test_base_has_metadata(self):
        """Test Base has metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_has_registry(self):
        """Test Base has registry for models."""
        assert hasattr(Base, "registry")


class TestGetProjectDbPath:
    """Test cases for get_project_db_path()."""

    def test_returns_path_on_darwin(self, monkeypatch):
        """Test returns correct path on macOS."""
        monkeypatch.delenv("AENGLISC_TOOLKIT_DB_PATH", raising=False)
        monkeypatch.delenv("AENGLISC_TOOLKIT_DATA_PATH", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert "Library" in str(db_path)
        assert "Application Support" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_returns_path_on_linux(self, monkeypatch):
        """Test returns correct path on Linux."""
        monkeypatch.delenv("AENGLISC_TOOLKIT_DB_PATH", raising=False)
        monkeypatch.delenv("AENGLISC_TOOLKIT_DATA_PATH", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert ".config" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_returns_path_on_windows(self, monkeypatch):
        """Test returns correct path on Windows."""
        monkeypatch.delenv("AENGLISC_TOOLKIT_DB_PATH", raising=False)
        monkeypatch.delenv("AENGLISC_TOOLKIT_DATA_PATH", raising=False)
        monkeypatch.setattr(sys, "platform", "win32")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert "AppData" in str(db_path)
        assert "Local" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_raises_value_error_for_unsupported_platform(self, monkeypatch):
        """Test raises ValueError for unsupported platform."""
        monkeypatch.delenv("AENGLISC_TOOLKIT_DB_PATH", raising=False)
        monkeypatch.delenv("AENGLISC_TOOLKIT_DATA_PATH", raising=False)
        monkeypatch.setattr(sys, "platform", "unsupported")
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_project_db_path()

    def test_creates_directory_if_not_exists(self, monkeypatch, tmp_path):
        """Test creates directory if it doesn't exist."""
        monkeypatch.delenv("AENGLISC_TOOLKIT_DATA_PATH", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        # Mock Path.home() to return tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            db_path = get_project_db_path()
            assert db_path.parent.exists()


class TestCreateEngineWithPath:
    """Test cases for create_engine_with_path()."""

    @pytest.mark.skip(reason="This test can be run in CI, but don't run it if you have a local database, otherwise it will overwrite your database.")
    def test_creates_engine_with_default_path(self):
        """
        Test creates engine with default path when None provided.

        This test can be run in CI, but don't run it if you have a local
        database, otherwise it will overwrite your database.

        """
        engine = create_engine_with_path(None)
        assert engine is not None
        assert engine.url.database is not None

    def test_creates_engine_with_custom_path(self, tmp_path):
        """Test creates engine with custom path."""
        db_path = tmp_path / "test.db"
        engine = create_engine_with_path(db_path)
        assert engine is not None
        assert db_path.exists()

    def test_creates_database_file_if_not_exists(self, tmp_path):
        """Test creates database file if it doesn't exist."""
        db_path = tmp_path / "new.db"
        assert not db_path.exists()
        create_engine_with_path(db_path)
        assert db_path.exists()


class TestSQLitePragmas:
    """Validate SQLite PRAGMA defaults and override behavior."""

    def test_default_sqlite_pragmas(self, tmp_path, monkeypatch):
        """Default performance pragmas should be applied on connection."""
        monkeypatch.delenv("OE_SQLITE_SYNCHRONOUS", raising=False)
        monkeypatch.delenv("OE_SQLITE_CACHE_SIZE_KIB", raising=False)
        monkeypatch.delenv("OE_SQLITE_MMAP_SIZE_MB", raising=False)
        monkeypatch.delenv("OE_SQLITE_BUSY_TIMEOUT_MS", raising=False)
        monkeypatch.delenv("OE_SQLITE_TEMP_STORE", raising=False)
        monkeypatch.delenv("OE_SQLITE_WAL_AUTOCHECKPOINT_PAGES", raising=False)

        db_path = tmp_path / "default_pragmas.db"
        engine = create_engine_with_path(db_path)
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert conn.execute(text("PRAGMA synchronous")).scalar() == 1
            assert conn.execute(text("PRAGMA cache_size")).scalar() == -16384
            assert conn.execute(text("PRAGMA mmap_size")).scalar() == 134217728
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 10000
            assert conn.execute(text("PRAGMA temp_store")).scalar() == 2
            assert conn.execute(text("PRAGMA wal_autocheckpoint")).scalar() == 2000
        engine.dispose()

    def test_sqlite_pragma_env_overrides(self, tmp_path, monkeypatch):
        """Environment variables should override default PRAGMA values."""
        monkeypatch.setenv("OE_SQLITE_SYNCHRONOUS", "FULL")
        monkeypatch.setenv("OE_SQLITE_CACHE_SIZE_KIB", "32768")
        monkeypatch.setenv("OE_SQLITE_MMAP_SIZE_MB", "64")
        monkeypatch.setenv("OE_SQLITE_BUSY_TIMEOUT_MS", "15000")
        monkeypatch.setenv("OE_SQLITE_TEMP_STORE", "FILE")
        monkeypatch.setenv("OE_SQLITE_WAL_AUTOCHECKPOINT_PAGES", "4096")

        db_path = tmp_path / "override_pragmas.db"
        engine = create_engine_with_path(db_path)
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA synchronous")).scalar() == 2
            assert conn.execute(text("PRAGMA cache_size")).scalar() == -32768
            assert conn.execute(text("PRAGMA mmap_size")).scalar() == 67108864
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 15000
            assert conn.execute(text("PRAGMA temp_store")).scalar() == 1
            assert conn.execute(text("PRAGMA wal_autocheckpoint")).scalar() == 4096
        engine.dispose()

    def test_invalid_sqlite_pragma_env_falls_back_to_defaults(
        self, tmp_path, monkeypatch
    ):
        """Invalid PRAGMA env values should safely fall back to defaults."""
        monkeypatch.setenv("OE_SQLITE_SYNCHRONOUS", "INVALID")
        monkeypatch.setenv("OE_SQLITE_CACHE_SIZE_KIB", "oops")
        monkeypatch.setenv("OE_SQLITE_MMAP_SIZE_MB", "-7")
        monkeypatch.setenv("OE_SQLITE_BUSY_TIMEOUT_MS", "bad")
        monkeypatch.setenv("OE_SQLITE_TEMP_STORE", "BANANA")
        monkeypatch.setenv("OE_SQLITE_WAL_AUTOCHECKPOINT_PAGES", "0")

        db_path = tmp_path / "fallback_pragmas.db"
        engine = create_engine_with_path(db_path)
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA synchronous")).scalar() == 1
            assert conn.execute(text("PRAGMA cache_size")).scalar() == -16384
            assert conn.execute(text("PRAGMA mmap_size")).scalar() == 134217728
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 10000
            assert conn.execute(text("PRAGMA temp_store")).scalar() == 2
            assert conn.execute(text("PRAGMA wal_autocheckpoint")).scalar() == 2000
        engine.dispose()

    def test_run_pragma_optimize_success(self, tmp_path):
        """PRAGMA optimize should return True when it succeeds."""
        db_path = tmp_path / "optimize_ok.db"
        engine = create_engine_with_path(db_path)
        assert run_pragma_optimize(engine) is True
        engine.dispose()

    def test_run_pragma_optimize_failure(self):
        """PRAGMA optimize should return False on engine/connection failures."""

        class BadEngine:
            def connect(self):
                msg = "connection failed"
                raise RuntimeError(msg)

        assert run_pragma_optimize(BadEngine()) is False


class TestSessionLocal:
    """Test cases for SessionLocal."""

    def test_session_local_is_defined(self):
        """Test SessionLocal is defined."""
        assert SessionLocal is not None
        assert callable(SessionLocal)

    def test_session_local_creates_session(self):
        """Test SessionLocal creates a session."""
        session = SessionLocal()
        assert session is not None
        session.close()


class TestTableToModelName:
    """Test cases for table_to_model_name()."""

    def test_converts_plural_table_name(self):
        """Test converts plural table name to singular model name."""
        result = table_to_model_name("projects")
        assert result == "Project"

    def test_converts_singular_table_name(self):
        """Test converts singular table name (no 's' ending)."""
        result = table_to_model_name("project")
        assert result == "Project"

    def test_handles_empty_string(self):
        """Test handles empty string."""
        result = table_to_model_name("")
        assert result == ""

    def test_handles_single_character(self):
        """Test handles single character."""
        result = table_to_model_name("s")
        assert result == ""
