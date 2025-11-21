"""SQLAlchemy database setup for Old English Annotator."""

import sys
from pathlib import Path
from typing import Final

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

#: The default database name.
DEFAULT_DB_NAME: Final[str] = "default.db"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_project_db_path() -> Path:
    """
    Get the path to the project database.

    - On Windows, the database is created in the user's
        ``AppData/Local/oe_annotator/projects`` directory.
    - On macOS, the database is created in the user's
        ``~/Library/Application Support/oe_annotator/projects`` directory.
    - On Linux, the database is created in the user's
        ``~/.config/oe_annotator/projects`` directory.
    - If the platform is not supported, raise a ValueError.

    Returns:
        Path to the database file

    """
    if sys.platform not in ["win32", "darwin", "linux"]:
        msg = f"Unsupported platform: {sys.platform}"
        raise ValueError(msg)
    if sys.platform == "win32":
        db_path = Path.home() / "AppData" / "Local" / "oe_annotator" / "projects"
    elif sys.platform == "darwin":
        db_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "oe_annotator"
            / "projects"
        )
    elif sys.platform == "linux":
        db_path = Path.home() / ".config" / "oe_annotator" / "projects"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path / DEFAULT_DB_NAME


def create_engine_with_path(db_path: Path | None = None) -> Engine:
    """
    Create SQLAlchemy engine with proper SQLite settings.

    Args:
        db_path: Optional path to database file. If None, uses default path.

    Returns:
        SQLAlchemy engine

    """
    if db_path is None:
        db_path = get_project_db_path()

    # Create the file if it doesn't exist
    db_path.touch(exist_ok=True)

    # Create engine with SQLite-specific settings
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        echo=False,  # Set to True for SQL debugging
    )

    # Enable foreign keys and WAL mode
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas on connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


# Create default engine and session factory
_engine = create_engine_with_path()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_session():
    """
    Get a database session.

    Yields:
        SQLAlchemy session

    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def apply_migrations() -> None:
    """
    Apply pending Alembic migrations.

    This should be called on application startup.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text  # noqa: F401

    # Check if database is fresh (no alembic_version table)
    inspector = inspect(_engine)
    existing_tables = inspector.get_table_names()

    if "alembic_version" not in existing_tables:
        # Fresh database - create tables from models
        Base.metadata.create_all(_engine)
        # Create alembic_version table and mark initial migration as applied
        with _engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO alembic_version (version_num) VALUES ('57399ca978ee')"
                )
            )
            conn.commit()
    else:
        # Existing database - apply migrations normally
        from pathlib import Path

        # Get path to alembic.ini in oeapp/etc/
        alembic_ini_path = Path(__file__).parent / "etc" / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
