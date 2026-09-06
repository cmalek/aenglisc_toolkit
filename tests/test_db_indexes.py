"""Tests for SQLite index presence on fresh and upgraded schemas."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from oeapp.db import Base, create_engine_with_path

EXPECTED_PERF_INDEXES = {
    "idx_annotations_idiom_id",
    "idx_annotations_token_id",
    "idx_chapters_project_number",
    "idx_idioms_sentence_token_span",
    "idx_notes_sentence",
    "idx_paragraphs_section_order",
    "idx_sections_chapter_number",
    "idx_sentences_paragraph_order",
}


def _alembic_config() -> Config:
    """Return Alembic config pointing at project alembic.ini."""
    project_root = Path(__file__).resolve().parents[1]
    return Config(str(project_root / "oeapp" / "etc" / "alembic.ini"))


def _fetch_indexes(db_path: Path) -> set[str]:
    """Fetch explicit index names from sqlite_master."""
    engine = create_engine_with_path(db_path)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
            )
        ).fetchall()
    engine.dispose()
    return {row[0] for row in rows}


class TestFreshSchemaIndexes:
    """Validate index presence for fresh DB creation path."""

    def test_fresh_schema_contains_performance_indexes(self, tmp_path):
        """Fresh create_all schema should include performance indexes."""
        db_path = tmp_path / "fresh_schema.db"
        engine = create_engine_with_path(db_path)
        Base.metadata.create_all(engine)
        engine.dispose()

        index_names = _fetch_indexes(db_path)
        assert EXPECTED_PERF_INDEXES.issubset(index_names)


class TestMigrationUpgradeIndexes:
    """Validate index presence for existing DB migration path."""

    def test_upgrade_adds_performance_indexes(self, tmp_path, monkeypatch):
        """Alembic upgrade from pre-index revision should add expected indexes."""
        db_path = tmp_path / "upgrade_schema.db"

        engine = create_engine_with_path(db_path)
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE chapters (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, number INTEGER NOT NULL)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE sections (id INTEGER PRIMARY KEY, chapter_id INTEGER NOT NULL, number INTEGER NOT NULL)"
            )
            conn.exec_driver_sql(
                'CREATE TABLE paragraphs (id INTEGER PRIMARY KEY, section_id INTEGER NOT NULL, "order" INTEGER NOT NULL)'
            )
            conn.exec_driver_sql(
                "CREATE TABLE sentences (id INTEGER PRIMARY KEY, project_id INTEGER, paragraph_id INTEGER, display_order INTEGER)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE notes (id INTEGER PRIMARY KEY, sentence_id INTEGER, start_token INTEGER)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE idioms (id INTEGER PRIMARY KEY, sentence_id INTEGER, start_token_id INTEGER, end_token_id INTEGER)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE annotations (id INTEGER PRIMARY KEY, token_id INTEGER, idiom_id INTEGER)"
            )
            conn.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
            )
            conn.exec_driver_sql(
                "INSERT INTO alembic_version (version_num) VALUES ('4fa091868838')"
            )
            conn.commit()
        engine.dispose()

        monkeypatch.setenv("AENGLISC_TOOLKIT_DB_PATH", str(db_path))
        command.upgrade(_alembic_config(), "head")

        index_names = _fetch_indexes(db_path)
        assert EXPECTED_PERF_INDEXES.issubset(index_names)
