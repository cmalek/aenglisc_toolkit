"""Service for handling database migrations."""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

from alembic import command
from alembic.config import Config
from alembic.script import Script, ScriptDirectory
from PySide6.QtCore import QSettings
from sqlalchemy import inspect, text

from oeapp import __version__
from oeapp.db import (
    Base,
    create_engine_with_path,
    get_project_db_path,
    read_alembic_revision,
    table_to_model_name,
)
from oeapp.exc import (
    BackupFailed,
    MigrationCreationFailed,
    MigrationFailed,
    UnknownDatabaseRevision,
)

from .backup import LAST_APP_VERSION_KEY, BackupService
from .logs import get_logger
from .mixins import ProjectFoldersMixin
from .revision_version import RevisionVersionResolver


@dataclass
class MigrationResult:
    """Result of a migration."""

    #: The application version
    app_version: str | None
    #: The curren database migration version
    migration_version: str


@dataclass
class MigrationCreationResult:
    """Service for handling migration files."""

    #: The migration file path
    migration_file_path: Path
    #: The revision ID
    revision_id: str


class MigrationMetadataService(ProjectFoldersMixin):
    """
    Service for handling migration metadata.

    This handles this JSON file:

    - migration_versions.json: This file contains the migration versions and the
      minimum app version required for each migration.

    """

    @staticmethod
    def _is_truthy(value: str | None) -> bool:
        """
        Return True when an environment variable value is truthy.

        Args:
            value: Value.

        Returns:
            The computed value.

        """
        if value is None:
            return False
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _guard_repo_metadata_write_under_pytest(self) -> None:
        """
        Prevent pytest from mutating repo-tracked migration metadata by default.

        Tests should inject a mock/in-memory metadata service or patch
        MIGRATION_VERSIONS_PATH to a temporary file.
        """
        if "PYTEST_CURRENT_TEST" not in os.environ:
            return
        if self._is_truthy(os.environ.get("AENGLISC_ALLOW_REPO_METADATA_WRITE")):
            return

        target = self.MIGRATION_VERSIONS_PATH.resolve()
        canonical = (
            self.PROJECT_ROOT / "oeapp" / "etc" / "migration_versions.json"
        ).resolve()
        if target != canonical:
            return

        msg = (
            "Refusing to write repo migration metadata during pytest: "
            f"{target}. Use an injected metadata service, patch "
            "MIGRATION_VERSIONS_PATH to a temp file, or set "
            "AENGLISC_ALLOW_REPO_METADATA_WRITE=1 to override."
        )
        raise RuntimeError(msg)

    @property
    def versions(self) -> dict[str, Any] | None:
        """
        Read migration versions metadata from JSON file.

        Returns:
            Migration versions metadata dictionary, or None if not found

        """
        if not self.MIGRATION_VERSIONS_PATH.exists():
            return None
        try:
            with self.MIGRATION_VERSIONS_PATH.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
        except (OSError, PermissionError, json.JSONDecodeError):
            return None
        return metadata

    @versions.setter
    def versions(self, metadata: dict[str, Any]) -> None:
        """
        Write migration versions metadata to JSON file.

        Args:
            metadata: Migration versions metadata dictionary

        """
        self._guard_repo_metadata_write_under_pytest()
        self.MIGRATION_VERSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.MIGRATION_VERSIONS_PATH.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")

    def get_min_version_for_migration(self, migration_version: str) -> str | None:
        """
        Get the minimum app version required for a given migration version.

        Args:
            migration_version: Migration revision ID

        Returns:
            Minimum app version string, or None if not found

        """
        if self.versions is None:
            return None
        try:
            return self.versions.get(migration_version)
        except KeyError:
            return None

    def update(self, revision: str, min_version: str) -> None:
        """
        Update migration_versions.json with new migration.

        Ensures only one migration SHA per version (the latest one).

        Args:
            revision: Migration revision ID
            min_version: Minimum app version required

        """
        versions = self.versions
        if versions is None:
            versions = {}
        # Remove any existing migration SHA that maps to this version
        # (to ensure only the latest migration SHA per version)
        keys_to_remove = [
            old_revision
            for old_revision, old_version in versions.items()
            if old_version == min_version
        ]
        for key in keys_to_remove:
            del versions[key]

        # Add the new migration SHA for this version
        versions[revision] = min_version
        self.versions = versions
        if keys_to_remove:
            print(  # noqa: T201
                f"Updated {self.MIGRATION_VERSIONS_PATH!s}: "
                f"Replaced {keys_to_remove} with {revision} for version "
                f"{min_version}"
            )
        else:
            print(  # noqa: T201
                f"Updated {self.MIGRATION_VERSIONS_PATH!s} with "
                f"{revision}: {min_version}"
            )


class FieldMappingService(ProjectFoldersMixin):
    """Service for handling field mappings."""

    #: Alter column pattern.
    ALTER_COLUMN_PATTERN: Final[re.Pattern[str]] = re.compile(
        r'batch_op\.alter_column\(["\']([^"\']+)["\'][^)]*new_column_name\s*=\s*["\']([^"\']+)["\']'
    )
    #: Alter table pattern.
    ALTER_TABLE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r'batch_alter_table\(["\']([^"\']+)["\']'
    )

    @property
    def mapping(self) -> dict[str, Any]:
        """
        Read field mappings from JSON file.

        Returns:
            Field mappings dictionary, or None if not found

        """
        if not self.FIELD_MAPPINGS_PATH.exists():
            return {}
        try:
            with self.FIELD_MAPPINGS_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, PermissionError, json.JSONDecodeError):
            return {}

    @mapping.setter
    def mapping(self, mappings: dict[str, Any]) -> None:
        """
        Write field mappings to JSON file.

        Args:
            mappings: Mappings.

        """
        self.FIELD_MAPPINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.FIELD_MAPPINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2)
        f.write("\n")

    def update(self, migration_file: Path) -> bool:
        """
        Update field mappings with new migration, but only if renames are provided.

        Args:
            migration_file: Path to the migration file

        Returns:
            True if the field mappings were updated, False otherwise

        """
        revision_id, renames = self.discover(migration_file)
        mappings = self.mapping
        if renames:
            mappings[revision_id] = renames
            self.mapping = mappings
            return True
        return False

    def discover(self, migration_file: Path) -> tuple[str, dict[str, dict[str, str]]]:
        """
        Discover field renames from a migration file.

        Args:
            migration_file: Path to the migration file

        Returns:
            Tuple containing the revision ID and the field renames

        """
        renames: dict[str, dict[str, str]] = {}

        # Read file content
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()

        migration_service = MigrationService()
        revision_id = migration_service.extract_revision_id(migration_file)

        # Look for batch_op.alter_column() calls with new_column_name parameter
        # Pattern: batch_op.alter_column("old_name", new_column_name="new_name", ...)
        matches = self.ALTER_COLUMN_PATTERN.finditer(content)
        for match in matches:
            old_name = match.group(1)
            new_name = match.group(2)

            # Try to determine table/model name from context
            # Look backwards for table name in batch_alter_table
            before_match = content[: match.start()]
            table_match = self.ALTER_TABLE_PATTERN.search(before_match)
            if table_match:
                table_name = table_match.group(1)
                model_name = table_to_model_name(table_name)
                if model_name not in renames:
                    renames[table_name] = {}
                renames[table_name][old_name] = new_name
        return revision_id, renames


class MigrationService(ProjectFoldersMixin):
    """
    Service for handling database migrations.

    Args:
        backup_service: Backup service.
        engine: Engine.
        migration_metadata_service: Migration metadata service.

    """

    #: Regex for extracting the revision ID from a migration file
    REVISION_ID_REGEX: Final[re.Pattern[str]] = re.compile(
        r'revision\s*:\s*str\s*=\s*["\']([^"\']+)["\']'
    )

    def __init__(
        self,
        backup_service: BackupService | None = None,
        engine: "Engine | None" = None,
        migration_metadata_service: MigrationMetadataService | None = None,
    ) -> None:
        """
        Initialize migration service.

        Args:
            backup_service: Optional BackupService instance (created if not provided)
            engine: Optional SQLAlchemy engine (created if not provided)
            migration_metadata_service: Optional MigrationMetadataService instance
                (created if not provided)

        """
        #: The logger for the migration service.
        self.logger = get_logger(__name__)
        #: Engine.
        self.engine = engine if engine is not None else create_engine_with_path()
        #: Database file the engine points at; backup, upgrade and restore all use it.
        database = self.engine.url.database
        self.db_path = Path(database) if database else get_project_db_path()
        #: Allow dependency injection for testing, but create defaults for normal use
        self.backup_service = (
            backup_service
            if backup_service is not None
            else BackupService(db_path=self.db_path)
        )
        #: Migration metadata service.
        self.migration_metadata_service = (
            migration_metadata_service
            if migration_metadata_service is not None
            else MigrationMetadataService()
        )
        #: Resolves which application version a database revision needs.
        self.revision_versions = RevisionVersionResolver(
            self.migration_metadata_service, self.backup_service
        )

    @property
    def config(self) -> Config:
        """
        Get the Alembic configuration.

        Returns:
            Alembic configuration

        """
        return Config(str(self.ALEMBIC_INI_PATH))

    @property
    def script(self) -> ScriptDirectory:
        """
        Get the Alembic script.

        Returns:
            Alembic script

        """
        return ScriptDirectory.from_config(self.config)

    def last_working_migration_version(self) -> str | None:
        """
        Get the last known working migration version from QSettings.

        Returns:
            Migration version string, or None if not set

        """
        settings = QSettings()
        return cast(
            "str | None",
            settings.value("migration/last_working_version", None, type=str),
        )

    def newest_migration_file(self) -> Path | None:
        """
        Get the newest migration file from the migrations directory.

        Returns:
            Path to the newest migration file, or None if no migrations exist

        """
        migration_files = sorted(
            self.MIGRATIONS_DIR.glob("*.py"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return migration_files[0] if migration_files else None

    def file_migration_version(self, migration_file: Path) -> str | None:
        """
        Get the migration version from a migration file.

        Args:
            migration_file: Migration file.

        Returns:
            The computed value.

        """
        return self.extract_revision_id(migration_file)

    def latest_migration_version(self) -> str | None:
        """
        Get the latest migration version from Alembic.

        Returns:
            The computed value.

        """
        # ponytail: Alembic head, not newest file mtime (edits shuffle mtimes)
        return self.code_migration_version()

    def db_migration_version(self) -> str | None:
        """
        Get the current database migration version from Alembic.

        Returns:
            Migration version string, or None if no version is set

        """
        return read_alembic_revision(self.engine)

    def known_revisions(self) -> set[str]:
        """
        List every revision this build's Alembic scripts define.

        Returns:
            The set of revision IDs

        """
        return {script.revision for script in self.script.walk_revisions()}

    def is_known_revision(self, revision: str) -> bool:
        """
        Check whether this build understands a database revision.

        Args:
            revision: Alembic revision to check

        Returns:
            True if the revision is one of this build's scripts

        """
        return revision in self.known_revisions()

    def ensure_known_revision(self) -> None:
        """
        Refuse to proceed with a database this build does not understand.

        Raises:
            UnknownDatabaseRevision: If the database revision is not one of this
                build's scripts

        """
        revision = self.db_migration_version()
        if revision is None or self.is_known_revision(revision):
            return
        raise UnknownDatabaseRevision(
            revision, self.revision_versions.required_app_version(revision)
        )

    def code_migration_version(self) -> str | None:
        """
        Get the head migration version from Alembic (what code expects).

        Returns:
            Head migration version string, or None if no migrations exist

        """
        return self.script.get_current_head()

    def revision_chain(self, from_version: str, to_version: str) -> list[str]:  # noqa: PLR0912
        """
        Get ordered list of migration revision IDs from one version to another.

        Args:
            from_version: Starting migration version (export version)
            to_version: Target migration version (current version)

        Returns:
            Ordered list of migration revision IDs (from oldest to newest)

        """
        # Build a map of down_revision -> list of revisions that have it
        # This allows us to walk forward from from_version to to_version
        forward_map: dict[str | None, list[str]] = {}
        revision_to_down: dict[str, str | None] = {}

        for script_revision in self.script.walk_revisions():
            rev_id = script_revision.revision
            down_rev = script_revision.down_revision
            if isinstance(down_rev, str):
                revision_to_down[rev_id] = down_rev
                if down_rev not in forward_map:
                    forward_map[down_rev] = []
                forward_map[down_rev].append(rev_id)
            elif isinstance(down_rev, (list, tuple)) and down_rev:
                # Handle multiple down revisions - take first one
                revision_to_down[rev_id] = down_rev[0]
                if down_rev[0] not in forward_map:
                    forward_map[down_rev[0]] = []
                forward_map[down_rev[0]].append(rev_id)
            else:
                revision_to_down[rev_id] = None
                if None not in forward_map:
                    forward_map[None] = []
                forward_map[None].append(rev_id)

        # If versions are the same, return empty list
        if from_version == to_version:
            return []

        # Walk forward from from_version to to_version
        chain: list[str] = []
        current = from_version
        visited: set[str] = set()

        while current and current != to_version:
            if current in visited:
                # Circular reference or invalid chain
                break
            visited.add(current)

            # Find next revision(s) that have current as down_revision
            if current in forward_map:
                next_revisions = forward_map[current]
                if next_revisions:
                    # Take the first one (assuming linear chain)
                    # If there are multiple, we might need more sophisticated logic
                    current = next_revisions[0]
                    chain.append(current)
                else:
                    break
            else:
                break

        return chain

    def has_pending_migrations(self) -> bool:
        """
        Check whether the database revision differs from the Alembic head.

        Alembic is the only source of truth: the application-version catalog
        plays no part.

        Returns:
            True if the database revision is not the head, False otherwise

        """
        head_version = self.code_migration_version()
        if head_version is None:
            return False
        return self.db_migration_version() != head_version

    def create(self, name: str) -> MigrationCreationResult:
        """
        Create a new migration.

        Args:
            name: Migration name

        Returns:
            Migration revision ID

        """
        result = command.revision(self.config, message=name, autogenerate=True)
        if result is None:
            self.logger.error("migration.creation.failed", name=name)
            msg = f"Failed to create migration: {name}"
            raise MigrationCreationFailed(Exception(msg))
        result = cast("Script", result)
        self.migration_metadata_service.update(result.revision, __version__)
        self.logger.info(
            "migration.creation.success",
            name=name,
            revision_id=result.revision,
            version=__version__,
        )
        return MigrationCreationResult(
            migration_file_path=Path(result.path),
            revision_id=result.revision,
        )

    def migrate(self) -> MigrationResult:
        """
        Migrate the database to the latest version.

        A Fresh Database is built and stamped with no backup. Otherwise a
        Pre-migration Backup is taken, the upgrade runs, and a post-migration
        backup follows. On failure the pre-migration backup is restored.

        Side Effects:
            Writes backups, upgrades the database, and prunes old backups.

        Raises:
            MigrationFailed: If the backup or the migration fails
            UnknownDatabaseRevision: If the database revision is not one of this
                build's scripts (raised before any backup or upgrade)

        Returns:
            The resulting migration state

        """
        self.ensure_known_revision()
        if not self.has_pending_migrations():
            self.logger.info("migration.no-pending-migrations")
            db_version = self.db_migration_version()
            return MigrationResult(
                app_version=__version__,
                migration_version=db_version or "",
            )
        if not self._has_alembic_table():
            return self.apply_migrations()  # Fresh Database: nothing to protect
        backup_path = self._backup_before_migration()
        try:
            result = self.apply_migrations()
        except Exception as e:
            raise self._safe_roll_back(e, backup_path) from e
        self._backup_after_migration()
        return result

    def _has_alembic_table(self) -> bool:
        """
        Check whether the database has an ``alembic_version`` table.

        A Fresh Database has none; an existing but empty table (a first launch
        interrupted before stamping) is an ordinary pending migration.

        Returns:
            True if the table exists, even when it is empty

        """
        return "alembic_version" in inspect(self.engine).get_table_names()

    def _backup_before_migration(self) -> Path:
        """
        Take the Pre-migration Backup, stamped with the previous build's version.

        Raises:
            MigrationFailed: If the backup cannot be created

        Returns:
            Path to the backup

        """
        previous = cast(
            "str | None", QSettings().value(LAST_APP_VERSION_KEY, None, type=str)
        )
        try:
            return self.backup_service.create_backup(
                prune=False, maintained_by=previous or None
            )
        except BackupFailed as e:
            raise MigrationFailed(e, None, None) from e

    def _backup_after_migration(self) -> None:
        """
        Take the post-migration backup and enforce retention once.

        A failure here is logged, never raised: the migration has committed.

        Side Effects:
            Writes a backup and prunes old backups.
        """
        try:
            self.backup_service.create_backup(prune=False)
        except BackupFailed:
            self.logger.exception("migration.post-backup.failed")
        try:
            self.backup_service.cleanup_old_backups()
        except OSError:
            self.logger.exception("migration.cleanup.failed")

    def _roll_back(self, error: Exception, backup_path: Path) -> MigrationFailed:
        """
        Restore the pre-migration backup and describe the failure.

        Args:
            error: The exception that aborted the migration
            backup_path: The Pre-migration Backup to restore

        Side Effects:
            Overwrites the live database with the backup.

        Returns:
            The exception to raise, carrying the previous build's version and the
            restored database's revision

        """
        metadata = self.backup_service.restore_backup(backup_path)
        if metadata is None:
            self.logger.error("migration.restore.failed", backup_path=str(backup_path))
            return self._unrestored_failure(error, backup_path)
        try:
            migration_version = self.db_migration_version()
        except Exception as version_error:  # noqa: BLE001
            self.logger.debug(
                "migration.restore.version-unreadable", error=version_error
            )
            migration_version = None
        return MigrationFailed(
            error,
            metadata.get("application_version"),
            migration_version,
            restored=True,
            backup_path=backup_path,
            database_path=self.db_path,
        )

    def _unrestored_failure(
        self, error: Exception, backup_path: Path
    ) -> MigrationFailed:
        """
        Describe a failure whose automatic restore did not happen.

        Never raises; versions come from the backup's sidecar when readable.

        Args:
            error: The exception that aborted the migration
            backup_path: The Pre-migration Backup that could not be restored

        Returns:
            The exception to raise, with ``restored=False``

        """
        try:
            sidecar = self.backup_service.read_backup_metadata(backup_path)
        except Exception:
            self.logger.exception("migration.rollback.sidecar-unreadable")
            sidecar = {}
        return MigrationFailed(
            error,
            sidecar.get("application_version"),
            sidecar.get("migration_version"),
            restored=False,
            backup_path=backup_path,
            database_path=self.db_path,
        )

    def _safe_roll_back(self, error: Exception, backup_path: Path) -> MigrationFailed:
        """
        Roll back without ever masking the original migration error.

        Args:
            error: The exception that aborted the migration
            backup_path: The Pre-migration Backup to restore

        Side Effects:
            Overwrites the live database with the backup.

        Returns:
            The exception to raise; ``restored=False`` if rollback itself raised

        """
        try:
            return self._roll_back(error, backup_path)
        except Exception:
            self.logger.exception("migration.rollback.failed")
            return self._unrestored_failure(error, backup_path)

    def _upgrade_to_head(self) -> None:
        """
        Run ``alembic upgrade head`` on the injected engine's database.

        Foreign keys are switched OFF on the migration connection before any
        statement, because batch table recreation under ``foreign_keys=ON`` can
        cascade-delete child rows. The pragma is a no-op once a transaction has
        begun, so it must come first. It is switched back ON afterwards because
        the pooled connection is reused.

        Side Effects:
            Upgrades the database schema and commits.

        """
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            config = self.config
            config.attributes["connection"] = connection
            try:
                command.upgrade(config, "head")
                connection.commit()
            finally:
                self._restore_foreign_keys(connection)

    def _restore_foreign_keys(self, connection: "Connection") -> None:
        """
        Roll back any open transaction, then switch foreign keys back ON.

        The pragma is a no-op inside a transaction, so a failed upgrade must be
        rolled back first or the pooled connection keeps foreign keys OFF. A
        failure here is logged, never raised, so it cannot mask the original
        migration exception.

        Args:
            connection: The connection the upgrade ran on

        Side Effects:
            Rolls back an open transaction and resets ``PRAGMA foreign_keys``.

        """
        try:
            if connection.in_transaction():
                connection.rollback()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        except Exception:
            self.logger.exception("migration.foreign_keys.restore_failed")

    def _build_fresh_database(self) -> MigrationResult:
        """
        Create the ``alembic_version`` table, every model table, and stamp head.

        Side Effects:
            Creates the schema and the ``alembic_version`` table.

        Returns:
            The resulting migration state

        """
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"  # noqa: E501
                )
            )
            conn.commit()
        return self._stamp_unstamped_database()

    def _stamp_unstamped_database(self) -> MigrationResult:
        """
        Complete the schema from the models and stamp the head revision.

        Used for a database whose ``alembic_version`` table exists but holds no
        revision (a first launch interrupted before stamping); ``create_all``
        only adds what is missing.

        Side Effects:
            Creates missing tables and inserts the head revision.

        Returns:
            The resulting migration state

        """
        Base.metadata.create_all(self.engine)
        initial_version = self.latest_migration_version()
        with self.engine.connect() as conn:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": initial_version},
            )
            conn.commit()
        self.logger.info(
            "migration.alembic.table.created", initial_version=initial_version
        )
        return MigrationResult(
            app_version=__version__,
            migration_version=cast("str", initial_version),
        )

    def apply_migrations(self) -> MigrationResult:
        """
        Apply pending Alembic migrations.

        This should be called on application startup.
        Raises an exception if migrations fail.

        Raises:
            Exception: If migration fails

        Returns:
            Tuple containing the current database migration version and the
            current application version

        """
        if not self._has_alembic_table():
            return self._build_fresh_database()
        if self.db_migration_version() is None:
            return self._stamp_unstamped_database()
        # Existing database - apply migrations normally
        self._upgrade_to_head()
        # Migration succeeded - return current version
        current_version = self.db_migration_version()
        self.logger.info(
            "migration.migrate.success",
            current_version=current_version,
        )
        return MigrationResult(
            app_version=__version__,
            migration_version=cast("str", current_version),
        )

    def extract_revision_id(self, migration_file: Path) -> str:
        """
        Extract the revision ID from a migration file.

        Args:
            migration_file: Path to the migration file

        Returns:
            Revision ID, or None if not found

        Raises:
            FileNotFoundError: If the migration file is not found
            SyntaxError: If the migration file is not a valid Python file
            OSError: If the migration file cannot be read
            PermissionError: If the migration file cannot be read
            KeyError: If the revision ID is not found

        """
        # Read file content
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()

        # Look for revision = "..." pattern
        match = self.REVISION_ID_REGEX.search(content)
        if match:
            return cast("str", match.group(1))

        # Try parsing as Python AST
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "revision":
                        if isinstance(node.value, ast.Constant):
                            value = node.value.value
                            if isinstance(value, str):
                                return value
                        if sys.version_info < (3, 8) and isinstance(
                            node.value, ast.Str
                        ):  # Python < 3.8
                            return node.value.s

        msg = f"Revision ID not found in migration file: {migration_file}"
        raise KeyError(msg)
