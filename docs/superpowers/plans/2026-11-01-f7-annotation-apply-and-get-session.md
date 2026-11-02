# F7 Annotation Apply and get_session Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move annotation-modal apply into `oeapp.services` and the `Annotation` model, fix Undo after editing an existing annotation, and delete the unused `get_session` generator.

**Architecture:** `Annotation.undo_snapshot()` owns the undo field list (fat ORM). `AnnotationApplyService` in `oeapp/services/annotation_apply.py` takes the before-snapshot when a modal opens, builds the `AnnotateTokenCommand`, and records a newly created idiom's id. `AnnotationEdit` in `oeapp.models` carries that before-snapshot from modal open to apply. `SentenceCardController` stays UI: it starts the edit, opens the modal, pushes the command, and tells the card to paint. `SentenceCard` paints and emits. `get_session` is a separate first commit; ADR 0011 D7 is its spec. The F8 classmethod migration is a later plan.

**Tech Stack:** Python 3, PySide6, SQLAlchemy, pytest, ruff, mypy, `make napoleon-gate`. Activate with `source .venv/bin/activate`, then use `.venv/bin/pytest`, `.venv/bin/ruff`, and `.venv/bin/mypy`.

## Spec

### The Undo bug this plan fixes

`AnnotationModal` writes the translator's choices onto the object it edits: the loaded `token.annotation` or `idiom.annotation`. `OldEnglishTextEdit.annotations` caches those same objects, and `Annotation.get_by_idiom` returns the same object from the session's identity map. The card reads its before-state after the modal has already written the new values, so `before` equals `after`. Undo after editing an existing annotation does not restore the old values. A probe on 2026-11-01 set a token's POS to V, applied N through `SentenceCard._on_annotation_applied`, undid, and still read N. New token annotations and new idioms are not affected, because their before-state is `{}`.

### In

1. Delete `oeapp/db.py:get_session`. Keep the name `get_session` in the freeze scanner's kind set. Drop `"get_session": {"SessionLocal": 1}` from the `oeapp/db.py` allowlist entry. Update ADR 0011 in the same commit.
2. `Annotation.undo_snapshot()` returns the grammatical and lexical fields that `SentenceCard._extract_annotation_state` copies today. It excludes `last_inferred_json` and `updated_at`. Do not reuse `to_json()`.
3. `AnnotationEdit` is a frozen dataclass in `oeapp/models/annotation_edit.py` with one field, `before`.
4. `AnnotationApplyService`:
   - `begin(existing)` returns `AnnotationEdit(before=existing.undo_snapshot())`, or `AnnotationEdit(before={})` when `existing` is `None`.
   - `command_for(edit, applied, sentence_id)` builds `AnnotateTokenCommand` with `before` from the edit and `after=applied.undo_snapshot()`. When `applied.idiom_id is None` and `applied.idiom is not None`, it passes that idiom as `new_idiom` (ADR 0002).
   - `finish(applied, command)` copies `command.idiom_id` onto `applied` when the command created an idiom.
5. The controller calls `begin` before it constructs the modal. The existing annotation is `token.annotation`, or `Annotation.get_by_token(token.id)` when that is `None`, for a token. It is `idiom.annotation` for an existing idiom, and `None` for a new idiom.
6. `SentenceCardController.apply_annotation(edit, annotation)` builds the command through the service and pushes it. On success it calls `finish`, then `card.show_applied_annotation(annotation)`. On failure it does not paint, emit, or set `idiom_id`. Today the card paints and emits even when the push fails.
7. `SentenceCardController.open_annotation_modal` calls `self.open_idiom_modal`, `self.open_new_idiom_modal`, and `self.open_token_modal`. Delete `SentenceCard._open_idiom_modal`, `_open_new_idiom_modal`, and `_open_token_modal`. Keep `SentenceCard._open_annotation_modal`, which ends the Typed Run and calls the controller. Double-click, Enter, and the token table keep using it.
8. The idiom modal's token link calls `parent.controller.open_token_modal`. It does not end the Typed Run again. The idiom modal is modal, and opening it already ended the run.
9. `SentenceCard.show_applied_annotation(annotation)` updates the token cache and token table, or re-renders the idiom, then emits `annotation_applied` and highlights. The card's cache is no longer an undo source.
10. `MainWindowActions.paste_annotation` stays as it is, including its `to_json()` snapshot.
11. `SentenceCardController` takes `annotation_apply: AnnotationApplyService | None = None` as a keyword argument and builds one when none is given.

### Out

- Notes, hierarchy, Old English save, and ADR 0010's Typed Run rules.
- Constructor injection of the runtime session, and the F8 classmethod migration.
- New `_get_session`, `get_runtime_session`, or `app_context.session` reads. The card loses one `Annotation.get_by_idiom` call. `AnnotationApplyService` makes none: it reads the object the controller passes. The controller keeps its existing `Annotation.get_by_token` call in `open_token_modal`. The freeze allowlist does not change, and ADR 0011 D3 cannot see calls into model classmethods either way.
- The duplicate `self.controller = SentenceCardController(self)` in `SentenceCard.__init__` (lines 132 and 135). Keep both lines as they are. Do not add the service argument to either.
- In-app help. `start-here.md` already says annotation changes are undoable. This plan makes that true for edits of existing annotations.
- `docs/superpowers/plans/2026-10-26-runtime-session-freeze.md` and ADR 0002's historical mention of `SentenceCard._on_idiom_annotation_applied`.

### Pre-existing gate failures

On 2026-11-01, before any change:

- `make napoleon-gate` exits 1 with 19 violations against an empty baseline. None are in files this plan touches. The baseline is keyed by line. "Pass" in this plan means no violation is reported in a touched file.
- `.venv/bin/mypy` on the touched UI files reports 2 errors in the imported `oeapp/ui/dialogs/pos_form_system.py` (lines 391 and 414). "Pass" means no error in a touched file.
- `ruff` (`select = ["ALL"]`) reports 1 error in the product files this plan touches: `oeapp/ui/dialogs/annotation_modal.py:104` `PLR0917`. The four existing test files this plan edits have 363 errors between them. "Pass" means no product error other than that one, and a test-file error count no higher than Task 0's.

Record all three outputs before Task 1 so later runs can be compared.

### File map

- Modify `oeapp/db.py` — delete `get_session`.
- Modify `tests/test_runtime_session_freeze.py` — drop the deleted function from `ALLOWLIST` only.
- Modify `doc/source/architecture/adr_0011_runtime_session_freeze.rst` — D7 done in Task 1. F7 done in Task 5.
- Modify `oeapp/models/annotation.py` — `undo_snapshot`.
- Create `oeapp/models/annotation_edit.py` — `AnnotationEdit`. Export from `oeapp/models/__init__.py`.
- Create `oeapp/services/annotation_apply.py` — `AnnotationApplyService`. Export from `oeapp/services/__init__.py`.
- Modify `oeapp/ui/sentence_card_controller.py` — service injection, modal opens, `apply_annotation`.
- Modify `oeapp/ui/sentence_card.py` — `show_applied_annotation`; delete the apply pipeline and the modal bounce.
- Modify `oeapp/ui/dialogs/annotation_modal.py` — token link calls the controller.
- Modify `tests/test_annotation.py`, `tests/test_sentence_card.py`, `tests/test_idioms.py`, `tests/test_annotation_integration.py`.
- Create `tests/test_annotation_apply_service.py`.

---

### Task 0: Record the gate baseline

- [ ] **Step 1: Capture today's gate output**

```bash
source .venv/bin/activate
python bin/check_napoleon_gate.py > /tmp/napoleon-before.txt 2>&1; echo "exit=$?"
.venv/bin/mypy oeapp/db.py oeapp/models/annotation.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py oeapp/ui/dialogs/annotation_modal.py > /tmp/mypy-before.txt 2>&1; echo "exit=$?"
```

```bash
.venv/bin/ruff check oeapp/db.py oeapp/models/annotation.py oeapp/models/__init__.py oeapp/services/__init__.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py oeapp/ui/dialogs/annotation_modal.py --output-format concise > /tmp/ruff-product-before.txt 2>&1
.venv/bin/ruff check tests/test_annotation.py tests/test_sentence_card.py tests/test_idioms.py tests/test_annotation_integration.py --statistics > /tmp/ruff-tests-before.txt 2>&1
```

Expected: both mypy and napoleon exit 1. `/tmp/napoleon-before.txt` ends with `Found 19 new violations`. `/tmp/mypy-before.txt` lists only `pos_form_system.py:391` and `:414`. `/tmp/ruff-product-before.txt` lists only `annotation_modal.py:104` `PLR0917`. `/tmp/ruff-tests-before.txt` ends with `Found 363 errors.`

---

### Task 1: Delete `get_session`

**Files:**
- Modify: `oeapp/db.py` (lines 328–340)
- Modify: `tests/test_runtime_session_freeze.py` (`ALLOWLIST["oeapp/db.py"]`)
- Modify: `doc/source/architecture/adr_0011_runtime_session_freeze.rst`

- [ ] **Step 1: Confirm there is one product definition**

```bash
rg -n "def get_session" oeapp tests
```

Expected: one hit, `oeapp/db.py:328`. `tests/test_runtime_session_freeze.py` mentions `get_session` only inside a sample source string. Leave that string and `LOOKUP_CALLS` alone.

- [ ] **Step 2: Change the allowlist first**

Replace the `oeapp/db.py` entry in `ALLOWLIST` with:

```python
    "oeapp/db.py": {
        "get_runtime_session": {"SessionLocal": 1},
    },
```

- [ ] **Step 3: Verify the freeze test fails**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py::test_oeapp_lookups_match_the_allowlist -q`

Expected: FAIL. The tree still has `get_session` with `SessionLocal: 1`.

- [ ] **Step 4: Delete the function**

Delete `get_session` and its docstring from `oeapp/db.py`.

- [ ] **Step 5: Update ADR 0011**

Set `:Revised:` to the implementation date.

- Context: replace "D7 deletes it. The 2026-11-01 revision does not." and the sentences before it about `get_session` with: `get_session` has been deleted, and `get_runtime_session` holds the only product `SessionLocal()` call.
- D1: replace the `get_session` paragraph with one sentence saying it was deleted under D7. Keep the `QueuePool` paragraph.
- D3: one grandfathered `SessionLocal()` creation remains, in `get_runtime_session`. The kind name `get_session` stays in the scanner and is absent from the allowlist until something calls it.
- D7: rename the heading to "D7 — Delete ``get_session``" (adjust the underline length). Replace the whole body with:

  ```rst
  ``get_session`` in ``oeapp/db.py`` had no callers and called
  ``SessionLocal()`` without registering its session. It has been deleted,
  and ``get_runtime_session`` holds the only product ``SessionLocal()``
  call. The same change dropped ``get_session`` from the ``oeapp/db.py``
  allowlist entry. The scanner keeps ``get_session`` as a kind name, so a
  later function of that name still counts.
  ```

  No sentence about waiting for sprint planning, or about the function still existing, may remain.
- Consequences: delete the bullet "``get_session`` stays until the sprint in D7 is planned."
- Alternatives: replace the "Delete ``get_session`` in the 2026-11-01 revision" bullet with: "**Keep** ``get_session`` **until a sprint is planned for it.** Chosen in the first 2026-11-01 revision. The sprint was planned and D7 deleted it." Dates in this bullet must not contradict D7 when both land on the same day.
- Related: replace the D7 bullet with "D7, delete ``get_session``, is done."

Leave every F7 sentence alone in this commit. Task 5 updates them.

- [ ] **Step 6: Run the freeze test**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py -q`

Expected: PASS, 5 tests.

- [ ] **Step 7: Gates, graph, commit**

```bash
.venv/bin/ruff check oeapp/db.py tests/test_runtime_session_freeze.py
.venv/bin/mypy oeapp/db.py
python bin/check_napoleon_gate.py 2>&1 | rg "oeapp/db.py" ; echo "db.py violations exit=$?"
graphify update .
```

Expected: ruff reports nothing in `oeapp/db.py`. The test file's errors, if any, are ones already in it before this change. mypy reports no error in `oeapp/db.py`. The `rg` exits 1, meaning no napoleon violation in `oeapp/db.py`.

```bash
git add oeapp/db.py tests/test_runtime_session_freeze.py doc/source/architecture/adr_0011_runtime_session_freeze.rst
git commit -m "$(cat <<'EOF'
Delete the unused get_session generator.

EOF
)"
```

Do not add `graphify-out/`.

---

### Task 2: `Annotation.undo_snapshot`

**Files:**
- Modify: `oeapp/models/annotation.py` (add after `to_json`, before `is_effectively_empty`, about line 324)
- Modify: `tests/test_annotation.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_annotation.py`:

```python
def test_undo_snapshot_keeps_grammatical_and_lexical_fields_only() -> None:
    """The undo snapshot excludes inference and timestamp fields."""
    annotation = Annotation(
        pos="N",
        root="cyning",
        root_normalized="cyning",
        modern_english_meaning="king",
        sense="the king",
        confidence=80,
        last_inferred_json='{"pos": "N"}',
    )
    snapshot = annotation.undo_snapshot()
    assert snapshot["pos"] == "N"
    assert snapshot["root"] == "cyning"
    assert snapshot["root_normalized"] == "cyning"
    assert snapshot["modern_english_meaning"] == "king"
    assert snapshot["sense"] == "the king"
    assert snapshot["confidence"] == 80
    assert "last_inferred_json" not in snapshot
    assert "updated_at" not in snapshot
    assert len(snapshot) == 28
```

If `tests/test_annotation.py` does not import `Annotation` at module level, add `from oeapp.models.annotation import Annotation`.

- [ ] **Step 2: Verify it fails**

Run: `.venv/bin/pytest tests/test_annotation.py::test_undo_snapshot_keeps_grammatical_and_lexical_fields_only -q`

Expected: FAIL with `AttributeError: 'Annotation' object has no attribute 'undo_snapshot'`.

- [ ] **Step 3: Add the method**

```python
    def undo_snapshot(self) -> dict:
        """
        Copy the grammatical and lexical fields an annotation Undo restores.

        Returns:
            Field values for :class:`~oeapp.commands.AnnotateTokenCommand`.
            Excludes ``last_inferred_json`` and ``updated_at``.

        """
        return {
            "pos": self.pos,
            "gender": self.gender,
            "number": self.number,
            "case": self.case,
            "declension": self.declension,
            "article_type": self.article_type,
            "pronoun_type": self.pronoun_type,
            "pronoun_number": self.pronoun_number,
            "verb_class": self.verb_class,
            "verb_tense": self.verb_tense,
            "verb_person": self.verb_person,
            "verb_mood": self.verb_mood,
            "verb_aspect": self.verb_aspect,
            "verb_form": self.verb_form,
            "verb_direct_object_case": self.verb_direct_object_case,
            "verb_requires_infinitive": self.verb_requires_infinitive,
            "verb_impersonal": self.verb_impersonal,
            "verb_transitivity": self.verb_transitivity,
            "prep_case": self.prep_case,
            "adverb_degree": self.adverb_degree,
            "adjective_inflection": self.adjective_inflection,
            "adjective_degree": self.adjective_degree,
            "conjunction_type": self.conjunction_type,
            "confidence": self.confidence,
            "modern_english_meaning": self.modern_english_meaning,
            "sense": self.sense,
            "root": self.root,
            "root_normalized": self.root_normalized,
        }
```

`Annotation` has no `list` classmethod, so plain `dict` is fine here.

- [ ] **Step 4: Verify it passes**

Run: `.venv/bin/pytest tests/test_annotation.py::test_undo_snapshot_keeps_grammatical_and_lexical_fields_only -q`

Expected: PASS.

Do not commit yet. Task 5 Step 7 commits Tasks 2–5 together.

---

### Task 3: `AnnotationEdit` and `AnnotationApplyService`

**Files:**
- Create: `oeapp/models/annotation_edit.py`
- Modify: `oeapp/models/__init__.py`
- Create: `oeapp/services/annotation_apply.py`
- Modify: `oeapp/services/__init__.py`
- Create: `tests/test_annotation_apply_service.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Annotation modal apply: before-snapshot, command, and Undo."""

from PySide6.QtGui import QUndoStack

from oeapp.commands import AnnotateTokenCommand, push_command
from oeapp.models import Annotation, AnnotationEdit, Idiom
from oeapp.services.annotation_apply import AnnotationApplyService
from tests.conftest import create_test_project


def _existing_token_annotation(db_session, pos: str):
    project = create_test_project(db_session, name="Apply", text="Se cyning")
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    annotation = Annotation.get_by_token(token.id)
    if annotation is None:
        annotation = Annotation(token_id=token.id)
    annotation.pos = pos
    annotation.save()
    db_session.refresh(token)
    return sentence, token


def test_begin_without_existing_annotation_is_empty() -> None:
    assert AnnotationApplyService().begin(None) == AnnotationEdit(before={})


def test_before_snapshot_is_taken_before_the_edit(db_session, qapp) -> None:
    _, token = _existing_token_annotation(db_session, "V")
    service = AnnotationApplyService()
    edit = service.begin(token.annotation)
    token.annotation.pos = "N"
    assert edit.before["pos"] == "V"


def test_undo_restores_an_edited_token_annotation(db_session, qapp) -> None:
    sentence, token = _existing_token_annotation(db_session, "V")
    service = AnnotationApplyService()
    edit = service.begin(token.annotation)
    applied = token.annotation
    applied.pos = "N"
    stack = QUndoStack()
    command = service.command_for(edit, applied, sentence.id)
    assert push_command(stack, command)
    assert Annotation.get_by_token(token.id).pos == "N"

    stack.undo()
    db_session.expire_all()
    assert Annotation.get_by_token(token.id).pos == "V"

    stack.redo()
    db_session.expire_all()
    assert Annotation.get_by_token(token.id).pos == "N"


def test_undo_restores_an_edited_idiom_annotation(db_session, qapp) -> None:
    project = create_test_project(db_session, name="Idiom", text="Se cyning")
    sentence = project.sentences[0]
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[1].id,
    )
    idiom.save()
    Annotation(idiom_id=idiom.id, pos="V").save()
    db_session.refresh(idiom)

    service = AnnotationApplyService()
    edit = service.begin(idiom.annotation)
    applied = idiom.annotation
    applied.pos = "N"
    stack = QUndoStack()
    assert push_command(stack, service.command_for(edit, applied, sentence.id))

    stack.undo()
    db_session.expire_all()
    assert Annotation.get_by_idiom(idiom.id).pos == "V"


def test_new_idiom_apply_creates_the_idiom_and_its_annotation(
    db_session, qapp
) -> None:
    project = create_test_project(db_session, name="New", text="Se cyning")
    sentence = project.sentences[0]
    tokens = list(sentence.tokens)
    new_idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[1].id,
    )
    applied = Annotation(pos="N")
    applied.idiom = new_idiom

    service = AnnotationApplyService()
    edit = service.begin(None)
    command = service.command_for(edit, applied, sentence.id)
    assert command.new_idiom is new_idiom
    assert push_command(QUndoStack(), command)

    assert command.idiom_id is not None
    assert Annotation.get_by_idiom(command.idiom_id).pos == "N"


def test_finish_copies_a_created_idiom_id() -> None:
    applied = Annotation(pos="N")
    command = AnnotateTokenCommand(
        token_id=None,
        idiom_id=7,
        before={},
        after={},
        new_idiom=Idiom(sentence_id=1, start_token_id=1, end_token_id=2),
        sentence_id=1,
    )
    AnnotationApplyService().finish(applied, command)
    assert applied.idiom_id == 7


def test_finish_leaves_an_existing_annotation_alone() -> None:
    applied = Annotation(pos="N", idiom_id=3)
    command = AnnotateTokenCommand(
        token_id=None, idiom_id=3, before={}, after={}, sentence_id=1
    )
    AnnotationApplyService().finish(applied, command)
    assert applied.idiom_id == 3
```

The `finish` tests build the command without pushing it. The push of a new idiom already sets `applied.idiom_id` through the `Idiom.annotation` cascade, so only a direct call proves `finish` itself copies the id. `AnnotateTokenCommand` is a plain `@dataclass` with no `__post_init__`, so building one needs no database.

- [ ] **Step 2: Verify they fail**

Run: `.venv/bin/pytest tests/test_annotation_apply_service.py -q`

Expected: collection error, `ImportError` for `AnnotationEdit`.

- [ ] **Step 3: Add `AnnotationEdit`**

`oeapp/models/annotation_edit.py`:

```python
"""Before-state of one annotation modal edit."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnnotationEdit:
    """
    The annotation fields as they were when the annotation modal opened.

    An edit carries this snapshot to the apply step, because the modal
    writes the new values onto the same annotation object.

    Args:
        before: Undo snapshot of the annotation before the edit, or empty
            when there was no annotation.

    """

    #: Undo snapshot of the annotation before the edit.
    before: dict[str, Any] = field(default_factory=dict)
```

Add `from oeapp.models.annotation_edit import AnnotationEdit` to `oeapp/models/__init__.py` and `"AnnotationEdit"` to `__all__`, in alphabetical order after `"Annotation"`.

- [ ] **Step 4: Add `AnnotationApplyService`**

`oeapp/services/annotation_apply.py`:

```python
"""Turn one annotation modal result into an undoable command."""

from oeapp.commands import AnnotateTokenCommand
from oeapp.models import Annotation, AnnotationEdit


class AnnotationApplyService:
    """
    Build the undoable command that saves one annotation modal result.

    The caller starts an edit before the modal opens, pushes the command
    this service builds, and calls :meth:`finish` once the push succeeds.
    """

    def begin(self, existing: Annotation | None) -> AnnotationEdit:
        """
        Snapshot an annotation before the modal edits it.

        Args:
            existing: Annotation the modal will edit, or ``None`` when the
                token or idiom has none yet.

        Returns:
            The edit, holding the before-snapshot.

        """
        if existing is None:
            return AnnotationEdit(before={})
        return AnnotationEdit(before=existing.undo_snapshot())

    def command_for(
        self, edit: AnnotationEdit, applied: Annotation, sentence_id: int | None
    ) -> AnnotateTokenCommand:
        """
        Build the command that saves the modal's result.

        Args:
            edit: Edit started when the modal opened.
            applied: Annotation the modal emitted.
            sentence_id: Sentence that holds the token or idiom.

        Returns:
            Command that writes ``applied`` and restores ``edit.before`` on
            Undo. It creates the idiom first when ``applied`` is for a new
            idiom (ADR 0002).

        """
        new_idiom = None
        if applied.idiom_id is None and applied.idiom is not None:
            new_idiom = applied.idiom
        return AnnotateTokenCommand(
            token_id=applied.token_id,
            idiom_id=applied.idiom_id,
            before=dict(edit.before),
            after=applied.undo_snapshot(),
            new_idiom=new_idiom,
            sentence_id=sentence_id,
        )

    def finish(self, applied: Annotation, command: AnnotateTokenCommand) -> None:
        """
        Record what a successful push created.

        Args:
            applied: Annotation the modal emitted.
            command: Command that was pushed successfully.

        Side Effects:
            Sets ``applied.idiom_id`` to the created idiom's id when the
            command created an idiom.

        """
        if command.new_idiom is not None:
            applied.idiom_id = command.idiom_id
```

Add `from oeapp.services.annotation_apply import AnnotationApplyService` to `oeapp/services/__init__.py` and `"AnnotationApplyService"` to `__all__`, before `"AnnotationPresetService"`.

- [ ] **Step 5: Verify the tests pass**

Run: `.venv/bin/pytest tests/test_annotation_apply_service.py tests/test_annotation.py -q`

Expected: PASS. These tests prove the service restores a snapshot taken before the edit. They do not prove the controller takes it before the modal writes. Task 4's `test_undo_after_editing_*_in_the_modal` tests are the Undo bug's regression tests.

---

### Task 4: Controller and card

**Files:**
- Modify: `oeapp/ui/sentence_card_controller.py`
- Modify: `oeapp/ui/sentence_card.py`
- Modify: `tests/test_sentence_card.py` (lines 523–611)
- Modify: `tests/test_annotation_integration.py` (line 44)

- [ ] **Step 1: Point the apply tests at the controller, and add a failure test**

In `tests/test_sentence_card.py`, add `from unittest.mock import patch` if it is not already imported, and `from oeapp.services.annotation_apply import AnnotationApplyService`.

In `test_annotation_applied_updates_existing_token_annotation`, replace `card._on_annotation_applied(new_ann)` with:

```python
edit = AnnotationApplyService().begin(existing)
card.controller.apply_annotation(edit, new_ann)
```

In `test_annotation_applied_updates_existing_idiom_annotation`, replace `card._on_annotation_applied(new_ann)` with:

```python
edit = AnnotationApplyService().begin(existing)
card.controller.apply_annotation(edit, new_ann)
```

In `test_idiom_annotation_applied_creates_idiom_via_command`, replace `card._on_idiom_annotation_applied(annotation)` with:

```python
card.controller.apply_annotation(AnnotationApplyService().begin(None), annotation)
```

Add this method to `TestSentenceCard`:

```python
    def test_failed_annotation_push_does_not_paint(
        self, db_session, qapp, mock_main_window
    ):
        """A failed push leaves the card unpainted and emits nothing."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[0]
        card = SentenceCard(
            sentence,
            undo_stack=QUndoStack(),
            main_window=mock_main_window,
            parent=None,
        )
        emitted: list[Annotation] = []
        card.annotation_applied.connect(emitted.append)
        before = card.oe_text_edit.annotations.get(token.id)

        with patch(
            "oeapp.ui.sentence_card_controller.push_command", return_value=False
        ):
            card.controller.apply_annotation(
                AnnotationApplyService().begin(None),
                Annotation(token_id=token.id, pos="N"),
            )

        assert emitted == []
        assert card.oe_text_edit.annotations.get(token.id) is before
```

Add the Undo bug's regression tests. They go through the controller's real `open_*_modal` methods with a stand-in modal that, like `AnnotationModal.save`, writes onto the annotation object it was given and emits that same object. Add these module-level helpers above `class TestSentenceCard`:

```python
class _Signal:
    """Minimal stand-in for a Qt signal."""

    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, slot) -> None:
        self._slots.append(slot)

    def emit(self, value) -> None:
        for slot in self._slots:
            slot(value)


class _InPlaceModal:
    """Stand-in modal that edits the given annotation in place, as save() does."""

    def __init__(self, *, annotation, **_kwargs) -> None:
        self.annotation = annotation
        self.annotation_applied = _Signal()

    def exec(self) -> int:
        self.annotation.pos = "N"
        self.annotation_applied.emit(self.annotation)
        return 1
```

Add these methods to `TestSentenceCard`:

```python
    def test_undo_after_editing_a_token_annotation_in_the_modal(
        self, db_session, qapp, mock_main_window, monkeypatch
    ):
        """Undo restores the value the token had before the modal edited it."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[0]
        existing = Annotation.get_by_token(token.id) or Annotation(token_id=token.id)
        existing.pos = "V"
        existing.save()
        db_session.refresh(token)
        card = SentenceCard(
            sentence,
            undo_stack=QUndoStack(),
            main_window=mock_main_window,
            parent=None,
        )
        monkeypatch.setattr(
            "oeapp.ui.sentence_card_controller.AnnotationModal", _InPlaceModal
        )

        card.controller.open_token_modal(token)
        assert Annotation.get_by_token(token.id).pos == "N"

        card.undo_stack.undo()
        db_session.expire_all()
        assert Annotation.get_by_token(token.id).pos == "V"

    def test_undo_after_editing_an_idiom_annotation_in_the_modal(
        self, db_session, qapp, mock_main_window, monkeypatch
    ):
        """Undo restores the value the idiom had before the modal edited it."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token1 = sentence.tokens[0]
        token2 = sentence.tokens[1]
        idiom = Idiom(
            sentence_id=sentence.id, start_token_id=token1.id, end_token_id=token2.id
        )
        idiom.save()
        Annotation(idiom_id=idiom.id, pos="V").save()
        db_session.refresh(idiom)
        card = SentenceCard(
            sentence,
            undo_stack=QUndoStack(),
            main_window=mock_main_window,
            parent=None,
        )
        monkeypatch.setattr(
            "oeapp.ui.sentence_card_controller.AnnotationModal", _InPlaceModal
        )

        card.controller.open_idiom_modal(idiom)
        assert Annotation.get_by_idiom(idiom.id).pos == "N"

        card.undo_stack.undo()
        db_session.expire_all()
        assert Annotation.get_by_idiom(idiom.id).pos == "V"
```

Against today's code both tests fail on the last assertion: the card reads its before-state from the object the stand-in already changed, so Undo writes N again. If `begin` were moved after `modal.exec()`, they would fail the same way.

In `tests/test_annotation_integration.py`, add `from functools import partial`, then replace line 44 with:

```python
    edit = sentence_card.controller.annotation_apply.begin(token.annotation)
    modal.annotation_applied.connect(
        partial(sentence_card.controller.apply_annotation, edit)
    )
```

- [ ] **Step 2: Verify the controller tests fail**

```bash
.venv/bin/pytest "tests/test_sentence_card.py::TestSentenceCard::test_annotation_applied_updates_existing_token_annotation" "tests/test_sentence_card.py::TestSentenceCard::test_annotation_applied_updates_existing_idiom_annotation" "tests/test_sentence_card.py::TestSentenceCard::test_idiom_annotation_applied_creates_idiom_via_command" "tests/test_sentence_card.py::TestSentenceCard::test_failed_annotation_push_does_not_paint" -q
```

Expected: 4 FAIL with `AttributeError: 'SentenceCardController' object has no attribute 'apply_annotation'`.

```bash
.venv/bin/pytest "tests/test_sentence_card.py::TestSentenceCard::test_undo_after_editing_a_token_annotation_in_the_modal" "tests/test_sentence_card.py::TestSentenceCard::test_undo_after_editing_an_idiom_annotation_in_the_modal" -q
```

Expected: 2 FAIL, each on its final `assert ... .pos == "V"` (the value is still `"N"`). This is the Undo bug. If either fails earlier, fix the test setup before going on.

- [ ] **Step 3: Inject the service into the controller**

Add imports to `oeapp/ui/sentence_card_controller.py`:

```python
from functools import partial

from oeapp.services.annotation_apply import AnnotationApplyService
```

Leave the existing runtime `from oeapp.models import Annotation, Idiom` line as it is. `AnnotationEdit` appears only in annotations in this module, and the module has `from __future__ import annotations`, so ruff's `TC001` requires it under the existing `if TYPE_CHECKING:` block:

```python
if TYPE_CHECKING:
    from oeapp.models import AnnotationEdit
    from oeapp.models.token import Token
    from oeapp.ui.sentence_card import SentenceCard
```

`AnnotationApplyService` is constructed at runtime, so its import stays at module level.

Replace `__init__` and the class docstring's `Args:` with:

```python
    """
    Coordinate sentence-card command execution and annotation modal routing.

    Args:
        card: Sentence card widget whose user actions are handled.

    Keyword Args:
        annotation_apply: Builds annotation commands. A new service is
            created when none is given.

    """

    def __init__(
        self,
        card: SentenceCard,
        *,
        annotation_apply: AnnotationApplyService | None = None,
    ) -> None:
        """
        Initialize controller for a sentence card.

        Args:
            card: Sentence card widget whose user actions are handled.

        Keyword Args:
            annotation_apply: Builds annotation commands.

        """
        #: Sentence card widget whose user actions are handled.
        self.card = card
        #: Builds the undoable command for an annotation modal result.
        self.annotation_apply = annotation_apply or AnnotationApplyService()
```

- [ ] **Step 4: Add `apply_annotation`**

```python
    def apply_annotation(self, edit: AnnotationEdit, annotation: Annotation) -> None:
        """
        Save one annotation modal result and paint it on the card.

        Args:
            edit: Edit started before the modal opened.
            annotation: Annotation the modal emitted.

        Side Effects:
            Pushes one undo command. On success, records a created idiom's
            id on ``annotation`` and has the card paint it.

        """
        card = self.card
        command = self.annotation_apply.command_for(
            edit, annotation, card.sentence.id
        )
        if not push_command(card.undo_stack, command):
            return
        self.annotation_apply.finish(annotation, command)
        card.show_applied_annotation(annotation)
```

- [ ] **Step 5: Start the edit before each modal and stop the bounce**

In `open_annotation_modal`, replace `card._open_idiom_modal(idiom)` with `self.open_idiom_modal(idiom)` (twice), `card._open_new_idiom_modal(start_order, end_order)` with `self.open_new_idiom_modal(start_order, end_order)`, and `card._open_token_modal(token)` with `self.open_token_modal(token)`.

`open_idiom_modal`: call `edit = self.annotation_apply.begin(idiom.annotation)` as the first line after `card = self.card`, before the existing `annotation = idiom.annotation` lines. Replace `modal.annotation_applied.connect(card._on_annotation_applied)` with:

```python
        modal.annotation_applied.connect(partial(self.apply_annotation, edit))
```

`open_new_idiom_modal`: after the early `return` for missing tokens, add `edit = self.annotation_apply.begin(None)`. Replace the `card._on_idiom_annotation_applied` connect with the same `partial(self.apply_annotation, edit)` line.

`open_token_modal`: after `annotation` is resolved from `token.annotation` or `Annotation.get_by_token`, add `edit = self.annotation_apply.begin(annotation)` before `AnnotationModal(...)`. Replace the `card._on_annotation_applied` connect with the `partial` line.

- [ ] **Step 6: Replace the card's apply pipeline with one paint method**

In `oeapp/ui/sentence_card.py`, delete `_open_idiom_modal`, `_open_new_idiom_modal`, `_open_token_modal`, `_extract_annotation_state`, `_execute_annotate_command`, `_finalize_annotation_update`, `_get_annotation_state`, `_on_idiom_annotation_applied`, and `_on_annotation_applied`. Keep `_open_annotation_modal`.

Add, in the "Annotation related methods" section:

```python
    def show_applied_annotation(self, annotation: Annotation) -> None:
        """
        Paint an annotation that has already been saved.

        Args:
            annotation: Annotation to show.

        Side Effects:
            Updates the token cache and token table, or re-renders the idiom.
            Emits ``annotation_applied`` and refreshes sentence highlighting.

        """
        if annotation.token_id:
            self.oe_text_edit.annotations[annotation.token_id] = annotation
            self.token_table.update_annotation(annotation)
        elif annotation.idiom_id:
            self.oe_text_edit.set_tokens()
            self.oe_text_edit.render_readonly_text()
        self.annotation_applied.emit(annotation)
        self.sentence_highlighter.highlight()
```

Delete `from oeapp.commands import AnnotateTokenCommand, push_command`. Change `from oeapp.models import Annotation, Idiom` to `from oeapp.models import Annotation`. After the deletions `Idiom` appears only in comments and docstrings. Run `rg -n "\bIdiom\b" oeapp/ui/sentence_card.py` to confirm no code reference is left.

- [ ] **Step 7: Run the apply tests**

```bash
.venv/bin/pytest "tests/test_sentence_card.py::TestSentenceCard::test_annotation_applied_updates_existing_token_annotation" "tests/test_sentence_card.py::TestSentenceCard::test_annotation_applied_updates_existing_idiom_annotation" "tests/test_sentence_card.py::TestSentenceCard::test_idiom_annotation_applied_creates_idiom_via_command" "tests/test_sentence_card.py::TestSentenceCard::test_failed_annotation_push_does_not_paint" "tests/test_sentence_card.py::TestSentenceCard::test_undo_after_editing_a_token_annotation_in_the_modal" "tests/test_sentence_card.py::TestSentenceCard::test_undo_after_editing_an_idiom_annotation_in_the_modal" -q
.venv/bin/pytest tests/test_annotation_integration.py tests/test_annotation_apply_service.py tests/test_runtime_session_freeze.py -q
```

Expected: both PASS. Run them as two commands. Do not combine files with `-k`; `-k` filters every listed file and deselects the integration, service, and freeze tests.

`tests/test_sentence_card.py::TestSentenceCard::test_double_click_selected_idiom_opens_idiom_modal` and `test_open_annotation_modal_uses_oe_selected_token_when_table_unselected` now fail, because `monkeypatch.setattr` raises on the deleted card methods. Task 5 fixes them. `tests/test_idioms.py::test_idiom_modal_navigation` still passes here: it sets `card._open_token_modal` as an instance attribute, which the modal's token link still finds until Task 5 changes both.

---

### Task 5: Modal routing tests, token link, ADR, commit

**Files:**
- Modify: `tests/test_sentence_card.py` (lines 311–312, 454–455)
- Modify: `tests/test_idioms.py` (line 222)
- Modify: `oeapp/ui/dialogs/annotation_modal.py` (`_on_token_link_clicked`, about line 804)
- Modify: `doc/source/architecture/adr_0011_runtime_session_freeze.rst`

- [ ] **Step 1: Patch the controller in the routing tests**

In `test_double_click_selected_idiom_opens_idiom_modal`:

```python
        monkeypatch.setattr(card.controller, "open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card.controller, "open_token_modal", lambda t: token_calls.append(t))
```

In `test_open_annotation_modal_uses_oe_selected_token_when_table_unselected`:

```python
        monkeypatch.setattr(card.controller, "open_idiom_modal", lambda idiom: None)
        monkeypatch.setattr(
            card.controller, "open_token_modal", lambda token: opened_tokens.append(token)
        )
```

In `tests/test_idioms.py::test_idiom_modal_navigation`, replace `card._open_token_modal = mock_open_token_modal` with:

```python
    card.controller.open_token_modal = mock_open_token_modal
```

- [ ] **Step 2: Verify only the token-link test fails**

```bash
.venv/bin/pytest "tests/test_sentence_card.py::TestSentenceCard::test_double_click_selected_idiom_opens_idiom_modal" "tests/test_sentence_card.py::TestSentenceCard::test_open_annotation_modal_uses_oe_selected_token_when_table_unselected" "tests/test_idioms.py::test_idiom_modal_navigation" -q
```

Expected: the two sentence-card tests PASS. `test_idiom_modal_navigation` FAILS on `assert opened_token == tokens[0]`, because `_on_token_link_clicked` still looks for `parent._open_token_modal`, which no longer exists, so it opens nothing. No modal is shown.

- [ ] **Step 3: Route the token link through the controller**

Replace the lines after `self.accept()` in `AnnotationModal._on_token_link_clicked` with:

```python
        controller = getattr(self.parent(), "controller", None)
        if controller is not None:
            controller.open_token_modal(token)
```

Keep the docstring. Keep the `cast` and `QObject` imports: other code in `annotation_modal.py` still uses both.

- [ ] **Step 4: Verify routing passes**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Record F7 in ADR 0011**

The F7 grilling on 2026-11-01 closed F7 with this change. Update every F7 sentence:

- Context: replace "F7 (resolve order 9) is unfinished." with "F7 (resolve order 9) landed on the implementation date. Annotation apply moved to ``AnnotationApplyService`` and ``Annotation.undo_snapshot``. The controller opens the modal and pushes the command." Keep the next two sentences ("F8's audit note said…" and "D4 does not require that injection."). Then replace the span from "F7 forbids new ``_get_session`` call sites in the UI." through "…keeps its ``_get_session`` inside ``Annotation.get_by_idiom``." with: "F7 added no ``_get_session`` call site in the UI. The card's ``Annotation.get_by_idiom`` call was removed, and no counted lookup moved."
- D3: replace "Moving ``Annotation.get_by_idiom`` from ``SentenceCard`` onto ``SentenceCardController`` does not change the allowlist." with "A UI call into a model classmethod, such as the controller's ``Annotation.get_by_token``, does not change the allowlist."
- D6: replace "F7 is still ahead." with "F7 has landed and added no counted lookup."
- Consequences: replace the bullet beginning "F1 landed under the freeze and added no lookup kind. F7 proceeds under the freeze." with "F1 and F7 landed under the freeze and added no lookup kind. A new ``app_context.session`` read fails the test until the dict matches."
- Related: change "F7 follows this freeze." to "F7 landed under this freeze."

Set `:Revised:` to the implementation date if it differs from Task 1's.

- [ ] **Step 6: Full suite, gates, graph**

```bash
source .venv/bin/activate
.venv/bin/pytest -q
.venv/bin/ruff check oeapp/db.py oeapp/models/annotation.py oeapp/models/annotation_edit.py oeapp/models/__init__.py oeapp/services/annotation_apply.py oeapp/services/__init__.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py oeapp/ui/dialogs/annotation_modal.py --output-format concise
.venv/bin/ruff check tests/test_annotation.py tests/test_sentence_card.py tests/test_idioms.py tests/test_annotation_integration.py --statistics | tail -1
.venv/bin/ruff check tests/test_annotation_apply_service.py --statistics
.venv/bin/mypy oeapp/models/annotation.py oeapp/models/annotation_edit.py oeapp/services/annotation_apply.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py oeapp/ui/dialogs/annotation_modal.py
python bin/check_napoleon_gate.py 2>&1 | rg "annotation\.py|annotation_edit|annotation_apply|models/__init__|services/__init__|sentence_card|annotation_modal" ; echo "touched-file violations exit=$?"
graphify update .
```

Expected:

- pytest: all pass. If a test outside this plan's files fails, run it on `master` before deciding this change caused it.
- ruff, product files: only `annotation_modal.py` `PLR0917` from Task 0. Fix anything else.
- ruff, edited test files: `Found N errors.` with N no higher than 363.
- ruff, new test file: only rule codes that already appear in `/tmp/ruff-tests-before.txt` (for example unused fixture arguments). Fix any other code.
- mypy: only the two `pos_form_system.py` errors from Task 0.
- The napoleon `rg` exits 1: no violation in a touched file.

- [ ] **Step 7: Commit**

```bash
git add oeapp/models/annotation.py oeapp/models/annotation_edit.py oeapp/models/__init__.py oeapp/services/annotation_apply.py oeapp/services/__init__.py oeapp/ui/sentence_card.py oeapp/ui/sentence_card_controller.py oeapp/ui/dialogs/annotation_modal.py tests/test_annotation.py tests/test_annotation_apply_service.py tests/test_sentence_card.py tests/test_idioms.py tests/test_annotation_integration.py doc/source/architecture/adr_0011_runtime_session_freeze.rst
git commit -m "$(cat <<'EOF'
Restore the old annotation on Undo after an edit.

The modal edits the loaded annotation in place, so the before-state was
read after the change. AnnotationApplyService now snapshots it when the
modal opens, and applying an annotation moves off the sentence card.

EOF
)"
```

Do not add `graphify-out/`.

---

## Self-review

- Spec item 1 is Task 1. Item 2 is Task 2. Items 3–4 are Task 3. Items 5–7, 9, and 11 are Task 4. Item 8 is Task 5. Item 10 is a stated non-change.
- Task 1 ships alone. Tasks 2–5 are one commit: Task 4 deletes card methods that Task 5's routing tests still patch, so the tree is red between Task 4 and Task 5.
- The Undo bug has two regression tests in Task 4 that go through the controller's `open_token_modal` and `open_idiom_modal` with a modal that edits in place. They fail on today's code and would fail again if `begin` moved after the modal ran. Task 3's service tests cover snapshot, Undo, and Redo at the service level, and two direct tests cover `finish`.
- The failure path that changes behavior has its own test.
- Placeholder scan: none. Node ids match `class TestSentenceCard` in `tests/test_sentence_card.py`.
