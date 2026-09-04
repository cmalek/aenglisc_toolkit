from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class DoesNotExist(Exception):  # noqa: N818
    """
    Exception raised when a resource does not exist.

    Args:
        resource_type: Resource type.
        resource_id: Resource id.

    """

    def __init__(self, resource_type: str, resource_id: int | str):
        """
        Initialize the instance.

        Args:
            resource_type: Resource type.
            resource_id: Resource id.

        """
        #: Resource type.
        self.resource_type = resource_type
        #: Resource id.
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" does not exist')


class NoAnnotationAvailable(Exception):  # noqa: N818
    """Exception raised when no annotation is available."""

    def __init__(self):
        """
        Initialize the instance.
        """
        super().__init__("No annotation available")


class AlreadyExists(Exception):  # noqa: N818
    """
    Exception raised when a resource already exists.

    Args:
        resource_type: Resource type.
        resource_id: Resource id.

    """

    def __init__(self, resource_type: str, resource_id: int | str):
        """
        Initialize the instance.

        Args:
            resource_type: Resource type.
            resource_id: Resource id.

        """
        #: Resource type.
        self.resource_type = resource_type
        #: Resource id.
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" already exists')


class MigrationCreationFailed(Exception):  # noqa: N818
    """
    Exception raised when a migration creation fails.

    Args:
        error: Error.

    """

    def __init__(self, error: Exception):
        """
        Initialize the instance.

        Args:
            error: Error.

        """
        #: Error.
        self.error = error
        super().__init__(f"Migration creation failed: {error}")


class MigrationFailed(Exception):  # noqa: N818
    """
    Exception raised when a migration fails.

    Args:
        error: Error.
        backup_app_version: Backup app version.
        backup_migration_version: Backup migration version.

    """

    def __init__(
        self,
        error: Exception,
        backup_app_version: str | None,
        backup_migration_version: str | None,
    ):
        """
        Initialize the instance.

        Args:
            error: Error.
            backup_app_version: Backup app version.
            backup_migration_version: Backup migration version.

        """
        #: Error.
        self.error = error
        #: Backup app version.
        self.backup_app_version = backup_app_version
        #: Backup migration version.
        self.backup_migration_version = backup_migration_version
        super().__init__(f"Migration failed: {error}")


class MigrationSkipped(Exception):  # noqa: N818
    """
    Exception raised when a migration is skipped.

    Args:
        skip_until_version: Skip until version.

    """

    def __init__(self, skip_until_version: str):
        """
        Initialize the instance.

        Args:
            skip_until_version: Skip until version.

        """
        #: Skip until version.
        self.skip_until_version = skip_until_version
        super().__init__(f"Migration skipped: {skip_until_version}")


class BackupFailed(Exception):  # noqa: N818
    """
    Exception raised when a backup fails.

    Args:
        error: Error.
        backup_path: Backup path.

    """

    def __init__(self, error: Exception, backup_path: "Path"):
        """
        Initialize the instance.

        Args:
            error: Error.
            backup_path: Backup path.

        """
        #: Error.
        self.error = error
        #: Backup path.
        self.backup_path = backup_path
        super().__init__(f"Backup failed: {error}")
