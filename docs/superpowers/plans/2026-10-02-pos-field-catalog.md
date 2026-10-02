# POS Field Catalog (F2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three hand-maintained copies of each part of speech's annotation fields (annotation modal, preset dialog, token-details sidebar) with one UI-only catalog, and repair the label-form `declension`/`verb_class` values the preset dialog has been writing.

**Architecture:** A new data-only module `oeapp/ui/pos_field_catalog.py` defines, per one-letter POS code, an ordered tuple of `PosField` (attr, canonical label, lookup map, clear-mode flag) plus a `preset_supported` flag. The modal's `*Fields.build()`, the preset dialog's field groups, and the sidebar's `*Renderer.render()` all iterate it. A hand-written Alembic revision repairs stored values and adds `CHECK`s to `annotation_presets`; JSON import gets a per-revision `values` remap that reuses one small repair class.

**Tech Stack:** Python 3.13, PySide6, SQLAlchemy 2.1, Alembic 1.20 (SQLite, batch mode), pytest, ruff, mypy.

**Spec:** `doc/source/architecture/adr_0005_pos_field_catalog.rst` (ADR 0005, Proposed). Intake: Trello card 102 (F2).

**Deviation from the grilling:** the ADR/grill said "commit Noun, then Verb, then the rest". This plan commits **surface by surface** (modal, preset, sidebar) instead, because the catalog is one data file and each surface consumes every POS through one generic loop; POS-by-POS would need a dual code path (old and new) inside every surface. All parts of speech are still migrated.

## Global Constraints

- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. Change directory only with `/usr/bin/cd`.
- Qt widgets stay in `oeapp.ui`; models in `oeapp.models`; the catalog is data only, no Qt types, no form framework.
- Do not add a third-party form library.
- Any SQLAlchemy model change needs an Alembic revision created with `bin/create_migration.py`.
- Functions and methods are at most 60 lines. Use constructor injection; no monkey-patching or runtime workarounds.
- Docstring contract (non-test code): brief description plus only the applicable `Args:`, `Keyword Args:`, `Raises:`, `Returns:`/`Yields:`, `Side Effects:` sections; `#:` comments on class attributes, `__init__` instance attributes and module-level globals.
- On ORM models that define a `list()` classmethod, annotate with `builtins.list[...]`, not bare `list[...]`.
- Canonical labels come from the annotation modal today (for example `Class`, `Type`, `Degree`, `Governed Case`); renderers add punctuation. The sidebar shows `?` for any unset or unrecognised value.
- Per-task gate before every commit: `.venv/bin/ruff check <touched>`, `.venv/bin/mypy <touched>`, and the task's pytest files. Run `.venv/bin/ruff format --check` only on files this plan **creates**; `oeapp/ui/token_details_sidebar.py` already fails it (a pre-existing drift around `dict_button.palette()`), so do not reformat existing files wholesale. `tests/` and `alembic/` are excluded from `ruff check` by `pyproject.toml`. `make napoleon-gate` is known-unusable (its baseline is keyed by line number and it always fails): run it once in the last task and report the result, do not block on it.
- Commit messages are lower-case conventional (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`) and end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Tasks 3 and 5 must ship in the same release: Task 3 stops the preset dialog writing labels, Task 5 repairs the rows already written.

## Review Focus

1. A preset row still holding a label-form value (`"Strong (s)"`) when the preset dialog loads it after Task 3 but before the migration runs: must show a blank combo, never crash (pinned in Task 3).
2. A preset that stores the clear sentinel for an ordinary field (for example gender `"__CLEAR__"`) must still round-trip to the "Clear" choice after the refactor (Task 3).
3. A saved annotation with an unset field, or a code the map does not know, must render `?` in the sidebar and not raise (Task 4); the sidebar header, DOCX export and propagation, which call `format_pos`, must not raise either (Task 4b).
4. The migration run against a database with no `annotation_presets` table, or run a second time, must be a harmless no-op (Task 5).
5. A pre-change JSON export containing label-form `declension`/`verb_class` (including on annotations, as in the maintainer's real data) must import as codes, and a malformed `values` section must raise, not be swallowed by `_transform_data` (Task 6).

---

## File Structure

| File | Responsibility |
|---|---|
| `oeapp/ui/pos_field_catalog.py` (create) | `PosField`, `PosFieldCatalog`: which fields each POS has, label, order, map, clear-mode, preset coverage |
| `oeapp/ui/dialogs/pos_form_system.py` (modify) | Modal field groups and preset field groups build from the catalog; remove `PosFieldSpec`, `FIELD_SPECS`, per-class `build()`, preset boolean maps |
| `oeapp/ui/dialogs/annotation_preset_management.py` (modify) | Remove dead `_set_combo_value`/`_extract_combo_value` helpers |
| `oeapp/mixins.py` (modify) | `AnnotationTextualMixin._label`: `format_pos/gender/context` fall back to stored text for unknown codes |
| `oeapp/ui/token_details_sidebar.py` (modify) | Generic `_render_fields()` driven by the catalog; delete per-POS `render()` bodies |
| `oeapp/models/annotation_preset.py` (modify) | Add `declension`/`verb_class` `CHECK` constraints to `__table_args__` |
| `oeapp/models/alembic/versions/<rev>_repair_declension_and_verb_class_codes.py` (create via script) | Data repair + preset `CHECK`s |
| `oeapp/services/pos_code_repair.py` (create) | `PosCodeRepair`: the tiered code repair used by import |
| `oeapp/services/import_export.py` (modify) | Apply per-revision `values` repairs in `_apply_field_mappings` |
| `oeapp/etc/field_mappings.json` (modify) | Frozen `values` tables for the new revision |
| `tests/test_pos_field_catalog.py` (create) | Catalog parity tests |
| `tests/test_migration_pos_codes.py` (create) | Migration tests |
| `tests/test_pos_code_repair.py` (create) | Repair class + import tests |
| `tests/test_annotation_modal.py`, `tests/test_annotation_preset_management_dialog.py`, `tests/test_token_details_sidebar.py` (modify) | Updated/added tests |
| `doc/source/overview/*.rst`, `oeapp/help/topics/*.md`, regenerated help assets, `doc/source/architecture/adr_0005_*.rst` | Docs, help, ADR status |

---

### Task 1: The catalog module and its parity tests

**Files:**
- Create: `oeapp/ui/pos_field_catalog.py`
- Create: `tests/test_pos_field_catalog.py`

**Interfaces:**
- Produces: `PosField(attr: str, label: str, lookup_map: Mapping[Any, str], preset_clear_mode: bool = True)` (frozen dataclass); `PosFieldCatalog.fields(pos: str | None) -> tuple[PosField, ...]` (empty tuple for unknown or field-less POS); `PosFieldCatalog.preset_supported(pos: str | None) -> bool`; `PosFieldCatalog.PRESET_POS: frozenset[str]`.
- Consumes: the `*_MAP` class attributes on `oeapp.ui.mixins.AnnotationLookupsMixin`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pos_field_catalog.py`:

```python
"""Parity tests for the POS field catalog."""

import re

import pytest

from oeapp.models.annotation import Annotation
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.ui.pos_field_catalog import PosFieldCatalog

ALL_POS = ["N", "V", "A", "R", "D", "E", "B", "C", "I", "L", None]
_IN_CLAUSE = re.compile(r"^(\w+) IN \((.*)\)$")


def _check_codes() -> dict[str, set[str]]:
    """Return {column: allowed codes} parsed from the Annotation CHECKs."""
    allowed: dict[str, set[str]] = {}
    for constraint in Annotation.__table__.constraints:
        sqltext = getattr(constraint, "sqltext", None)
        match = _IN_CLAUSE.match(str(sqltext)) if sqltext is not None else None
        if match:
            allowed[match.group(1)] = set(re.findall(r"'([^']+)'", match.group(2)))
    return allowed


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
    by_attr = {f.attr: f for f in PosFieldCatalog.fields("N") + PosFieldCatalog.fields("V")}
    assert by_attr["declension"].preset_clear_mode is False
    assert by_attr["verb_class"].preset_clear_mode is False
    assert by_attr["gender"].preset_clear_mode is True


def test_field_less_and_unknown_pos_have_no_fields():
    for pos in ("I", "L", None, "Z"):
        assert PosFieldCatalog.fields(pos) == ()


def test_preset_supported_is_exactly_nvard():
    supported = {pos for pos in ALL_POS if PosFieldCatalog.preset_supported(pos)}
    assert supported == {"N", "V", "A", "R", "D"}
    assert PosFieldCatalog.PRESET_POS == frozenset({"N", "V", "A", "R", "D"})


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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_pos_field_catalog.py -v`
Expected: collection FAIL, `ModuleNotFoundError: No module named 'oeapp.ui.pos_field_catalog'`.

- [ ] **Step 3: Write the catalog**

Create `oeapp/ui/pos_field_catalog.py`:

```python
"""Single definition of the annotation fields shown for each part of speech."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final

from oeapp.ui.mixins import AnnotationLookupsMixin as Maps

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class PosField:
    """One annotation field as presented on every surface."""

    #: Annotation column name.
    attr: str
    #: Canonical label, without punctuation.
    label: str
    #: Code-to-label map for the field's combo box.
    lookup_map: Mapping[Any, str]
    #: Whether presets offer an explicit "Clear" choice for this field.
    preset_clear_mode: bool = True


@dataclass(frozen=True)
class _PosEntry:
    """The ordered fields for one part of speech."""

    #: Fields in display order.
    fields: tuple[PosField, ...]


#: Fields shared by several parts of speech.
_GENDER: Final = PosField("gender", "Gender", Maps.GENDER_MAP)
#: Number for non-pronoun parts of speech.
_NUMBER: Final = PosField("number", "Number", Maps.NUMBER_MAP)
#: Grammatical case.
_CASE: Final = PosField("case", "Case", Maps.CASE_MAP)


class PosFieldCatalog:
    """
    Which annotation fields each part of speech has, and how they read.

    The annotation modal, the preset dialog and the token details sidebar all
    iterate this catalog, so a field is added in one place. The catalog holds
    data only; widgets stay in the surfaces that consume it.
    """

    #: Part-of-speech codes the preset dialog supports.
    PRESET_POS: ClassVar[frozenset[str]] = frozenset({"N", "V", "A", "R", "D"})

    #: Entries keyed by one-letter POS code.
    _ENTRIES: ClassVar[dict[str | None, _PosEntry]] = {
        "N": _PosEntry(
            (
                _GENDER,
                _NUMBER,
                _CASE,
                PosField(
                    "declension",
                    "Declension",
                    Maps.DECLENSION_MAP,
                    preset_clear_mode=False,
                ),
            )
        ),
        "V": _PosEntry(
            (
                PosField(
                    "verb_class", "Class", Maps.VERB_CLASS_MAP, preset_clear_mode=False
                ),
                PosField("verb_tense", "Tense", Maps.VERB_TENSE_MAP),
                PosField("verb_mood", "Mood", Maps.VERB_MOOD_MAP),
                PosField("verb_person", "Person", Maps.VERB_PERSON_MAP),
                _NUMBER,
                PosField("verb_aspect", "Aspect", Maps.VERB_ASPECT_MAP),
                PosField(
                    "verb_direct_object_case",
                    "Direct Object Case",
                    Maps.VERB_DIRECT_OBJECT_CASE_MAP,
                ),
                PosField("verb_form", "Form", Maps.VERB_FORM_MAP),
                PosField(
                    "verb_requires_infinitive",
                    "Requires Infinitive",
                    Maps.VERB_BOOLEAN_MAP,
                ),
                PosField("verb_impersonal", "Impersonal", Maps.VERB_BOOLEAN_MAP),
                PosField(
                    "verb_transitivity", "Transitivity", Maps.VERB_TRANSITIVITY_MAP
                ),
            )
        ),
        "A": _PosEntry(
            (
                PosField("adjective_degree", "Degree", Maps.ADJECTIVE_DEGREE_MAP),
                PosField(
                    "adjective_inflection", "Inflection", Maps.ADJECTIVE_INFLECTION_MAP
                ),
                _GENDER,
                _NUMBER,
                _CASE,
            )
        ),
        "R": _PosEntry(
            (
                PosField("pronoun_type", "Type", Maps.PRONOUN_TYPE_MAP),
                _GENDER,
                PosField("pronoun_number", "Number", Maps.PRONOUN_NUMBER_MAP),
                _CASE,
            )
        ),
        "D": _PosEntry(
            (
                PosField("article_type", "Type", Maps.ARTICLE_TYPE_MAP),
                _GENDER,
                _NUMBER,
                _CASE,
            )
        ),
        "E": _PosEntry(
            (PosField("prep_case", "Governed Case", Maps.PREPOSITION_CASE_MAP),)
        ),
        "B": _PosEntry(
            (PosField("adverb_degree", "Degree", Maps.ADVERB_DEGREE_MAP),)
        ),
        "C": _PosEntry(
            (PosField("conjunction_type", "Type", Maps.CONJUNCTION_TYPE_MAP),)
        ),
    }

    @classmethod
    def fields(cls, pos: str | None) -> tuple[PosField, ...]:
        """
        Return the ordered fields for a part of speech.

        Args:
            pos: One-letter POS code, or ``None`` for the empty POS state.

        Returns:
            The fields in display order; empty for field-less or unknown POS.

        """
        entry = cls._ENTRIES.get(pos)
        return entry.fields if entry else ()

    @classmethod
    def preset_supported(cls, pos: str | None) -> bool:
        """
        Return whether the preset dialog supports a part of speech.

        Args:
            pos: One-letter POS code, or ``None``.

        Returns:
            ``True`` for N, V, A, R and D.

        """
        return pos in cls.PRESET_POS
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_pos_field_catalog.py -v`
Expected: all PASS. The one mismatch known today (`verb_aspect` CHECK allows `'f'`, the map has no label for it) is recorded in `KNOWN_UNLABELLED`. If `test_lookup_map_codes_match_check_constraints` fails for any *other* field, **stop and report it to the user**: it is a real defect, not a test to loosen.

- [ ] **Step 5: Gate and commit**

Run: `.venv/bin/ruff check oeapp/ui/pos_field_catalog.py tests/test_pos_field_catalog.py && .venv/bin/ruff format --check oeapp/ui/pos_field_catalog.py tests/test_pos_field_catalog.py && .venv/bin/mypy oeapp/ui/pos_field_catalog.py`

```bash
git add oeapp/ui/pos_field_catalog.py tests/test_pos_field_catalog.py
git commit -m "feat: add POS field catalog with parity tests" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Annotation modal builds from the catalog

**Files:**
- Modify: `oeapp/ui/dialogs/pos_form_system.py` (the `PartOfSpeechFieldsBase` class and every `*Fields` subclass, roughly lines 47-423)
- Modify: `tests/test_annotation_modal.py:147-148`
- Test: `tests/test_annotation_modal.py`

**Interfaces:**
- Consumes: `PosFieldCatalog.fields(pos)` from Task 1.
- Produces: `PartOfSpeechFieldsBase.POS_CODE: str | None`; a default `build()` that adds one combo per catalog field. Class names (`NounFields`, `VerbFields`, ...) and `AnnotationPosFormManager.PARTS_OF_SPEECH` are unchanged.

- [ ] **Step 1: Write the failing tests**

In `tests/test_annotation_modal.py`, add to the imports `from oeapp.ui.pos_field_catalog import PosFieldCatalog`, and add this class next to `TestPOSFieldModelMapping`:

```python
class TestModalBuildsFromCatalog:
    """The modal field groups are driven by the POS field catalog."""

    @pytest.mark.parametrize(
        "cls",
        [
            NounFields, VerbFields, PronounFields, PrepositionFields,
            AdjectiveFields, ArticleFields, AdverbFields, ConjunctionFields,
            InterjectionFields, NoneFields,
        ],
    )
    def test_built_fields_match_catalog(self, qapp, cls):
        parent = QWidget()
        fields_obj = cls(QFormLayout(parent), parent)
        fields_obj.build()
        expected = [f.attr for f in PosFieldCatalog.fields(cls.POS_CODE)]
        assert list(fields_obj.fields) == expected

    def test_preterite_present_class_sets_requires_infinitive(self, qapp):
        parent = QWidget()
        fields_obj = VerbFields(QFormLayout(parent), parent)
        fields_obj.build()
        class_combo = fields_obj.fields["verb_class"]
        class_combo.setCurrentIndex(fields_obj.code_to_index_map["verb_class"]["pp"])
        assert fields_obj.extract_values()["verb_requires_infinitive"] is True
```

Also change lines 147-148 of the same file from `VerbFields.VERB_REQUIRES_INF_MAP` / `VerbFields.VERB_IMPERSONAL_MAP` to `VerbFields.VERB_BOOLEAN_MAP` for both.

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_annotation_modal.py -k "Catalog or TestPOSFieldModelMapping" -v`
Expected: FAIL with `AttributeError: type object 'NounFields' has no attribute 'POS_CODE'`.

- [ ] **Step 3: Implement**

In `oeapp/ui/dialogs/pos_form_system.py` add `from oeapp.ui.pos_field_catalog import PosFieldCatalog` to the imports.

Replace `PartOfSpeechFieldsBase.PART_OF_SPEECH` and `build()` with:

```python
    #: The Part of Speech Name
    PART_OF_SPEECH: str
    #: One-letter POS code used to look fields up in the POS field catalog.
    POS_CODE: str | None = None
```

```python
    def build(self) -> None:
        """Build one combo per field in the POS field catalog."""
        for field in PosFieldCatalog.fields(self.POS_CODE):
            self.add_combo(field.attr, field.label, field.lookup_map)
```

Rewrite each subclass to set only `PART_OF_SPEECH` and `POS_CODE`, deleting its `build()`; keep only `VerbFields`' extras:

```python
class NounFields(PartOfSpeechFieldsBase):
    """Fields for noun annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Noun"
    #: Catalog code.
    POS_CODE = "N"


class VerbFields(PartOfSpeechFieldsBase):
    """Fields for verb annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Verb"
    #: Catalog code.
    POS_CODE = "V"

    def build(self) -> None:
        """Build the verb fields and wire the class-change rule."""
        super().build()
        self.fields["verb_class"].currentIndexChanged.connect(self._on_class_changed)

    # _on_class_changed stays exactly as it is today.
```

Delete `VERB_REQUIRES_INF_MAP` and `VERB_IMPERSONAL_MAP` from `VerbFields`. Apply the same two-attribute pattern to the rest with these codes: `PronounFields "R"`, `PrepositionFields "E"`, `AdjectiveFields "A"`, `ArticleFields "D"`, `AdverbFields "B"`, `ConjunctionFields "C"`, `InterjectionFields "I"`, `NumberFields "L"`, `NoneFields None` (leave `POS_CODE = None`; remove their `build()` overrides).

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_annotation_modal.py tests/test_pos_field_catalog.py -v`
Expected: all PASS (including the pre-existing `TestPOSFieldModelMapping`).

- [ ] **Step 5: Gate and commit**

Run: `.venv/bin/ruff check oeapp/ui/dialogs/pos_form_system.py tests/test_annotation_modal.py && .venv/bin/ruff format --check oeapp/ui/dialogs/pos_form_system.py && .venv/bin/mypy oeapp/ui/dialogs/pos_form_system.py && .venv/bin/pytest tests/test_annotation_modal.py -q`

```bash
git add oeapp/ui/dialogs/pos_form_system.py tests/test_annotation_modal.py
git commit -m "refactor: annotation modal builds POS fields from the catalog" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Preset dialog builds from the catalog; presets store codes

**Files:**
- Modify: `oeapp/ui/dialogs/pos_form_system.py` (the `PosFieldSpec` dataclass, `PresetPartOfSpeechFieldsBase`, the five `Preset*Fields` classes and `PresetPosFormManager`)
- Modify: `oeapp/ui/dialogs/annotation_preset_management.py` (remove dead helpers around lines 656-700)
- Modify: `tests/test_annotation_preset_management_dialog.py` (delete the two `_set_combo_value` tests at ~167 and ~214)
- Test: `tests/test_pos_form_system_presets.py` (create)

**Interfaces:**
- Consumes: `PosFieldCatalog.fields(code)` and `PosField` from Task 1.
- Produces: `PresetPartOfSpeechFieldsBase(layout: QFormLayout, parent_widget: QWidget, pos: str)` (now takes the POS code and is used directly); `_add_field(field: PosField)`; preset combos named `f"{pos.lower()}_{attr}_combo"` (for example `n_gender_combo`); `declension`/`verb_class` become fixed code-mapped combos with no "Clear" item. `PosFieldSpec`, every `FIELD_SPECS`, the five `Preset{Noun,Verb,Adjective,Pronoun,Article}Fields` subclasses and `PresetPosFormManager.POS_FIELD_CLASSES` are removed: supported parts of speech come from `PosFieldCatalog.preset_supported(pos)` (nothing outside `pos_form_system.py` references those subclasses; verified by grep).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pos_form_system_presets.py`:

```python
"""Preset POS form behaviour after the catalog refactor."""

import pytest
from PySide6.QtWidgets import QFormLayout, QWidget

from oeapp.ui.dialogs.pos_form_system import (
    CLEAR_SENTINEL,
    PresetPartOfSpeechFieldsBase,
    PresetPosFormManager,
)


def _build(pos):
    parent = QWidget()
    fields = PresetPartOfSpeechFieldsBase(QFormLayout(parent), parent, pos)
    fields.build()
    return parent, fields


def test_declension_extracts_the_code_not_the_label(qapp):
    _parent, fields = _build("N")
    combo = fields.fields["declension"]
    combo.setCurrentIndex(combo.findText("Strong (s)"))
    assert fields.extract_values()["declension"] == "s"


def test_verb_class_round_trips_the_code(qapp):
    _parent, fields = _build("V")
    fields.load_from_values({"verb_class": "pp"})
    assert fields.fields["verb_class"].currentText() == "Preterite-Present (pp)"
    assert fields.extract_values()["verb_class"] == "pp"


def test_declension_and_verb_class_have_no_clear_choice(qapp):
    _p, noun = _build("N")
    _p2, verb = _build("V")
    assert noun.fields["declension"].findText("Clear") == -1
    assert verb.fields["verb_class"].findText("Clear") == -1


def test_ordinary_field_still_round_trips_the_clear_sentinel(qapp):
    _parent, fields = _build("N")
    fields.load_from_values({"gender": CLEAR_SENTINEL})
    assert fields.fields["gender"].currentText() == "Clear"
    assert fields.extract_values()["gender"] == CLEAR_SENTINEL


def test_label_form_value_loads_as_blank_without_crashing(qapp):
    """A pre-migration row holding a label must not break the dialog."""
    _parent, fields = _build("N")
    fields.load_from_values({"declension": "Strong (s)"})
    assert fields.fields["declension"].currentIndex() == 0
    assert fields.extract_values()["declension"] is None


def test_manager_accepts_only_preset_supported_pos(qapp):
    parent = QWidget()
    for pos in ("N", "V", "A", "R", "D"):
        PresetPosFormManager(pos, QFormLayout(parent), parent)
    for pos in ("E", "B", "C", "I", "L", "Z"):
        with pytest.raises(ValueError, match="Unsupported preset Part of Speech"):
            PresetPosFormManager(pos, QFormLayout(parent), parent)


def test_object_names_are_derived(qapp):
    _p, noun = _build("N")
    _p2, verb = _build("V")
    assert noun.fields["gender"].objectName() == "n_gender_combo"
    assert verb.fields["verb_class"].objectName() == "v_verb_class_combo"


@pytest.mark.parametrize("pos", ["N", "V", "A", "R", "D"])
def test_boolean_and_blank_semantics_survive(qapp, pos):
    _parent, fields = _build(pos)
    assert all(combo.itemText(0) == "" for combo in fields.fields.values())
    assert set(fields.extract_values().values()) == {None}
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_pos_form_system_presets.py -v`
Expected: every test FAILS at first with `TypeError` (the base class does not yet take `pos`). After the constructor change in Step 3, the behavioural tests are the real red-to-green check: `test_declension_extracts_the_code_not_the_label` and `test_verb_class_round_trips_the_code` must be confirmed failing against the old logic (`'Strong (s)' != 's'`, combo text `'pp'`) before you move on, for example by running them once with the constructor change but the old `_add_field` still in place.

- [ ] **Step 3: Implement**

Check dead-code candidates first: `grep -rn "_set_combo_value\|_extract_combo_value\|PosFieldSpec\|FIELD_SPECS\|PRESET_VERB_" oeapp tests --include=*.py`. Delete `_extract_combo_value` and `_set_combo_value` from `annotation_preset_management.py` only if the only remaining references are in tests; delete the two `_set_combo_value` test methods (`test_set_combo_value_sets_empty_for_none`, `test_set_combo_value_sets_actual_values_correctly`) entirely. Do not remove the `*_REVERSE_MAP` attributes on `AnnotationLookupsMixin` unless the grep shows no users anywhere.

In `pos_form_system.py`: delete the `PosFieldSpec` dataclass and its `dataclass` import, add `from oeapp.ui.pos_field_catalog import PosField, PosFieldCatalog` (Task 2 already imported `PosFieldCatalog`; add `PosField` to that import), and change `PresetPartOfSpeechFieldsBase`: remove `PART_OF_SPEECH`, `FIELD_SPECS`, `PRESET_VERB_BOOLEAN_MAP` and `PRESET_VERB_TRANSITIVITY_MAP`; change its `__init__` to `def __init__(self, layout: QFormLayout, parent_widget: QWidget, pos: str) -> None:` storing `#: Part of speech code.` / `self.pos = pos` (keep the existing attribute initialisation and update the docstring `Args:`); change the `_specs_by_attr` annotation to `dict[str, PosField]`; and replace `build`, `_add_field`, `load_from_values`, `extract_values` with:

```python
    def build(self) -> None:
        """Build one combo per catalog field for this preset POS."""
        for field in PosFieldCatalog.fields(self.pos):
            self._specs_by_attr[field.attr] = field
            self._add_field(field)

    def _add_field(self, field: PosField) -> None:
        """
        Add one code-mapped combo for a catalog field.

        Args:
            field: The catalog field to render.

        """
        combo = QComboBox(self.parent_widget)
        combo.setObjectName(f"{self.pos.lower()}_{field.attr}_combo")
        combo.addItem("")
        offset = 1
        if field.preset_clear_mode:
            combo.addItem("Clear")
            offset = 2

        codes = list(field.lookup_map.keys())
        values = list(field.lookup_map.values())
        if values and values[0] == "":
            codes = codes[1:]
            values = values[1:]

        combo.addItems([str(value) for value in values])
        self.code_to_index_map[field.attr] = {
            code: index for index, code in enumerate(codes, start=offset)
        }
        self.index_to_code_map[field.attr] = {
            index: code for code, index in self.code_to_index_map[field.attr].items()
        }
        self.fields[field.attr] = combo
        self.layout.addRow(f"{field.label}:", combo)

    def load_from_values(self, field_values: Mapping[str, str | bool | None]) -> None:
        """
        Load preset field values into rendered widgets.

        Args:
            field_values: Field values.

        """
        for attr, value in field_values.items():
            spec = self._specs_by_attr.get(attr)
            combo = self.fields.get(attr)
            if not spec or not combo:
                continue
            if value is None:
                combo.setCurrentIndex(0)
            elif spec.preset_clear_mode and value == CLEAR_SENTINEL:
                combo.setCurrentIndex(1)
            else:
                combo.setCurrentIndex(self.code_to_index_map[attr].get(value, 0))

    def extract_values(self) -> dict[str, str | bool | None]:
        """
        Extract preset values with empty/clear semantics.

        Returns:
            Field values keyed by attribute; ``None`` for blank.

        """
        extracted: dict[str, str | bool | None] = {}
        for attr, spec in self._specs_by_attr.items():
            index = self.fields[attr].currentIndex()
            if index == 0:
                extracted[attr] = None
            elif spec.preset_clear_mode and index == 1:
                extracted[attr] = CLEAR_SENTINEL
            else:
                extracted[attr] = self.index_to_code_map[attr].get(index)
        return extracted
```

Delete `PresetNounFields`, `PresetVerbFields`, `PresetAdjectiveFields`, `PresetPronounFields` and `PresetArticleFields` entirely. In `PresetPosFormManager`, delete `POS_FIELD_CLASSES` and change the constructor's guard and construction to:

```python
        if not PosFieldCatalog.preset_supported(pos):
            msg = f"Unsupported preset Part of Speech: {pos}"
            raise ValueError(msg)
        #: Pos.
        self.pos = pos
        #: Form layout.
        self.form_layout = form_layout
        #: Parent widget.
        self.parent_widget = parent_widget
        #: Current.
        self.current = PresetPartOfSpeechFieldsBase(form_layout, parent_widget, pos)
        self.current.build()
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_pos_form_system_presets.py tests/test_annotation_preset_management_dialog.py tests/test_annotation_modal.py -v`
Expected: all PASS. Fix any dialog test that hard-codes an old object name (for example `adj_degree_combo`) by switching it to the `_field(dialog, attr)` helper.

- [ ] **Step 5: Gate and commit**

Run: `.venv/bin/ruff check oeapp/ui/dialogs tests/test_pos_form_system_presets.py tests/test_annotation_preset_management_dialog.py && .venv/bin/ruff format --check oeapp/ui/dialogs/pos_form_system.py oeapp/ui/dialogs/annotation_preset_management.py tests/test_pos_form_system_presets.py && .venv/bin/mypy oeapp/ui/dialogs/pos_form_system.py oeapp/ui/dialogs/annotation_preset_management.py`

```bash
git add oeapp/ui/dialogs tests/test_pos_form_system_presets.py tests/test_annotation_preset_management_dialog.py
git commit -m "fix: preset dialog builds from the catalog and stores codes, not labels" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Sidebar renders from the catalog

**Files:**
- Modify: `oeapp/ui/token_details_sidebar.py` (`AbstractPartOfSpeechRenderer` and the per-POS renderer classes, roughly lines 80-440)
- Test: `tests/test_token_details_sidebar.py` (add tests, adjust any that assert the old labels)

**Interfaces:**
- Consumes: `PosFieldCatalog.fields(pos)` from Task 1.
- Produces: `AbstractPartOfSpeechRenderer._render_fields(parent_layout) -> None`. The per-POS renderer classes remain (so `POS_RENDER_MAP` and imports keep working) but become empty subclasses.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_token_details_sidebar.py` (add `from PySide6.QtWidgets import QVBoxLayout, QWidget` and `from oeapp.models.annotation import Annotation` and `from oeapp.ui.token_details_sidebar import NounRenderer, PronounRenderer, VerbRenderer` to the imports):

```python
def _label_texts(layout) -> list[str]:
    texts: list[str] = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is not None and isinstance(item.widget(), QLabel):
            texts.append(item.widget().text())
        elif item.layout() is not None:
            texts.extend(_label_texts(item.layout()))
    return texts


def _render(renderer_cls, annotation) -> list[str]:
    host = QWidget()
    layout = QVBoxLayout(host)
    renderer_cls(annotation).render(layout)
    return _label_texts(layout)


class TestSidebarRendersFromCatalog:
    def test_verb_uses_canonical_class_label(self, qapp):
        annotation = Annotation(pos="V", verb_class="s1")
        texts = _render(VerbRenderer, annotation)
        assert "Class: " in texts
        assert "Verb Class: " not in texts
        assert texts[texts.index("Class: ") + 1] == "Strong Class 1 (s1)"

    def test_unset_field_renders_question_mark(self, qapp):
        texts = _render(VerbRenderer, Annotation(pos="V", verb_class="s1"))
        assert texts[texts.index("Aspect: ") + 1] == "?"

    def test_unknown_code_renders_question_mark_not_error(self, qapp):
        texts = _render(NounRenderer, Annotation(pos="N", declension="zz"))
        assert texts[texts.index("Declension: ") + 1] == "?"

    def test_label_form_declension_renders_question_mark(self, qapp):
        texts = _render(NounRenderer, Annotation(pos="N", declension="Strong (s)"))
        assert texts[texts.index("Declension: ") + 1] == "?"

    def test_pronoun_uses_canonical_type_label(self, qapp):
        texts = _render(PronounRenderer, Annotation(pos="R", pronoun_type="p"))
        assert "Type: " in texts and "Pronoun Type: " not in texts

    def test_boolean_flag_renders_yes_no(self, qapp):
        annotation = Annotation(pos="V", verb_requires_infinitive=True, verb_impersonal=False)
        texts = _render(VerbRenderer, annotation)
        assert texts[texts.index("Requires Infinitive: ") + 1] == "Yes"
        assert texts[texts.index("Impersonal: ") + 1] == "No"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_token_details_sidebar.py -k Catalog -v`
Expected: FAIL (`"Class: "` not in texts because the sidebar says `Verb Class: `; `Aspect` shows blank not `?`).

- [ ] **Step 3: Implement**

In `token_details_sidebar.py` add `from oeapp.ui.pos_field_catalog import PosFieldCatalog`. At the end of `AbstractPartOfSpeechRenderer.render` (after `parent_layout.addSpacing(23)`) add `self._render_fields(parent_layout)` and add the method:

```python
    def _render_fields(self, parent_layout: QVBoxLayout) -> None:
        """
        Render one labelled row per catalog field for the annotation's POS.

        Args:
            parent_layout: Parent layout to add the rows to

        """
        annotation = cast("Annotation", self.annotation)
        for field in PosFieldCatalog.fields(annotation.pos):
            value = getattr(annotation, field.attr)
            text = "?" if value is None else field.lookup_map.get(value, "?")
            self.field_renderer.format_field(field.label, text, parent_layout)
```

Delete the `render()` override from every concrete renderer (`NounRenderer`, `VerbRenderer`, `AdjectiveRenderer`, `PronounRenderer`, `ArticleRenderer`, `PrepositionRenderer`, `AdverbRenderer`, `ConjunctionRenderer`), leaving each class as its docstring (and `pass` is unnecessary once a docstring exists).

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_token_details_sidebar.py -v`
Expected: all PASS. Fix any existing assertion that hard-codes an old sidebar label (`Pronoun Type`, `Article Type`, `Adverb Degree`, `Conjunction Type`, `Verb Class`) to the canonical one (`Type`, `Type`, `Degree`, `Type`, `Class`); keep the intent of each test.

- [ ] **Step 5: Gate and commit**

Run: `.venv/bin/ruff check oeapp/ui/token_details_sidebar.py && .venv/bin/mypy oeapp/ui/token_details_sidebar.py` (skip `ruff format --check` here: this file already has unrelated formatting drift).

```bash
git add oeapp/ui/token_details_sidebar.py tests/test_token_details_sidebar.py
git commit -m "refactor: token details sidebar renders POS fields from the catalog" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4b: Display helpers tolerate unrecognised codes

`AnnotationTextualMixin.format_pos`, `format_gender` and `format_context` in `oeapp/mixins.py` index their maps directly, so one unrecognised stored value (for example the label-form `"Strong (s)"` found in 6 of the maintainer's annotations) raises `KeyError` in the sidebar header, DOCX export, annotation propagation and the remembered-annotations dialog. The PDF exporter already falls back to the stored text; this makes the shared mixin do the same.

**Files:**
- Modify: `oeapp/mixins.py` (`AnnotationTextualMixin`: add `_label`; change the 21 direct `self.<X>_MAP[...]` lookups inside `format_pos`, `format_gender`, `format_context`)
- Test: `tests/test_mixins.py`

**Interfaces:**
- Produces: `AnnotationTextualMixin._label(mapping: Mapping[str, str], code: str) -> str` returning `mapping.get(code, code)`. Public method signatures and results for recognised codes are unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mixins.py` (it already imports `Annotation` and `AnnotationTextualMixin`):

```python
class TestAnnotationTextualMixinUnknownCodes:
    """Unrecognised stored values fall back to the stored text, never raise."""

    def test_format_pos_unknown_noun_declension(self):
        annotation = Annotation(pos="N", declension="Strong (s)")
        assert AnnotationTextualMixin().format_pos(annotation) == "n:Strong (s)"

    def test_format_pos_unknown_verb_class(self):
        annotation = Annotation(pos="V", verb_class="Weak Class II (w2)")
        assert AnnotationTextualMixin().format_pos(annotation) == "v:Weak Class II (w2)"

    def test_format_pos_unknown_adjective_values(self):
        annotation = Annotation(
            pos="A", adjective_inflection="odd", adjective_degree="weird"
        )
        result = AnnotationTextualMixin().format_pos(annotation)
        assert result.endswith(":odd:weird")

    def test_format_gender_unknown(self):
        annotation = Annotation(pos="N", gender="zz")
        assert AnnotationTextualMixin().format_gender(annotation) == "zz"

    def test_format_context_unknown_case_and_number(self):
        annotation = Annotation(pos="N", case="zz", number="qq")
        assert AnnotationTextualMixin().format_context(annotation) == "zzqq"

    def test_format_context_unknown_verb_values(self):
        annotation = Annotation(
            pos="V", verb_tense="t?", verb_mood="m?", verb_person="p?", number="n?"
        )
        assert AnnotationTextualMixin().format_context(annotation) == "t?m?p?n?"

    def test_format_pos_unknown_part_of_speech_does_not_raise(self):
        annotation = Annotation(pos="Z")
        assert AnnotationTextualMixin().format_pos(annotation) == "Z"

    def test_known_codes_are_unchanged(self):
        annotation = Annotation(pos="N", declension="s", gender="m", case="n", number="s")
        mixin = AnnotationTextualMixin()
        assert mixin.format_pos(annotation) == "n:strong"
        assert mixin.format_gender(annotation) == "m"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_mixins.py -k UnknownCodes -v`
Expected: the seven unknown-code tests FAIL with `KeyError`; `test_known_codes_are_unchanged` PASSES.

- [ ] **Step 3: Implement**

In `oeapp/mixins.py`, add `from collections.abc import Mapping` to the imports if absent, add this method to `AnnotationTextualMixin` just above `format_pos`:

```python
    @staticmethod
    def _label(mapping: Mapping[str, str], code: str) -> str:
        """
        Look a code up in a display map, falling back to the stored text.

        Args:
            mapping: Code-to-display map.
            code: The stored value.

        Returns:
            The display text, or ``code`` itself when the map does not know it.

        """
        return mapping.get(code, code)
```

then replace every direct lookup inside `format_pos`, `format_gender` and `format_context` mechanically, for example `self.DECLENSION_MAP[annotation.declension]` becomes `self._label(self.DECLENSION_MAP, annotation.declension)`. Do it with this one-off script (it touches only the three methods, from `def format_pos` to the start of `class TokenOccurrenceMixin`), then format the file:

```bash
.venv/bin/python - <<'EOF'
import re
from pathlib import Path

path = Path("oeapp/mixins.py")
src = path.read_text()
start = src.index("    def format_pos")
end = src.index("class TokenOccurrenceMixin")
body, count = re.subn(r"self\.(\w+_MAP)\[([^\]]+)\]", r"self._label(self.\1, \2)", src[start:end])
print("replaced", count)
path.write_text(src[:start] + body + src[end:])
EOF
.venv/bin/ruff format oeapp/mixins.py
```
Expected: `replaced 21`. `oeapp/mixins.py` was already ruff-format clean, so formatting it only re-wraps the lines this change lengthened.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_mixins.py tests/test_token_details_sidebar.py tests/test_export_docx.py -v`
Expected: all PASS, including every pre-existing `format_pos` test.

- [ ] **Step 5: Gate and commit**

Run: `.venv/bin/ruff check oeapp/mixins.py && .venv/bin/ruff format --check oeapp/mixins.py && .venv/bin/mypy oeapp/mixins.py`

```bash
git add oeapp/mixins.py tests/test_mixins.py
git commit -m "fix: annotation display helpers fall back to stored text for unknown codes" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Data migration and preset CHECK constraints

**Files:**
- Modify: `oeapp/models/annotation_preset.py` (`__table_args__`, about lines 32-39)
- Create (via script): `oeapp/models/alembic/versions/<rev>_repair_declension_and_verb_class_codes.py`
- Modify (by script): `oeapp/etc/migration_versions.json`
- Test: `tests/test_migration_pos_codes.py` (create)

**Interfaces:**
- Produces: a revision with `down_revision = "f38623b35077"`; module-level `_VALID_CODES: dict[str, frozenset[str]]`, `_LABELS: dict[str, dict[str, str]]`, `_repair(column: str, value: str) -> str | None` (frozen copies, deliberately independent of live code); `upgrade()`; `downgrade()` (no-op). Constraint names `ck_annotation_presets_declension` and `ck_annotation_presets_verb_class`.

- [ ] **Step 1: Add the CHECKs to the model**

In `AnnotationPreset.__table_args__`, after the existing two `CheckConstraint`s, add:

```python
        CheckConstraint(
            "declension IN ('s','w','o','i','u','ja','jo','wa','wo','pu','r',"
            "'i-mut','er','nd','th')",
            name="ck_annotation_presets_declension",
        ),
        CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','pp','s1','s2','s3','s4','s5','s6','s7')",
            name="ck_annotation_presets_verb_class",
        ),
```

- [ ] **Step 2: Create the revision skeleton**

Autogenerate does not track `CHECK`s, so the file is hand-filled. Run against a scratch copy of the real database so the maintainer's file is never touched:

```bash
S=/private/tmp/claude-501/-Users-cmalek-src-workspace-aenglisc-toolkit/504d1097-ad6e-4af4-9d3c-a17824ee7187/scratchpad
cp default.db "$S/default-copy.db"
AENGLISC_TOOLKIT_DB_PATH="$S/default-copy.db" .venv/bin/python bin/create_migration.py "repair declension and verb class codes"
git status --short oeapp/models/alembic/versions oeapp/etc
```

Expected: one new `*_repair_declension_and_verb_class_codes.py` plus a changed `oeapp/etc/migration_versions.json`. Keep the generated header (the `revision`, `down_revision`, `branch_labels`, `depends_on` lines) and the `"""docstring"""`; replace everything after `depends_on` in the next step. If `field_mappings.json` was also modified by the script, keep that change.

- [ ] **Step 3: Write the failing tests**

Create `tests/test_migration_pos_codes.py`:

```python
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
        return [r[0] for r in conn.exec_driver_sql(f"SELECT {column} FROM {table} ORDER BY id")]


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
    assert {"ck_annotation_presets_declension", "ck_annotation_presets_verb_class",
            "ck_annotation_presets_pos"} <= names
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO annotation_presets (pos, declension) VALUES ('N','bogus')")


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
        conn.exec_driver_sql("INSERT INTO annotation_presets (pos, declension) VALUES ('N','Weak (w)')")
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
```

- [ ] **Step 4: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_migration_pos_codes.py -v`
Expected: FAIL (`AttributeError: module ... has no attribute '_repair'`, and data unchanged).

- [ ] **Step 5: Fill in the revision**

First confirm the label history the frozen table must cover (ADR D6 says "every label the maps have carried"). Run:

```bash
for f in oeapp/ui/mixins.py oeapp/mixins.py; do git log --all -p --format= -- "$f"; done \
  | grep -E '^[-+]\s+"[a-z0-9-]+": "[^"]*\((s|w|o|i|u|ja|jo|wa|wo|pu|r|i-mut|er|nd|th|a|w[123]|pp|s[1-7])\)"' \
  | sed -E 's/^[-+]\s+//' | sort -u
```
Expected (checked 2026-10-02): every printed label already appears in `_LABELS` below, so history adds nothing and the reworded-label case is carried by tier b. If a label *without* a trailing `(code)` ever shows up, add it to `_LABELS`.

Then edit the generated file: add `import logging` and `import re` to its existing import block at the top (it already imports `sqlalchemy as sa` and `op`; do not import them a second time mid-file), and replace everything after `depends_on = None` with the following:

```python
logger = logging.getLogger(__name__)

#: Tables repaired by this revision.
_TABLES = ("annotation_presets", "annotations")

#: Valid codes, frozen at the time of this revision.
_VALID_CODES = {
    "declension": frozenset(
        {"s", "w", "o", "i", "u", "ja", "jo", "wa", "wo", "pu", "r", "i-mut", "er", "nd", "th"}
    ),
    "verb_class": frozenset(
        {"a", "w1", "w2", "w3", "pp", "s1", "s2", "s3", "s4", "s5", "s6", "s7"}
    ),
}

#: Display labels the combos have shown, mapped to codes. Frozen.
_LABELS = {
    "declension": {
        "Strong (s)": "s",
        "Weak (w)": "w",
        "Other (o)": "o",
        "i-stem (i)": "i",
        "u-stem (u)": "u",
        "ja-stem (ja)": "ja",
        "jo-stem (jo)": "jo",
        "wa-stem (wa)": "wa",
        "wo-stem (wo)": "wo",
        "abstract -pu/-po (pu)": "pu",
        "r-stem (r)": "r",
        "i-mutation (i-mut)": "i-mut",
        "er nouns (children) (er)": "er",
        "-nd nouns(nd)": "nd",
        "-þ endings (th)": "th",
    },
    "verb_class": {
        "Anomolous (a)": "a",
        "Weak Class I (w1)": "w1",
        "Weak Class II (w2)": "w2",
        "Weak Class III (w3)": "w3",
        "Preterite-Present (pp)": "pp",
        "Strong Class 1 (s1)": "s1",
        "Strong Class 2 (s2)": "s2",
        "Strong Class 3 (s3)": "s3",
        "Strong Class 4 (s4)": "s4",
        "Strong Class 5 (s5)": "s5",
        "Strong Class 6 (s6)": "s6",
        "Strong Class 7 (s7)": "s7",
    },
}

#: A trailing parenthesised code, as every label ends.
_SUFFIX = re.compile(r"\(([^()]+)\)\s*$")


def _normalise(text: str) -> str:
    """Collapse whitespace and case-fold ``text``."""
    return " ".join(text.split()).casefold()


_LABEL_LOOKUP = {
    column: {_normalise(label): code for label, code in labels.items()}
    for column, labels in _LABELS.items()
}


def _repair(column: str, value: str) -> str | None:
    """
    Return the code for a stored value, ``None`` for blank, or ``value`` itself.

    Tiers, first match wins: already a code; trailing ``(code)``; normalised
    label. There is deliberately no fuzzy matching.
    """
    codes = _VALID_CODES[column]
    if value in codes:
        return value
    if not value.strip():
        return None
    match = _SUFFIX.search(value)
    if match and match.group(1).strip() in codes:
        return match.group(1).strip()
    return _LABEL_LOOKUP[column].get(_normalise(value), value)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table: str) -> bool:
    return table in _inspector().get_table_names()


def _column_exists(table: str, column: str) -> bool:
    return _table_exists(table) and any(
        c["name"] == column for c in _inspector().get_columns(table)
    )


def _check_constraint_exists(table: str, name: str) -> bool:
    return _table_exists(table) and any(
        c.get("name") == name for c in _inspector().get_check_constraints(table)
    )


def _repair_column(table: str, column: str) -> bool:
    """
    Repair one column in place.

    Returns:
        ``True`` if any value remains that no tier could resolve.

    """
    bind = op.get_bind()
    select = sa.text(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")  # noqa: S608
    update = sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old")  # noqa: S608
    unresolved = False
    for value in bind.execute(select).scalars().all():
        repaired = _repair(column, value)
        if repaired == value:
            if value not in _VALID_CODES[column]:
                logger.warning("pos-code-repair.unmatched table=%s column=%s value=%r", table, column, value)
                unresolved = True
            continue
        bind.execute(update, {"new": repaired, "old": value})
    return unresolved


def _in_list(column: str) -> str:
    codes = ", ".join(repr(code) for code in sorted(_VALID_CODES[column]))
    return f"{column} IN ({codes})"


def _add_preset_checks() -> None:
    with op.batch_alter_table("annotation_presets", schema=None) as batch_op:
        for column in _VALID_CODES:
            name = f"ck_annotation_presets_{column}"
            if not _check_constraint_exists("annotation_presets", name):
                batch_op.create_check_constraint(name, _in_list(column))


def upgrade() -> None:
    """Repair label-form values, then constrain presets if everything resolved."""
    preset_unresolved = False
    for table in _TABLES:
        for column in _VALID_CODES:
            if not _column_exists(table, column):
                continue
            unresolved = _repair_column(table, column)
            preset_unresolved = preset_unresolved or (
                unresolved and table == "annotation_presets"
            )
    if not _table_exists("annotation_presets"):
        return
    if preset_unresolved:
        logger.warning("pos-code-repair.checks-skipped table=annotation_presets")
        return
    _add_preset_checks()


def downgrade() -> None:
    """Downgrade schema.

    Intentionally a no-op: the earlier state was corrupt data.
    """
```

- [ ] **Step 6: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_migration_pos_codes.py tests/test_migration_backup_restore.py tests/test_annotation_preset_model.py -v`
Expected: all PASS. If `test_checks_added_and_existing_check_kept_when_clean` fails because the pre-existing `ck_annotation_presets_pos` is lost by the batch rebuild, **stop and report it to the user**; the revision would then have to re-declare it explicitly.

- [ ] **Step 7: Rehearse on a copy of the real database**

```bash
S=/private/tmp/claude-501/-Users-cmalek-src-workspace-aenglisc-toolkit/504d1097-ad6e-4af4-9d3c-a17824ee7187/scratchpad
cp default.db "$S/rehearsal.db"
AENGLISC_TOOLKIT_DB_PATH="$S/rehearsal.db" .venv/bin/python - <<'EOF'
import sqlite3
from oeapp.services.migration import MigrationService
print(MigrationService().migrate())
con = sqlite3.connect("file:" + __import__("os").environ["AENGLISC_TOOLKIT_DB_PATH"] + "?mode=ro", uri=True)
print("preset labels:", con.execute("select count(*) from annotation_presets where declension like '%(%'").fetchone())
print("annotation labels:", con.execute("select count(*) from annotations where declension like '%(%'").fetchone())
print("annotation empties:", con.execute("select count(*) from annotations where declension = ''").fetchone())
print("preset checks:", [r[0] for r in con.execute("select sql from sqlite_master where name='annotation_presets'")][0].count("CHECK"))
EOF
rm -f "$S/rehearsal.db" "$S/default-copy.db"
```
Expected: migrate succeeds; the three counts are `(0,)`; `preset checks:` is at least 4. Report the numbers to the user.

- [ ] **Step 8: Gate and commit**

Run: `.venv/bin/ruff check oeapp/models tests/test_migration_pos_codes.py && .venv/bin/mypy oeapp/models/annotation_preset.py`

```bash
git add oeapp/models/annotation_preset.py oeapp/models/alembic/versions oeapp/etc tests/test_migration_pos_codes.py
git commit -m "feat: repair label-form declension and verb_class values, constrain presets" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Import remaps label-form values from older exports

**Files:**
- Create: `oeapp/services/pos_code_repair.py`
- Modify: `oeapp/services/import_export.py` (`_apply_field_mappings` at ~396; add two small helpers)
- Modify: `oeapp/etc/field_mappings.json`
- Test: `tests/test_pos_code_repair.py` (create)

**Interfaces:**
- Produces: `PosCodeRepair(valid_codes: Iterable[str], labels: Mapping[str, str])`; `PosCodeRepair.repair(value: str) -> str | None`; `PosCodeRepair.from_mapping(spec: Mapping[str, Any]) -> PosCodeRepair` (raises `ValueError` on a malformed spec, where a spec is `{"codes": [...], "labels": {label: code}}`).
- Consumes: the revision id and frozen tables from Task 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pos_code_repair.py`:

```python
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
    (ROOT / "oeapp/models/alembic/versions").glob("*_repair_declension_and_verb_class_codes.py")
)
FIELD_MAPPINGS = ROOT / "oeapp/etc/field_mappings.json"


def _migration():
    spec = importlib.util.spec_from_file_location("repair_codes_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _revision() -> str:
    return re.search(r'^revision: str = ["\']([^"\']+)["\']', MIGRATION.read_text(), re.M).group(1)


def _repairers() -> dict[str, PosCodeRepair]:
    values = json.loads(FIELD_MAPPINGS.read_text())[_revision()]["values"]
    return {attr: PosCodeRepair.from_mapping(spec) for attr, spec in values.items()}


def _importer() -> ProjectImporter:
    return ProjectImporter(migration_service=MagicMock())


def test_from_mapping_rejects_malformed_specs():
    for bad in ({}, {"codes": ["s"]}, {"codes": "s", "labels": {}}, {"codes": ["s"], "labels": []}):
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
        ("declension", "Strong (s)"), ("declension", " weak (w) "), ("declension", "-nd nouns(nd)"),
        ("declension", ""), ("declension", "s"), ("declension", "unknown text"),
        ("verb_class", "Anomolous (a)"), ("verb_class", "Strong Class 2 (s2)"),
        ("verb_class", "Strong Class 9"), ("verb_class", "pp"),
    ],
)
def test_runtime_repair_agrees_with_the_migration(column, value):
    assert _repairers()[column].repair(value) == _migration()._repair(column, value)


def test_old_export_label_values_import_as_codes():
    importer = _importer()
    data = {
        "presets": [{"pos": "N", "declension": "Strong (s)", "gender": "m"}],
        "annotations": [{"declension": "Strong (s)", "verb_class": "Preterite-Present (pp)"}],
    }
    mappings = {"rev1": json.loads(FIELD_MAPPINGS.read_text())[_revision()]}
    with patch.object(importer, "_load_field_mappings", return_value=mappings):
        result = importer._apply_field_mappings(data, ["rev1"])
    assert result["presets"][0] == {"pos": "N", "declension": "s", "gender": "m"}
    assert result["annotations"][0] == {"declension": "s", "verb_class": "pp"}


def test_unmatched_and_non_string_values_pass_through():
    importer = _importer()
    data = {"a": {"declension": "free text", "verb_class": None}, "b": [{"declension": 5}]}
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_pos_code_repair.py -v`
Expected: collection FAIL, `ModuleNotFoundError: No module named 'oeapp.services.pos_code_repair'`.

- [ ] **Step 3: Write `PosCodeRepair`**

Create `oeapp/services/pos_code_repair.py`:

```python
"""Tiered repair of label-form part-of-speech codes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class PosCodeRepair:
    """
    Turn a stored value into the code it was meant to be.

    Tiers, first match wins: already a code; trailing ``(code)``; normalised
    label. There is deliberately no fuzzy matching, because the labels differ
    by one character ("Strong Class 1 (s1)" against "Strong Class 2 (s2)").

    Args:
        valid_codes: The codes the column may hold.
        labels: Display label to code.

    """

    #: A trailing parenthesised code, as every label ends.
    _SUFFIX: ClassVar[re.Pattern[str]] = re.compile(r"\(([^()]+)\)\s*$")

    def __init__(self, valid_codes: Iterable[str], labels: Mapping[str, str]) -> None:
        """
        Initialize the repairer.

        Args:
            valid_codes: The codes the column may hold.
            labels: Display label to code.

        """
        #: Valid codes.
        self.valid_codes: frozenset[str] = frozenset(valid_codes)
        #: Normalised label to code.
        self._labels: dict[str, str] = {
            self._normalise(label): code for label, code in labels.items()
        }

    @staticmethod
    def _normalise(text: str) -> str:
        """Collapse whitespace and case-fold ``text``."""
        return " ".join(text.split()).casefold()

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> PosCodeRepair:
        """
        Build a repairer from a ``field_mappings.json`` values spec.

        Args:
            spec: ``{"codes": [...], "labels": {label: code}}``.

        Returns:
            The repairer.

        Raises:
            ValueError: If the spec is malformed.

        """
        codes = spec.get("codes") if isinstance(spec, dict) else None
        labels = spec.get("labels") if isinstance(spec, dict) else None
        if not isinstance(codes, list) or not isinstance(labels, dict):
            msg = f"Malformed values mapping: {spec!r}"
            raise ValueError(msg)
        return cls(codes, labels)

    def repair(self, value: str) -> str | None:
        """
        Repair one stored value.

        Args:
            value: The stored string.

        Returns:
            The code; ``None`` for a blank value; ``value`` unchanged when no
            tier matches.

        """
        if value in self.valid_codes:
            return value
        if not value.strip():
            return None
        match = self._SUFFIX.search(value)
        if match and match.group(1).strip() in self.valid_codes:
            return match.group(1).strip()
        return self._labels.get(self._normalise(value), value)
```

- [ ] **Step 4: Generate the frozen JSON tables**

Run this one-off (it reads the revision id from the migration file and writes the tables into `oeapp/etc/field_mappings.json`, merging with anything the Task 5 script already wrote):

```bash
.venv/bin/python - <<'EOF'
import json, re
from pathlib import Path
from oeapp.ui.mixins import AnnotationLookupsMixin as M

path = next(Path("oeapp/models/alembic/versions").glob("*_repair_declension_and_verb_class_codes.py"))
rev = re.search(r'^revision: str = ["\']([^"\']+)["\']', path.read_text(), re.M).group(1)

def section(m):
    return {"codes": sorted(k for k in m if k), "labels": {v: k for k, v in m.items() if k}}

target = Path("oeapp/etc/field_mappings.json")
data = json.loads(target.read_text() or "{}")
data.setdefault(rev, {})["values"] = {
    "declension": section(M.DECLENSION_MAP),
    "verb_class": section(M.VERB_CLASS_MAP),
}
target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("wrote", rev)
EOF
git diff --stat oeapp/etc/field_mappings.json
```

- [ ] **Step 5: Teach the importer about `values`**

In `oeapp/services/import_export.py` add `from oeapp.services.pos_code_repair import PosCodeRepair` to the imports, replace `_apply_field_mappings` and add `_apply_value_repairs`:

```python
    def _apply_field_mappings(
        self, data: dict[str, Any], migration_chain: list[str]
    ) -> dict[str, Any]:
        """
        Apply field renames and value repairs incrementally through the chain.

        Args:
            data: Data dictionary to transform
            migration_chain: Ordered list of migration revision IDs

        Returns:
            Transformed data dictionary

        Raises:
            ValueError: If a revision's ``values`` section is malformed

        """
        field_mappings = self._load_field_mappings()

        for migration_sha in migration_chain:
            if migration_sha not in field_mappings:
                continue
            migration_mappings = dict(field_mappings[migration_sha])
            values = migration_mappings.pop("values", None)
            self._apply_mappings_recursive(data, migration_mappings)
            if values:
                if not isinstance(values, dict):
                    msg = f"Malformed values mapping: {values!r}"
                    raise ValueError(msg)  # noqa: TRY004
                repairers = {
                    attr: PosCodeRepair.from_mapping(spec)
                    for attr, spec in values.items()
                }
                self._apply_value_repairs(data, repairers)

        return data

    def _apply_value_repairs(
        self, obj: Any, repairers: dict[str, PosCodeRepair]
    ) -> None:
        """
        Repair string values of the named keys wherever they appear.

        Args:
            obj: Object to transform (dict, list, or primitive)
            repairers: Repairer per key name

        """
        if isinstance(obj, dict):
            for attr, repairer in repairers.items():
                if isinstance(obj.get(attr), str):
                    obj[attr] = repairer.repair(obj[attr])
            for value in obj.values():
                self._apply_value_repairs(value, repairers)
        elif isinstance(obj, list):
            for item in obj:
                self._apply_value_repairs(item, repairers)
```

Note the `_transform_data` handler catches only `(KeyError, AttributeError, TypeError)`; `ValueError` therefore propagates, which the malformed-section test pins.

- [ ] **Step 6: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_pos_code_repair.py tests/test_import_export.py -v`
Expected: all PASS.

- [ ] **Step 7: Gate and commit**

Run: `.venv/bin/ruff check oeapp/services && .venv/bin/ruff format --check oeapp/services/pos_code_repair.py && .venv/bin/mypy oeapp/services/pos_code_repair.py oeapp/services/import_export.py`

```bash
git add oeapp/services/pos_code_repair.py oeapp/services/import_export.py oeapp/etc/field_mappings.json tests/test_pos_code_repair.py
git commit -m "feat: import repairs label-form declension and verb_class from older exports" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Docs, help, ADR status and final verification

**Files:**
- Modify: `doc/source/overview/annotation.rst`, `doc/source/overview/translation.rst`, `oeapp/help/topics/annotation-guide.md`, `oeapp/help/topics/morphological-reference.md`, and any other file the grep below flags
- Modify: `doc/source/architecture/adr_0005_pos_field_catalog.rst`
- Regenerate: `oeapp/help/assets/*.html`, `.qch`/`.qhc`, and the macOS help book

- [ ] **Step 1: Find label mentions**

Run: `grep -rnE "Verb Class|Pronoun Type|Article Type|Adverb Degree|Conjunction Type" doc/source oeapp/help/topics README* 2>/dev/null`
Edit each hit that names the **sidebar or form field label** to the canonical label (`Verb Class` to `Class`, `Pronoun Type`/`Article Type`/`Conjunction Type` to `Type`, `Adverb Degree` to `Degree`). Leave ordinary prose ("the verb class", "verb class codes") alone. For `oeapp/help/topics/export-formatting.md`, read the context first: change it only if it describes a form label, not an export column.

- [ ] **Step 2: Regenerate help assets**

Run: `make help-assets && .venv/bin/python scripts/build_macos_helpbook.py`
Expected: `oeapp/help/assets/*.html` and the macOS help book change only where topics changed. Do not hand-edit the generated files.

- [ ] **Step 3: Update the ADR**

In `adr_0005_pos_field_catalog.rst`: set `:Status: Accepted`; replace the "Ordering:" consequence with: "The catalog is consumed surface by surface (modal, preset, sidebar), each handling every part of speech, rather than part of speech by part of speech." Keep the screenshot list.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check oeapp tests
.venv/bin/mypy oeapp
make napoleon-gate
graphify update .
```
Expected: the suite is green (baseline is 0 failures); ruff and mypy clean for touched files. Report `make napoleon-gate` output as-is and say it is the known-unusable gate; do not edit the baseline.

- [ ] **Step 5: Hand the screenshots to the user**

Do not retake them yourself. Tell the user these four need retaking in `doc/source/_static/`: `screenshot-annotation-sidebar.png` and `screenshot-full-translation.png` (sidebar "Class:"), `screenshot-save-as-preset-button.png` (preset dialog order and normal Class combo), `screenshot-pos-presets-dialog.png` (normal Declension combo).

- [ ] **Step 6: Commit**

```bash
git add doc oeapp/help
git commit -m "docs: update labels, help topics and ADR 0005 for the POS field catalog" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage (ADR 0005):** D8 display fallback (Task 4b); D1 catalog (Task 1); D2 one label and order (Tasks 1, 4, 7); D3 flags, derived `object_name`, `editable` removed, dead helpers removed, clear-mode kept off for `declension`/`verb_class` (Tasks 1, 3); D4 `pp` rule stays in `VerbFields` (Task 2, test pins it); D5 all parts of speech (Tasks 1-4); D6 migration tiers, `NULL`/sentinel handling, preset `CHECK`s, unmatched kept (Task 5), import `values` remap with parity test and non-swallowed errors (Task 6); D7 verification: stored-label repro (Task 3), migration test (Task 5), parity test (Task 1), import test (Task 6). Docs/help/screenshots (Task 7). The backlog card owns the `annotations` `CHECK`s; this plan deliberately does not add them.

**Placeholders:** none. The one runtime-substituted value (the new revision id) is read from the migration file by the Task 5 filename glob and the Task 6 script/regex, not hand-typed.

**Type consistency:** `PosField`, `PosFieldCatalog.fields/preset_supported/PRESET_POS` (Task 1) are used with the same names in Tasks 2-4. `PosCodeRepair.from_mapping/repair` (Task 6) match their tests. The migration's `_repair`, `_VALID_CODES`, `_LABELS` (Task 5) are the names Task 6's parity tests read.

**Review Focus coverage:** items 1-2 in Task 3 tests, item 3 in Task 4 tests, item 4 in Task 5 tests (`test_upgrade_is_idempotent`, `test_missing_presets_table_is_a_noop`), item 5 in Task 6 tests.
