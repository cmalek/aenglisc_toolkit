"""SQLAlchemy database setup for Ænglisc Toolkit."""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

if TYPE_CHECKING:
    import sqlite3

from oeapp.utils import get_app_data_path

#: The default database name.
DEFAULT_DB_NAME: Final[str] = "default.db"

#: SQLite environment variable names.
ENV_SQLITE_SYNCHRONOUS: Final[str] = "OE_SQLITE_SYNCHRONOUS"
ENV_SQLITE_CACHE_SIZE_KIB: Final[str] = "OE_SQLITE_CACHE_SIZE_KIB"
ENV_SQLITE_MMAP_SIZE_MB: Final[str] = "OE_SQLITE_MMAP_SIZE_MB"
ENV_SQLITE_BUSY_TIMEOUT_MS: Final[str] = "OE_SQLITE_BUSY_TIMEOUT_MS"
ENV_SQLITE_TEMP_STORE: Final[str] = "OE_SQLITE_TEMP_STORE"
ENV_SQLITE_WAL_AUTOCHECKPOINT_PAGES: Final[str] = "OE_SQLITE_WAL_AUTOCHECKPOINT_PAGES"

#: Default SQLite PRAGMA tuning values.
DEFAULT_SQLITE_SYNCHRONOUS: Final[str] = "NORMAL"
DEFAULT_SQLITE_CACHE_SIZE_KIB: Final[int] = 16384
DEFAULT_SQLITE_MMAP_SIZE_MB: Final[int] = 128
DEFAULT_SQLITE_BUSY_TIMEOUT_MS: Final[int] = 10000
DEFAULT_SQLITE_TEMP_STORE: Final[str] = "MEMORY"
DEFAULT_SQLITE_WAL_AUTOCHECKPOINT_PAGES: Final[int] = 2000

_LOGGER = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def _parse_env_int(name: str, default: int, minimum: int = 0) -> int:
    """Parse an integer environment variable with safe fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        _LOGGER.warning(
            "Invalid SQLite integer env var; using default",
            extra={"env_var": name},
        )
        return default
    if value < minimum:
        _LOGGER.warning(
            "SQLite integer env var below minimum; using default",
            extra={"env_var": name, "minimum": minimum},
        )
        return default
    return value


def _parse_env_choice(name: str, default: str, allowed_values: set[str]) -> str:
    """Parse a constrained string environment variable with safe fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().upper()
    if value not in allowed_values:
        _LOGGER.warning(
            "Invalid SQLite enum env var; using default",
            extra={"env_var": name, "allowed_values": sorted(allowed_values)},
        )
        return default
    return value


def _sqlite_pragma_settings() -> dict[str, str | int]:
    """Build SQLite PRAGMA settings from defaults and optional env overrides."""
    synchronous = _parse_env_choice(
        ENV_SQLITE_SYNCHRONOUS,
        DEFAULT_SQLITE_SYNCHRONOUS,
        {"OFF", "NORMAL", "FULL", "EXTRA"},
    )
    cache_size_kib = _parse_env_int(
        ENV_SQLITE_CACHE_SIZE_KIB, DEFAULT_SQLITE_CACHE_SIZE_KIB, minimum=1
    )
    mmap_size_mb = _parse_env_int(
        ENV_SQLITE_MMAP_SIZE_MB, DEFAULT_SQLITE_MMAP_SIZE_MB, minimum=0
    )
    busy_timeout_ms = _parse_env_int(
        ENV_SQLITE_BUSY_TIMEOUT_MS, DEFAULT_SQLITE_BUSY_TIMEOUT_MS, minimum=0
    )
    temp_store = _parse_env_choice(
        ENV_SQLITE_TEMP_STORE,
        DEFAULT_SQLITE_TEMP_STORE,
        {"DEFAULT", "FILE", "MEMORY"},
    )
    wal_autocheckpoint = _parse_env_int(
        ENV_SQLITE_WAL_AUTOCHECKPOINT_PAGES,
        DEFAULT_SQLITE_WAL_AUTOCHECKPOINT_PAGES,
        minimum=1,
    )

    return {
        "foreign_keys": "ON",
        "journal_mode": "WAL",
        "synchronous": synchronous,
        # Negative cache_size value is KiB in SQLite.
        "cache_size": -cache_size_kib,
        "mmap_size": mmap_size_mb * 1024 * 1024,
        "busy_timeout": busy_timeout_ms,
        "temp_store": temp_store,
        "wal_autocheckpoint": wal_autocheckpoint,
    }


def get_project_db_path() -> Path:
    """
    Get the path to the project database.

    - If OE_ANNOTATOR_DB_PATH environment variable is set, use that.
    - Otherwise, use the "projects" subdirectory in the app data path.

    Returns:
        Path to the database file

    """
    env_path = os.environ.get("OE_ANNOTATOR_DB_PATH")
    if env_path:
        return Path(env_path)

    db_path = get_app_data_path() / "projects"
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

    # Apply SQLite performance and safety pragmas on each connection.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_conn: "sqlite3.Connection | Any", _connection_record: Any
    ) -> None:
        """Set SQLite pragmas on connection."""
        cursor = cast("sqlite3.Cursor", dbapi_conn.cursor())
        for pragma, value in _sqlite_pragma_settings().items():
            cursor.execute(f"PRAGMA {pragma}={value}")
        cursor.close()

    return engine


# Create default engine and session factory
_engine = create_engine_with_path()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def run_pragma_optimize(engine: Engine | None = None) -> bool:
    """
    Run ``PRAGMA optimize`` as a lightweight best-effort maintenance operation.

    Args:
        engine: Optional SQLAlchemy engine. Defaults to the shared app engine.

    Returns:
        True when optimize executes successfully, False otherwise.

    """
    target_engine = _engine if engine is None else engine
    try:
        with target_engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA optimize")
            conn.commit()
    except Exception:
        _LOGGER.exception("sqlite.optimize.failed")
        return False
    return True


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


def table_to_model_name(table_name: str) -> str:
    """
    Convert table name to model name.

    Args:
        table_name: Database table name

    Returns:
        Model name

    """
    # Simple mapping: plural table names to singular model names
    # This is a basic implementation - may need refinement
    if table_name.endswith("s"):
        return table_name[:-1].capitalize()
    return table_name.capitalize()
