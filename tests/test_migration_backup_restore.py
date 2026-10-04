"""Unit tests for migration backup and restore functionality."""

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text

from oeapp.db import Base
from oeapp.services.migration import MigrationMetadataService, MigrationService


class InMemoryMigrationMetadataService:
    """Test double that stores migration metadata in memory."""

    def __init__(self) -> None:
        self._versions: dict[str, str] | None = {}

    @property
    def versions(self) -> dict[str, str] | None:
        return self._versions

    @versions.setter
    def versions(self, metadata: dict[str, str]) -> None:
        self._versions = metadata

    def get_min_version_for_migration(self, migration_version: str) -> str | None:
        if self._versions is None:
            return None
        return self._versions.get(migration_version)

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test.db"
    return db_path


@pytest.fixture
def temp_db_engine(temp_db_path):
    """Create a temporary database engine and initialize it."""
    engine = create_engine(f"sqlite:///{temp_db_path}")
    Base.metadata.create_all(engine)

    # Create alembic_version table
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": "test_version"},
        )
        conn.commit()

    yield engine

    engine.dispose()
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def migration_service_with_temp_db(temp_db_path, monkeypatch):
    """Create a MigrationService with a temporary database."""
    # Mock get_project_db_path to return our temp path
    monkeypatch.setattr("oeapp.services.migration.get_project_db_path", lambda: temp_db_path)

    # Create a new engine with the temp path
    with patch("oeapp.services.migration.create_engine_with_path") as mock_create:
        engine = create_engine(f"sqlite:///{temp_db_path}")
        mock_create.return_value = engine

        metadata_service = InMemoryMigrationMetadataService()
        service = MigrationService(migration_metadata_service=metadata_service)
        service.engine = engine
        yield service


class TestHasPendingMigrations:
    """Test has_pending_migrations() method."""

    def test_has_pending_migrations_when_db_behind(self, migration_service_with_temp_db, monkeypatch):
        """Test that has_pending_migrations returns True when DB is behind."""
        service = migration_service_with_temp_db

        # Mock versions to return a mapping
        mock_versions = {"newer_version": "0.1.0"}
        service.migration_metadata_service.versions = mock_versions

        # Mock code_migration_version to return a newer version
        with patch.object(service, "code_migration_version", return_value="newer_version"):
            with patch.object(service, "db_migration_version", return_value="test_version"):
                assert service.has_pending_migrations() is True

    def test_no_pending_migrations_when_db_up_to_date(self, migration_service_with_temp_db, monkeypatch):
        """Test that has_pending_migrations returns False when DB is up to date."""
        service = migration_service_with_temp_db

        # Mock versions
        mock_versions = {"current_version": "0.1.0"}
        service.migration_metadata_service.versions = mock_versions

        # Mock both versions to be the same
        with patch.object(service, "code_migration_version", return_value="current_version"):
            with patch.object(service, "db_migration_version", return_value="current_version"):
                assert service.has_pending_migrations() is False

    def test_has_pending_migrations_fresh_database(self, migration_service_with_temp_db):
        """Test that has_pending_migrations returns True for fresh database with migrations."""
        service = migration_service_with_temp_db

        # Mock db_migration_version to return None (fresh DB)
        with patch.object(service, "db_migration_version", return_value=None):
            with patch.object(service, "code_migration_version", return_value="some_version"):
                assert service.has_pending_migrations() is True

    def test_no_pending_migrations_fresh_database_no_migrations(self, migration_service_with_temp_db):
        """Test that has_pending_migrations returns False for fresh DB with no migrations."""
        service = migration_service_with_temp_db

        # Mock db_migration_version to return None (fresh DB)
        with patch.object(service, "db_migration_version", return_value=None):
            with patch.object(service, "code_migration_version", return_value=None):
                assert service.has_pending_migrations() is False


class TestMigrationMetadataWriteGuards:
    """Guardrails preventing repo metadata mutation during pytest."""

    def test_versions_setter_raises_for_repo_path_under_pytest(self, monkeypatch):
        """Writing the canonical migration_versions.json should fail under pytest."""
        service = MigrationMetadataService()
        canonical_path = (
            Path(__file__).resolve().parents[1]
            / "oeapp"
            / "etc"
            / "migration_versions.json"
        )
        monkeypatch.setattr(
            MigrationMetadataService, "MIGRATION_VERSIONS_PATH", canonical_path
        )
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_guard")
        monkeypatch.delenv("AENGLISC_ALLOW_REPO_METADATA_WRITE", raising=False)

        with pytest.raises(RuntimeError, match="Refusing to write repo migration metadata"):
            service.versions = {"deadbeef": "0.1.0"}

    def test_versions_setter_writes_when_path_is_temp(self, tmp_path, monkeypatch):
        """Writing to a temp metadata path should succeed under pytest."""
        service = MigrationMetadataService()
        temp_path = tmp_path / "migration_versions.json"
        monkeypatch.setattr(MigrationMetadataService, "MIGRATION_VERSIONS_PATH", temp_path)
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_guard")
        monkeypatch.delenv("AENGLISC_ALLOW_REPO_METADATA_WRITE", raising=False)

        service.versions = {"abc123": "0.1.0"}
        assert temp_path.exists()
        assert service.versions == {"abc123": "0.1.0"}


class TestFreshDatabaseStamp:
    """A fresh database must be stamped at the Alembic head."""

    @pytest.fixture
    def service(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OE_ANNOTATOR_DB_PATH", str(tmp_path / "fresh.db"))
        return MigrationService()

    def test_latest_migration_version_is_alembic_head(self, service):
        assert service.latest_migration_version() == service.script.get_current_head()

    def test_fresh_database_can_be_migrated_twice(self, service):
        first = service.apply_migrations()
        assert first.migration_version == service.script.get_current_head()

        second = service.apply_migrations()

        assert second.migration_version == service.script.get_current_head()
