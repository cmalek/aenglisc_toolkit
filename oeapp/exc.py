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

    Keyword Args:
        restored: Whether the pre-migration backup was restored.
        backup_path: Path of the pre-migration backup, if one was taken.
        database_path: Path of the live database.

    """

    def __init__(  # noqa: PLR0913
        self,
        error: Exception,
        backup_app_version: str | None,
        backup_migration_version: str | None,
        *,
        restored: bool = True,
        backup_path: Path | None = None,
        database_path: Path | None = None,
    ):
        """
        Initialize the instance.

        Args:
            error: Error.
            backup_app_version: Backup app version.
            backup_migration_version: Backup migration version.

        Keyword Args:
            restored: Whether the pre-migration backup was restored.
            backup_path: Path of the pre-migration backup, if one was taken.
            database_path: Path of the live database.

        """
        #: Error.
        self.error = error
        #: Backup app version.
        self.backup_app_version = backup_app_version
        #: Backup migration version.
        self.backup_migration_version = backup_migration_version
        #: Whether the pre-migration backup was restored.
        self.restored = restored
        #: Path of the pre-migration backup, if one was taken.
        self.backup_path = backup_path
        #: Path of the live database.
        self.database_path = database_path
        super().__init__(f"Migration failed: {error}")


class UnknownDatabaseRevision(Exception):  # noqa: N818
    """
    Exception raised when the database revision is unknown to this build.

    Args:
        revision: The database's Alembic revision.
        required_app_version: Application version that understands it, or None
            when it cannot be determined.

    """

    def __init__(self, revision: str, required_app_version: str | None):
        """
        Initialize the instance.

        Args:
            revision: The database's Alembic revision.
            required_app_version: Application version that understands it, or
                None when it cannot be determined.

        """
        #: The database's Alembic revision.
        self.revision = revision
        #: Application version that understands the revision, if known.
        self.required_app_version = required_app_version
        super().__init__(f"Unknown database revision: {revision}")


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
