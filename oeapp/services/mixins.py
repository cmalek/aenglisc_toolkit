from pathlib import Path
from typing import Final


class ProjectFoldersMixin:
    """Mixin for project folders."""

    #: Path to the project root
    PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent
    #: The config file dir
    ETC_DIR: Final[Path] = PROJECT_ROOT / "oeapp" / "etc"
    #: Path to the Alembic configuration file
    ALEMBIC_INI_PATH: Final[Path] = ETC_DIR / "alembic.ini"
    #: Path to the migration versions file
    MIGRATION_VERSIONS_PATH: Final[Path] = ETC_DIR / "migration_versions.json"
    #: Path to the field mappings file
    FIELD_MAPPINGS_PATH: Final[Path] = ETC_DIR / "field_mappings.json"

    #: Path to the migrations directory
    MIGRATIONS_DIR: Final[Path] = (
        PROJECT_ROOT / "oeapp" / "models" / "alembic" / "versions"
    )
