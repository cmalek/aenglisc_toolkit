"""Parity tests for the POS field catalog."""

import importlib.util
import re
from pathlib import Path

import pytest
from oeapp.models.annotation import Annotation
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.ui.pos_field_catalog import PosFieldCatalog

ALL_POS = ["N", "V", "A", "R", "D", "E", "B", "C", "I", "L", None]
VERSIONS = Path(__file__).resolve().parents[1] / "oeapp/models/alembic/versions"
_IN_CLAUSE = re.compile(r"^\"?(\w+)\"? IN \((.*)\)$")


def _check_codes() -> dict[str, set[str]]:
    """Return {column: allowed codes} parsed from the Annotation CHECKs."""
    allowed: dict[str, set[str]] = {}
    for constraint in Annotation.__table__.constraints:
        sqltext = getattr(constraint, "sqltext", None)
        match = _IN_CLAUSE.match(str(sqltext)) if sqltext is not None else None
        if match:
            allowed[match.group(1)] = set(re.findall(r"'([^']+)'", match.group(2)))
    return allowed


def test_check_parser_finds_known_columns():
    parsed = _check_codes()
    assert {"declension", "verb_class", "case"} <= set(parsed)


def test_noun_fields_in_canonical_order():
    attrs = [f.attr for f in PosFieldCatalog.fields("N")]
    assert attrs == ["gender", "number", "case", "declension"]


def test_verb_uses_modal_labels_and_order():
    fields = PosFieldCatalog.fields("V")
    assert [f.label for f in fields] == [
        "Class",
        "Tense",
        "Mood",
        "Person",
        "Number",
        "Aspect",
        "Direct Object Case",
        "Form",
        "Requires Infinitive",
        "Impersonal",
        "Transitivity",
    ]


def test_declension_and_verb_class_opt_out_of_clear():
    by_attr = {
        f.attr: f for f in PosFieldCatalog.fields("N") + PosFieldCatalog.fields("V")
    }
    assert by_attr["declension"].preset_clear_mode is False
    assert by_attr["verb_class"].preset_clear_mode is False
    assert by_attr["gender"].preset_clear_mode is True


def test_field_less_and_unknown_pos_have_no_fields():
    for pos in ("I", "L", None, "Z"):
        assert PosFieldCatalog.fields(pos) == ()


def test_preset_supported_is_exactly_nvard():
    supported = {pos for pos in ALL_POS if PosFieldCatalog.preset_supported(pos)}
    assert supported == {"N", "V", "A", "R", "D"}
    assert frozenset({"N", "V", "A", "R", "D"}) == PosFieldCatalog.PRESET_POS


@pytest.mark.parametrize("pos", ALL_POS)
def test_every_attr_is_an_annotation_column(pos):
    columns = {c.name for c in Annotation.__table__.columns}
    for field in PosFieldCatalog.fields(pos):
        assert field.attr in columns, field.attr


@pytest.mark.parametrize("pos", ["N", "V", "A", "R", "D"])
def test_preset_supported_attrs_are_preset_columns(pos):
    columns = {c.name for c in AnnotationPreset.__table__.columns}
    for field in PosFieldCatalog.fields(pos):
        assert field.attr in columns, field.attr


#: Codes the database CHECK allows but the UI has no label for. Verified on
#: 2026-10-02: `verb_aspect` allows 'f' but VERB_ASPECT_MAP has no entry; no row in
#: the maintainer's database uses it. Decision: 'f' is dropped from the CHECK by the
#: CHECK-drift backlog card (https://trello.com/c/JnHO9Fx8); delete this entry when
#: that lands.
KNOWN_UNLABELLED = {"verb_aspect": {"f"}}


@pytest.mark.parametrize("pos", ALL_POS)
def test_lookup_map_codes_match_check_constraints(pos):
    allowed = _check_codes()
    for field in PosFieldCatalog.fields(pos):
        if field.attr not in allowed:
            continue
        codes = {k for k in field.lookup_map if k is not None}
        # The harmful direction: the UI offering a code the database rejects.
        assert codes <= allowed[field.attr], field.attr
        # The benign direction: only the documented exceptions may be unlabelled.
        unlabelled = allowed[field.attr] - codes
        assert unlabelled == KNOWN_UNLABELLED.get(field.attr, set()), field.attr


def test_preset_check_codes_match_migration_valid_codes():
    path = next(VERSIONS.glob("7cd945e38aff_*.py"))
    spec = importlib.util.spec_from_file_location("pos_codes_revision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for column in ("declension", "verb_class"):
        presets: set[str] = set()
        for constraint in AnnotationPreset.__table__.constraints:
            text = str(getattr(constraint, "sqltext", ""))
            match = _IN_CLAUSE.match(text)
            if match and match.group(1) == column:
                presets = set(re.findall(r"'([^']+)'", match.group(2)))
        assert presets, column
        assert presets == set(module._VALID_CODES[column]), column
