"""Tests for the declension/verb_class repair revision."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

VERSIONS = Path(__file__).resolve().parents[1] / "oeapp/models/alembic/versions"


def _load():
    path = next(VERSIONS.glob("*_repair_declension_and_verb_class_codes.py"))
    spec = importlib.util.spec_from_file_location("repair_codes_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _upgrade(engine):
    module = _load()
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()


@pytest.fixture
def engine(tmp_path):
    eng = sa.create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    with eng.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE annotation_presets (id INTEGER PRIMARY KEY, "
            "pos VARCHAR NOT NULL, declension VARCHAR, verb_class VARCHAR, "
            "CONSTRAINT ck_annotation_presets_pos CHECK (pos IN ('N','V','A','R','D')))"
        )
        conn.exec_driver_sql(
            "CREATE TABLE annotations (id INTEGER PRIMARY KEY, "
            "declension VARCHAR, verb_class VARCHAR)"
        )
    return eng


def _column(engine, table, column):
    with engine.connect() as conn:
        return [
            r[0]
            for r in conn.exec_driver_sql(f"SELECT {column} FROM {table} ORDER BY id")
        ]


def _check_names(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_check_constraints(table)}


def test_labels_become_codes_in_presets_and_annotations(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO annotation_presets (pos, declension, verb_class) VALUES "
            "('N','Strong (s)',NULL),('V',NULL,'Preterite-Present (pp)'),('N','w',NULL)"
        )
        conn.exec_driver_sql(
            "INSERT INTO annotations (declension, verb_class) VALUES "
            "('Strong (s)','Strong Class 1 (s1)'),('',NULL),('i-mut',NULL)"
        )
    _upgrade(engine)
    assert _column(engine, "annotation_presets", "declension") == ["s", None, "w"]
    assert _column(engine, "annotation_presets", "verb_class") == [None, "pp", None]
    assert _column(engine, "annotations", "declension") == ["s", None, "i-mut"]
    assert _column(engine, "annotations", "verb_class") == ["s1", None, None]


def test_checks_added_and_existing_check_kept_when_clean(engine):
    _upgrade(engine)
    names = _check_names(engine, "annotation_presets")
    assert {
        "ck_annotation_presets_declension",
        "ck_annotation_presets_verb_class",
        "ck_annotation_presets_pos",
    } <= names
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO annotation_presets (pos, declension) VALUES ('N','bogus')"
        )


def test_unmatched_value_is_kept_and_checks_are_skipped(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO annotation_presets (pos, declension) VALUES ('N','totally unknown')"
        )
    _upgrade(engine)
    assert _column(engine, "annotation_presets", "declension") == ["totally unknown"]
    names = _check_names(engine, "annotation_presets")
    assert "ck_annotation_presets_declension" not in names
    assert "ck_annotation_presets_pos" in names


def test_upgrade_is_idempotent(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO annotation_presets (pos, declension) VALUES ('N','Weak (w)')"
        )
    _upgrade(engine)
    _upgrade(engine)
    assert _column(engine, "annotation_presets", "declension") == ["w"]


def test_missing_presets_table_is_a_noop(tmp_path):
    eng = sa.create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    _upgrade(eng)


@pytest.mark.parametrize(
    ("column", "value", "expected"),
    [
        ("declension", "Strong (s)", "s"),
        ("declension", "  strong (s) ", "s"),
        ("declension", "-nd nouns(nd)", "nd"),
        ("declension", "er nouns (children) (er)", "er"),
        ("verb_class", "Anomolous (a)", "a"),
        ("verb_class", "Strong Class 2 (s2)", "s2"),
        ("verb_class", "pp", "pp"),
        ("verb_class", "", None),
        ("verb_class", "Strong Class 9", "Strong Class 9"),
    ],
)
def test_repair_tiers(column, value, expected):
    assert _load()._repair(column, value) == expected
