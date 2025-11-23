#!/usr/bin/env python3
"""Alembic wrapper that creates migrations and updates version/mapping files."""

import sys

from oeapp.exc import MigrationCreationFailed
from oeapp.services import FieldMappingService, MigrationService


def main() -> None:
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: create_migration.py <message>", file=sys.stderr)
        print("Example: create_migration.py 'Add new field'", file=sys.stderr)
        sys.exit(1)

    message = sys.argv[1]
    migration_service = MigrationService()

    # Run alembic revision
    try:
        migration_result = migration_service.create(message)
    except MigrationCreationFailed as e:
        print(f"Failed to create migration: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Created migration file: {migration_result.migration_file_path} with revision ID: {migration_result.revision_id}"  # noqa: E501
    )

    # Detect field renames
    print("Detecting field renames...")
    field_mapping_service = FieldMappingService()
    field_mapping_service.update(migration_result.migration_file_path)
    print("Migration creation complete!")


if __name__ == "__main__":
    main()
