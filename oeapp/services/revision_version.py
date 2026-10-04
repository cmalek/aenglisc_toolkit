"""Resolve which application version a database revision needs."""

from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from .backup import BackupService
    from .migration import MigrationMetadataService


class RevisionVersionResolver:
    """
    Name the application version that understands a database revision.

    The bundled catalog is consulted first. Backup sidecars come next: every
    build that took a backup at a revision understood it, so the smallest
    recorded version is the tightest answer.

    Args:
        metadata_service: Reads the revision-to-version catalog.
        backup_service: Lists backups and their sidecar versions.

    """

    def __init__(
        self,
        metadata_service: "MigrationMetadataService",
        backup_service: "BackupService",
    ) -> None:
        """
        Initialize the resolver.

        Args:
            metadata_service: Reads the revision-to-version catalog.
            backup_service: Lists backups and their sidecar versions.

        """
        #: Reads the revision-to-version catalog.
        self.metadata_service = metadata_service
        #: Lists backups and their sidecar versions.
        self.backup_service = backup_service

    def required_app_version(self, revision: str) -> str | None:
        """
        Find the application version that understands ``revision``.

        Args:
            revision: Alembic revision to look up

        Returns:
            A version string, or None when neither source knows

        """
        catalog = self.metadata_service.get_min_version_for_migration(revision)
        if catalog:
            return str(catalog)
        parsed: list[tuple[Version, str]] = []
        for raw in self.backup_service.application_versions_for(revision):
            try:
                parsed.append((Version(raw), raw))
            except (InvalidVersion, TypeError):
                continue
        return min(parsed)[1] if parsed else None
