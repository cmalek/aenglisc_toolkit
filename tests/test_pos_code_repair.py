"""Tests for PosCodeRepair and the import-time values remap."""

import importlib.util
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oeapp.services.import_export import ProjectImporter
from oeapp.services.pos_code_repair import PosCodeRepair

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "oeapp/models/alembic/versions").glob(
        "*_repair_declension_and_verb_class_codes.py"
    )
)
FIELD_MAPPINGS = ROOT / "oeapp/etc/field_mappings.json"


def _migration():
    spec = importlib.util.spec_from_file_location("repair_codes_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _revision() -> str:
    return re.search(
        r'^revision: str = ["\']([^"\']+)["\']', MIGRATION.read_text(), re.M
    ).group(1)


def _repairers() -> dict[str, PosCodeRepair]:
    values = json.loads(FIELD_MAPPINGS.read_text())[_revision()]["values"]
    return {attr: PosCodeRepair.from_mapping(spec) for attr, spec in values.items()}


def _importer() -> ProjectImporter:
    return ProjectImporter(migration_service=MagicMock())


def test_from_mapping_rejects_malformed_specs():
    for bad in (
        {},
        {"codes": ["s"]},
        {"codes": "s", "labels": {}},
        {"codes": ["s"], "labels": []},
    ):
        with pytest.raises(ValueError, match="Malformed"):
            PosCodeRepair.from_mapping(bad)


def test_json_tables_equal_the_frozen_migration_tables():
    migration = _migration()
    values = json.loads(FIELD_MAPPINGS.read_text())[_revision()]["values"]
    for column in ("declension", "verb_class"):
        assert set(values[column]["codes"]) == set(migration._VALID_CODES[column])
        assert values[column]["labels"] == migration._LABELS[column]


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("declension", "Strong (s)"),
        ("declension", " weak (w) "),
        ("declension", "-nd nouns(nd)"),
        ("declension", ""),
        ("declension", "s"),
        ("declension", "unknown text"),
        ("verb_class", "Anomolous (a)"),
        ("verb_class", "Strong Class 2 (s2)"),
        ("verb_class", "Strong Class 9"),
        ("verb_class", "pp"),
    ],
)
def test_runtime_repair_agrees_with_the_migration(column, value):
    assert _repairers()[column].repair(value) == _migration()._repair(column, value)


def test_old_export_label_values_import_as_codes():
    importer = _importer()
    data = {
        "presets": [{"pos": "N", "declension": "Strong (s)", "gender": "m"}],
        "annotations": [
            {"declension": "Strong (s)", "verb_class": "Preterite-Present (pp)"}
        ],
    }
    mappings = {"rev1": json.loads(FIELD_MAPPINGS.read_text())[_revision()]}
    with patch.object(importer, "_load_field_mappings", return_value=mappings):
        result = importer._apply_field_mappings(data, ["rev1"])
    assert result["presets"][0] == {"pos": "N", "declension": "s", "gender": "m"}
    assert result["annotations"][0] == {"declension": "s", "verb_class": "pp"}


def test_unmatched_and_non_string_values_pass_through():
    importer = _importer()
    data = {
        "a": {"declension": "free text", "verb_class": None},
        "b": [{"declension": 5}],
    }
    mappings = {"rev1": json.loads(FIELD_MAPPINGS.read_text())[_revision()]}
    with patch.object(importer, "_load_field_mappings", return_value=mappings):
        result = importer._apply_field_mappings(data, ["rev1"])
    assert result["a"] == {"declension": "free text", "verb_class": None}
    assert result["b"] == [{"declension": 5}]


def test_malformed_values_section_raises_and_is_not_swallowed():
    importer = _importer()
    importer.migration_service.code_migration_version.return_value = "v2"
    importer.migration_service.revision_chain.return_value = ["rev1"]
    mappings = {"rev1": {"values": {"declension": {"codes": "s"}}}}
    with patch.object(importer, "_load_field_mappings", return_value=mappings):
        with pytest.raises(ValueError, match="Malformed"):
            importer._transform_data({"x": {"declension": "s"}}, "v1")


def test_rename_mappings_still_work_alongside_values():
    importer = _importer()
    mappings = {"rev1": {"Project": {"old": "new"}, "values": {}}}
    with patch.object(importer, "_load_field_mappings", return_value=mappings):
        result = importer._apply_field_mappings({"p": {"old": 1}}, ["rev1"])
    assert result == {"p": {"new": 1}}
