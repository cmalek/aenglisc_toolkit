"""Backup service for database backups."""

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final, cast

from PySide6.QtCore import QObject, QSettings
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError

from oeapp import __version__
from oeapp.db import get_project_db_path, read_alembic_revision
from oeapp.exc import BackupFailed
from oeapp.models.project import Project

from .logs import get_logger

if TYPE_CHECKING:
    from pathlib import Path

#: QSettings key holding the application version that last started successfully.
LAST_APP_VERSION_KEY: Final[str] = "app/current_version"

class BackupService(QObject):
    """
    Service for managing database backups.

    Handles creating backups, managing retention, and extracting metadata.
    """

    def __init__(self) -> None:
        """Initialize backup service."""
        super().__init__()
        #: The global settings for the application.
        self.settings = QSettings()
        #: The path to the project database.
        self.db_path = get_project_db_path()
        #: The directory to store backups.
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        #: The logger
        self.logger = get_logger(__name__)

    def get_num_backups(self) -> int:
        """
        Get the number of backups to keep from settings.

        Returns:
            Number of backups to keep (default: 5)

        """
        return cast("int", self.settings.value("backup/num_backups", 5, type=int))

    def get_interval_minutes(self) -> int:
        """
        Get the backup interval in minutes from settings.

        Returns:
            Backup interval in minutes (default: 720 = 12 hours)

        """
        return cast(
            "int", self.settings.value("backup/interval_minutes", 720, type=int)
        )

    def get_last_backup_time(self) -> datetime | None:
        """
        Get the timestamp of the last backup from settings.

        Returns:
            Last backup timestamp in local time, or None if no backup has been made

        """
        last_backup_epoch = cast(
            "float | None",
            self.settings.value("backup/last_backup_time", None, type=float),
        )
        if last_backup_epoch is not None:
            # Convert from UNIX epoch (UTC) to local datetime
            return datetime.fromtimestamp(last_backup_epoch, tz=UTC)
        return None

    def set_last_backup_time(self, timestamp: datetime) -> None:
        """
        Set the timestamp of the last backup in settings.

        Stores as UNIX epoch (seconds since 1970-01-01 UTC) to avoid DST issues.

        Args:
            timestamp: Timestamp of the backup (will be converted to UTC epoch)

        """
        # Convert datetime to UNIX epoch (UTC-based)
        epoch_seconds = timestamp.timestamp()
        self.settings.setValue("backup/last_backup_time", epoch_seconds)

    def should_backup(self) -> bool:
        """
        Check if a backup is needed based on time since last backup.

        Returns:
            True if backup is needed, False otherwise

        """
        last_backup = self.get_last_backup_time()
        if last_backup is None:
            return True

        interval_minutes = self.get_interval_minutes()
        time_since_backup = (datetime.now(tz=UTC) - last_backup).total_seconds() / 60

        return time_since_backup >= interval_minutes

    def get_current_migration_version(self, engine: Engine) -> str | None:
        """
        Get the current migration version from the database.

        Args:
            engine: SQLAlchemy engine

        Returns:
            Migration version string, or None if no version is set

        """
        return read_alembic_revision(engine)

    def extract_backup_metadata(
        self, engine: Engine, *, maintained_by: str | None = __version__
    ) -> dict[str, Any]:
        """
        Extract metadata from the database for a backup sidecar.

        Args:
            engine: SQLAlchemy engine for the database being backed up

        Keyword Args:
            maintained_by: Application version that maintained the captured state

        Returns:
            Dictionary containing backup metadata

        """
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "backup_timestamp": datetime.now(UTC).isoformat(),
            "database_file_size": db_size,
            "migration_version": self.get_current_migration_version(engine),
            "application_version": maintained_by,
            "created_by_version": __version__,
            "projects": self._project_summaries(),
        }

    def _project_summaries(self) -> list[dict[str, Any]]:
        """
        Summarise each project for the sidecar.

        Returns:
            One dict per project, or an empty list when projects cannot be read

        """
        try:
            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "last_updated": project.updated_at.isoformat(),
                    "token_count": project.total_token_count(),
                }
                for project in Project.list()
            ]
        except SQLAlchemyError as e:
            self.logger.warning("backup.projects.failed", error=e)
            return []

    def create_backup(
        self, *, prune: bool = True, maintained_by: str | None = __version__
    ) -> "Path":
        """
        Create a backup of the database immediately.

        Keyword Args:
            prune: Whether to enforce the retention limit afterwards
            maintained_by: Application version that maintained the database
                state being captured (the running version unless a caller is
                capturing state the previous version left)

        Side Effects:
            Writes a ``.db`` snapshot and ``.json`` sidecar to the backup
            directory and updates the last-backup time.

        Raises:
            BackupFailed: If the database is missing or the backup fails

        Returns:
            Path to the created backup file

        """
        if not self.db_path.exists():
            raise BackupFailed(OSError("Database file does not exist"), self.db_path)
        backup_path, metadata_path = self._free_backup_paths()
        try:
            self._snapshot(self.db_path, backup_path)
        except (OSError, sqlite3.Error) as e:
            self.logger.exception(
                "backup.failed", error=e, backup_path=str(backup_path)
            )
            raise BackupFailed(e, backup_path) from e
        metadata = self._collect_metadata(maintained_by)
        try:
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except (OSError, TypeError) as e:
            self.logger.exception(
                "backup.metadata.save.failed",
                error=e,
                backup_path=str(backup_path),
            )
            raise BackupFailed(e, metadata_path) from e
        self.set_last_backup_time(datetime.now(UTC))
        if prune:
            self._prune_quietly()
        self.logger.info("backup.success", backup_path=str(backup_path))
        return backup_path

    def _free_backup_paths(self) -> tuple["Path", "Path"]:
        """
        Pick a backup path and sidecar path that do not exist yet.

        Returns:
            The ``.db`` path and its ``.json`` sidecar path

        """
        stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S-%f")
        base = f"{self.db_path.stem}_{stamp}"
        attempt = 0
        while True:
            name = base if attempt == 0 else f"{base}-{attempt}"
            backup_path = self.backup_dir / f"{name}.db"
            metadata_path = backup_path.with_suffix(".json")
            if not backup_path.exists() and not metadata_path.exists():
                return backup_path, metadata_path
            attempt += 1

    @staticmethod
    def _snapshot(source_path: "Path", target_path: "Path") -> None:
        """
        Copy a database with SQLite's backup API (WAL-safe).

        Args:
            source_path: Database to read
            target_path: File to write

        """
        source = sqlite3.connect(source_path)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def _collect_metadata(self, maintained_by: str | None) -> dict[str, Any]:
        """
        Build the sidecar metadata, falling back to minimal metadata on failure.

        Args:
            maintained_by: Application version that maintained the captured state

        Returns:
            Sidecar metadata dictionary

        """
        engine = create_engine(
            f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False}
        )
        try:
            return self.extract_backup_metadata(engine, maintained_by=maintained_by)
        except (SQLAlchemyError, OSError) as e:
            self.logger.exception("backup.metadata.extraction.failed", error=e)
            return {
                "backup_timestamp": datetime.now(UTC).isoformat(),
                "database_file_size": 0,
                "migration_version": None,
                "application_version": maintained_by,
                "created_by_version": __version__,
                "projects": [],
            }
        finally:
            engine.dispose()

    def _prune_quietly(self) -> None:
        """Enforce retention, logging instead of failing the backup."""
        try:
            self.cleanup_old_backups()
        except OSError as e:
            self.logger.warning("backup.cleanup.failed", error=e)

    def cleanup_old_backups(self) -> None:
        """Remove backups beyond the retention limit."""
        num_backups = self.get_num_backups()

        # Get all backup files (both .db and .json)
        backup_files = list(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Keep only the most recent backups
        if len(backup_files) > num_backups:
            for backup_file in backup_files[num_backups:]:
                # Delete .db file
                backup_file.unlink()
                # Delete corresponding .json file
                json_file = backup_file.with_suffix(".json")
                if json_file.exists():
                    json_file.unlink()

    def get_backup_list(self) -> list[dict[str, Any]]:
        """
        Get a list of all available backups with metadata.

        Returns:
            List of dictionaries containing backup information

        """
        backups = []
        backup_files = list(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))

        for backup_file in backup_files:
            # Try to load metadata from JSON file
            json_file = backup_file.with_suffix(".json")
            metadata: dict[str, Any] = {}
            if json_file.exists():
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except (OSError, json.JSONDecodeError):
                    # Metadata file is corrupted or unreadable - continue without it
                    pass

            # Get file stats
            try:
                stat = backup_file.stat()
                file_size = stat.st_size
                # st_mtime is a Unix timestamp (UTC-based), convert to UTC datetime
                file_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            except OSError:
                # Skip this backup file if we can't read its stats
                continue

            # Extract timestamp from metadata (stored in UTC)
            backup_timestamp = metadata.get("backup_timestamp")
            if backup_timestamp:
                try:
                    # Parse ISO format timestamp (may be UTC with timezone info)
                    file_time = datetime.fromisoformat(backup_timestamp).replace(
                        tzinfo=UTC
                    )
                    # If timezone-aware, keep it as-is (will be converted to
                    # local in UI) If naive, treat as UTC (for backwards
                    # compatibility with old backups)
                    if file_time.tzinfo is None:
                        file_time = file_time.replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    # Invalid timestamp format - use file mtime instead
                    pass

            backups.append(
                {
                    "backup_path": backup_file,
                    "metadata_path": json_file if json_file.exists() else None,
                    "file_size": file_size,
                    "backup_timestamp": file_time,
                    "migration_version": metadata.get("migration_version"),
                    "application_version": metadata.get("application_version"),
                    "projects": metadata.get("projects", []),
                }
            )

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b["backup_timestamp"], reverse=True)
        return backups

    def restore_backup(self, backup_path: "Path") -> dict[str, Any] | None:
        """
        Restore a backup file over the current database.

        Args:
            backup_path: Path to the backup file to restore

        Returns:
            Dictionary containing backup metadata, or None if restore failed

        """
        if not backup_path.exists():
            return None

        # Create a backup of current database before restoring
        _ = self.create_backup()

        # Copy backup file over current database
        try:
            shutil.copy2(backup_path, self.db_path)
        except (OSError, PermissionError) as e:
            print(f"Failed to restore backup file: {e}")  # noqa: T201
            return None

        # Load metadata from JSON file
        json_file = backup_path.with_suffix(".json")
        metadata: dict[str, Any] = {}
        if json_file.exists():
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Failed to load backup metadata: {e}")  # noqa: T201
                # Continue - restore was successful even if metadata is missing

        return metadata
