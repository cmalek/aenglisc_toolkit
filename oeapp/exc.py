from pathlib import Path
from typing import TYPE_CHECKING


class DoesNotExist(Exception):  # noqa: N818
    """Exception raised when a resource does not exist."""

    def __init__(self, resource_type: str, resource_id: int | str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" does not exist')


class NoAnnotationAvailable(Exception):  # noqa: N818
    """Exception raised when no annotation is available."""

    def __init__(self):
        super().__init__("No annotation available")


class AlreadyExists(Exception):  # noqa: N818
    """Exception raised when a resource already exists."""

    def __init__(self, resource_type: str, resource_id: int | str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" already exists')


class MigrationCreationFailed(Exception):  # noqa: N818
    """Exception raised when a migration creation fails."""

    def __init__(self, error: Exception):
        self.error = error
        super().__init__(f"Migration creation failed: {error}")


class MigrationFailed(Exception):  # noqa: N818
    """Exception raised when a migration fails."""

    def __init__(
        self,
        error: Exception,
        backup_app_version: str | None,
        backup_migration_version: str | None,
    ):
        self.error = error
        self.backup_app_version = backup_app_version
        self.backup_migration_version = backup_migration_version
        super().__init__(f"Migration failed: {error}")


class MigrationSkipped(Exception):  # noqa: N818
    """Exception raised when a migration is skipped."""

    def __init__(self, skip_until_version: str):
        self.skip_until_version = skip_until_version
        super().__init__(f"Migration skipped: {skip_until_version}")


class BackupFailed(Exception):  # noqa: N818
    """Exception raised when a backup fails."""

    def __init__(self, error: Exception, backup_path: Path):
        self.error = error
        self.backup_path = backup_path
        super().__init__(f"Backup failed: {error}")
