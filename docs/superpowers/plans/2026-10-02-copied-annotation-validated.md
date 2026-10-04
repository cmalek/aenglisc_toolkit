# Copied Annotation as a Validated AnnotationJson Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the untyped `dict[str, Any]` Copied Annotation on `AppContext` with a validated `AnnotationJson`, refusing (and logging) invalid copies and not carrying timestamps on paste.

**Architecture:** `AnnotationJson` moves to `oeapp.models` (own commit). `AppContext.copied_annotation` holds `AnnotationJson | None` and emits `model_dump(mode="json")` on its signal. `MainWindowActions.copy_annotation` validates `Annotation.to_json()` once (the setter boundary); `paste_annotation` dumps the stored model minus `created_at`/`updated_at` into `AnnotateTokenCommand.after`.

**Tech Stack:** Python, PySide6, pydantic v2 (already installed), structlog, pytest + pytest-qt.

**Spec:** `doc/source/architecture/adr_0006_copied_annotation.rst` (ADR 0006); glossary term **Copied Annotation** in `CONTEXT.md`.

## Global Constraints

- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`; use `/usr/bin/cd` to change directories.
- No new dependency.
- Data models live in `oeapp.models`; UI wiring in `oeapp.ui`; business logic in `oeapp.services`.
- Functions and methods ≤ 60 lines; docstrings per the repo Documentation Contract; `#:` comments on class attributes.
- Only `AnnotationJson` moves out of `oeapp/services/import_export_schema.py`; the rest of that schema stays (ADR 0006 D6).
- Project import/export JSON format must not change.
- After Python edits: ruff, mypy on touched files, `make napoleon-gate` (known unusable signal, see memory note: report, do not chase), `graphify update .`.
- Commit messages end with: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`

## Review Focus

- Copy of an annotation that fails the schema (unknown key): status "Cannot copy annotation: invalid data", previous Copied Annotation unchanged, error logged with payload (Task 3).
- Paste onto a token must not take the source annotation's `updated_at` (Task 2).
- Copying a different annotation replaces the earlier Copied Annotation and emits the signal; re-copying an identical one does not emit (Task 2).
- `reset()` clears the Copied Annotation and emits `None` on the signal (Task 2).
- Project export/import still round-trips with `AnnotationJson` in its new location (Task 1).

---

### Task 1: Move `AnnotationJson` to `oeapp.models`

**Files:**
- Create: `oeapp/models/annotation_json.py`
- Modify: `oeapp/services/import_export_schema.py:10-~66` (remove class, add import)
- Modify: `oeapp/models/__init__.py` (export)

**Interfaces:**
- Produces: `oeapp.models.annotation_json.AnnotationJson` and `oeapp.models.AnnotationJson` (same pydantic class, unchanged fields, `extra="forbid"`).

- [ ] **Step 1: Baseline** — `.venv/bin/pytest tests/test_import_export.py -q` — all pass.
- [ ] **Step 2: Create `oeapp/models/annotation_json.py`.** Cut the entire `AnnotationJson` class (from `class AnnotationJson(BaseModel):` through its last field `updated_at`) out of `import_export_schema.py` and paste it verbatim, with this header:

```python
"""Pydantic schema for one annotation's JSON payload."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
```

- [ ] **Step 3: Update `import_export_schema.py`.** Add `from oeapp.models.annotation_json import AnnotationJson` below the existing imports. `from pydantic import BaseModel, ConfigDict` stays (other classes use it). `TokenJson`/`IdiomJson` keep referencing `AnnotationJson` unchanged.
- [ ] **Step 4: Export from the package.** In `oeapp/models/__init__.py` add `from oeapp.models.annotation_json import AnnotationJson` (alphabetical, before `annotation_preset`) and `"AnnotationJson"` to `__all__`.
- [ ] **Step 5: Verify no import cycle and no behavior change**

Run: `.venv/bin/python -c "import oeapp.services.import_export_schema, oeapp.models"` — no error.
Run: `.venv/bin/pytest tests/test_import_export.py tests/test_annotation.py -q` — all pass (this covers the Review Focus round-trip).
`oeapp.models` modules import `oeapp.services` only lazily inside functions, so no import-time cycle is expected. If one appears, stop and report it: importing the submodule directly would not avoid it, because it still runs `oeapp/models/__init__.py`.

- [ ] **Step 6: Gates** — `.venv/bin/ruff check oeapp/models oeapp/services/import_export_schema.py`; `.venv/bin/mypy oeapp/models/annotation_json.py oeapp/services/import_export_schema.py`.
- [ ] **Step 7: Commit**

```bash
git add oeapp/models/annotation_json.py oeapp/models/__init__.py oeapp/services/import_export_schema.py
git commit -m "refactor: move AnnotationJson to oeapp.models

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `AppContext` holds a validated `AnnotationJson`

**Files:**
- Modify: `oeapp/state.py:72`, `:207-232`, `TYPE_CHECKING` block
- Modify: `oeapp/ui/main_window.py` (`copy_annotation` ~1079, `paste_annotation` ~1118-1143, imports)
- Test: `tests/test_state.py:43,85-91`, `tests/test_main_window.py:379-391`, `tests/test_annotation_copy_paste.py` (all raw-dict `copied_annotation` uses, ~lines 38, 129, 155, 185, 229)

**Interfaces:**
- Consumes: `oeapp.models.AnnotationJson` (Task 1).
- Produces: `AppContext.copied_annotation: AnnotationJson | None` (getter/setter); `copied_annotation_changed` emits `dict` (`model_dump(mode="json")`) or `None`.

- [ ] **Step 1: Write failing tests**

In `tests/test_state.py` add (import `AnnotationJson` from `oeapp.models`):

```python
def test_copied_annotation_signal_emits_plain_dict(self, db_session, qtbot):
    context = AppContext(session=db_session)
    with qtbot.waitSignal(context.copied_annotation_changed, timeout=1000) as blocker:
        context.copied_annotation = AnnotationJson(pos="N", root="cyning")
    payload = blocker.args[0]
    assert isinstance(payload, dict)
    assert payload["pos"] == "N"
    assert payload["root"] == "cyning"

def test_reset_clears_copied_annotation_and_emits_none(self, db_session, qtbot):
    context = AppContext(session=db_session)
    context.copied_annotation = AnnotationJson(pos="N")
    with qtbot.waitSignal(context.copied_annotation_changed, timeout=1000) as blocker:
        context.reset()
    assert blocker.args == [None]
    assert context.copied_annotation is None
```

```python
def test_copy_replaces_previous_and_emits_only_on_change(self, db_session, qtbot):
    context = AppContext(session=db_session)
    context.copied_annotation = AnnotationJson(pos="N")
    with qtbot.waitSignal(context.copied_annotation_changed, timeout=1000):
        context.copied_annotation = AnnotationJson(pos="V")
    assert context.copied_annotation == AnnotationJson(pos="V")
    with qtbot.assertNotEmitted(context.copied_annotation_changed):
        context.copied_annotation = AnnotationJson(pos="V")
```

Also change existing lines using `{"pos": "N"}` / `{"pos": "N", "root": "cyning"}` to `AnnotationJson(...)` equivalents (equality assertions compare models).

In `tests/test_annotation_copy_paste.py` add:

```python
def test_copy_annotation_stores_annotation_json(self, db_session, qapp, mock_main_window):
    del qapp
    project = create_test_project(db_session, name="Typed", text="Se cyning")
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    token.annotation.pos = "N"
    token.annotation.save()
    db_session.refresh(token)
    _select_card(db_session, mock_main_window, sentence, 0)

    assert _actions(mock_main_window).copy_annotation() is True
    copied = mock_main_window.app_context.copied_annotation
    assert isinstance(copied, AnnotationJson)
    assert copied.pos == "N"
```

and for paste (uses the real command path, like `test_paste_annotation_success_and_undo`):

```python
def test_paste_annotation_does_not_copy_source_timestamps(self, db_session, qapp, mock_main_window):
    del qapp
    project = create_test_project(db_session, name="Stamp", text="Se cyning")
    sentence = project.sentences[0]
    token = sentence.tokens[1]
    mock_main_window.app_context.copied_annotation = AnnotationJson(
        pos="N",
        created_at="2020-01-01T00:00:00+00:00",
        updated_at="2020-01-01T00:00:00+00:00",
    )
    _select_card(db_session, mock_main_window, sentence, 1)

    assert _actions(mock_main_window).paste_annotation() is True
    db_session.refresh(token)
    assert token.annotation.pos == "N"
    assert token.annotation.updated_at.year != 2020
```

(Add `from oeapp.models import Annotation, AnnotationJson` and `from structlog.testing import capture_logs` at the top of that test file as needed.)

In `tests/test_main_window.py::test_paste_annotation_state` the final assertion `mock_command.call_args.kwargs["after"] == copied_data` must become:

```python
copied_data = AnnotationJson(pos="V", root="gangan")
...
assert mock_command.call_args.kwargs["after"] == copied_data.model_dump(
    exclude={"created_at", "updated_at"}
)
```

and `test_copy_annotation_state` reads become `copied.pos == "N"` / `copied.modern_english_meaning == "king"`.

Update remaining raw-dict injections (`copied_annotation={"pos": "N"}`, `copied_data = {...}`, `copied["pos"]` style reads) to `AnnotationJson(...)` and attribute access (`copied.pos`, `copied.modern_english_meaning`).

- [ ] **Step 2: Run to see failures** — `.venv/bin/pytest tests/test_state.py tests/test_annotation_copy_paste.py tests/test_main_window.py -q` — new tests FAIL (dict stored / `model_dump` missing / timestamps present).
- [ ] **Step 3: Implement `state.py`.** Under `TYPE_CHECKING` add `from oeapp.models import AnnotationJson` (file already has `from __future__ import annotations`). Change `_copied_annotation` to `AnnotationJson | None`, update the `#:` comment, getter return type, and:

```python
@copied_annotation.setter
def copied_annotation(self, annotation: AnnotationJson | None) -> None:
    """
    Set or clear the Copied Annotation.

    Args:
        annotation: Validated annotation payload, or ``None`` to clear it.

    Side Effects:
        Emits :attr:`copied_annotation_changed` with a plain JSON dict (or
        ``None``) when the value changes.

    """
    if self._copied_annotation == annotation:
        return
    self._copied_annotation = annotation
    self.copied_annotation_changed.emit(
        None if annotation is None else annotation.model_dump(mode="json")
    )
```

Remove `Any` from the `typing` import only if now unused (check with ruff).

- [ ] **Step 4: Implement `main_window.py`.** Add `from oeapp.models.annotation_json import AnnotationJson`. In `copy_annotation` replace the assignment with:

```python
self.app_context.copied_annotation = AnnotationJson.model_validate(
    annotation.to_json()
)
```

In `paste_annotation` change the command construction to:

```python
command = AnnotateTokenCommand(
    token_id=token.id,
    before=before_state,
    after=copied_annotation.model_dump(exclude={"created_at", "updated_at"}),
)
```

- [ ] **Step 5: Run tests** — same command as Step 2 — all PASS. Then `.venv/bin/pytest tests -q -x` (full suite baseline is 0 failures).
- [ ] **Step 6: Gates** — ruff + mypy on `oeapp/state.py oeapp/ui/main_window.py` and the three test files.
- [ ] **Step 7: Commit**

```bash
git add oeapp/state.py oeapp/ui/main_window.py tests/test_state.py tests/test_main_window.py tests/test_annotation_copy_paste.py
git commit -m "feat: hold Copied Annotation as validated AnnotationJson

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Refuse and log an invalid copy

**Files:**
- Modify: `oeapp/ui/main_window.py` (`copy_annotation`; new helper `_validated_copied_annotation`)
- Test: `tests/test_annotation_copy_paste.py`

**Interfaces:**
- Consumes: `AnnotationJson` (Task 1), `AppContext.copied_annotation` (Task 2), `get_logger` from `oeapp.services.logs`.
- Produces: `MainWindowActions._validated_copied_annotation(self, token: "Token", annotation: "Annotation") -> AnnotationJson | None` — returns `None` after logging the error and showing the status message.

- [ ] **Step 1: Write failing tests** (reuse the setup of `test_copy_annotation_stores_annotation_json`; `Annotation` from `oeapp.models`, `capture_logs` from `structlog.testing`):

```python
def test_copy_invalid_payload_is_refused(self, db_session, qapp, mock_main_window, monkeypatch):
    del qapp
    project = create_test_project(db_session, name="Bad", text="Se cyning")
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    token.annotation.pos = "N"
    token.annotation.save()
    db_session.refresh(token)
    _select_card(db_session, mock_main_window, sentence, 0)
    actions = _actions(mock_main_window)
    assert actions.copy_annotation() is True  # a good copy first
    previous = mock_main_window.app_context.copied_annotation

    real_to_json = Annotation.to_json
    monkeypatch.setattr(
        Annotation, "to_json", lambda self: {**real_to_json(self), "bogus": 1}
    )
    with capture_logs() as logs:
        assert actions.copy_annotation() is True  # event handled

    mock_main_window.messages.show_message.assert_called_with(
        "Cannot copy annotation: invalid data"
    )
    assert mock_main_window.app_context.copied_annotation is previous
    entry = next(e for e in logs if e["event"] == "annotation.copy.invalid")
    assert entry["log_level"] == "error"
    assert entry["payload"]["bogus"] == 1
    assert entry["payload"]["pos"] == "N"
    assert entry["errors"]
```

`capture_logs` was verified to work here: `tests/conftest.py` calls `configure_logging()` (with `cache_logger_on_first_use=True`), and a logger warmed before `capture_logs()` still captured the entry, with `log_level: "error"` and the keyword fields. No fallback is needed.

- [ ] **Step 2: Run** — `.venv/bin/pytest tests/test_annotation_copy_paste.py -k invalid -v` — FAIL (`ValidationError` propagates).
- [ ] **Step 3: Implement.** In `main_window.py` add `from pydantic import ValidationError` and `from oeapp.services.logs import get_logger`. Add the helper to `MainWindowActions` and use it in `copy_annotation`:

```python
def _validated_copied_annotation(
    self, token: "Token", annotation: "Annotation"
) -> AnnotationJson | None:
    """
    Validate a token's annotation payload for the Copied Annotation.

    Args:
        token: Token that owns the annotation (for log context).
        annotation: Annotation being copied.

    Side Effects:
        On failure, logs the payload and shows a status message.

    Returns:
        The validated payload, or ``None`` when validation failed.

    """
    payload = annotation.to_json()
    try:
        return AnnotationJson.model_validate(payload)
    except ValidationError as exc:
        get_logger(self.__class__.__name__).error(
            "annotation.copy.invalid",
            token_id=token.id,
            annotation_id=annotation.id,
            payload=payload,
            errors=exc.errors(include_context=False),
        )
        self.messages.show_message("Cannot copy annotation: invalid data")
        return None
```

In `copy_annotation`, replace the Task 2 assignment block with:

```python
copied = self._validated_copied_annotation(token, annotation)
if copied is None:
    return True
self.app_context.copied_annotation = copied
self.messages.show_message("Annotation copied")
return True
```

(`annotation` is the local already bound from `token.annotation` earlier in the method, so mypy sees a non-None `Annotation`. Add `Annotation` to the `TYPE_CHECKING` imports in `main_window.py` next to `Token`: `from oeapp.models.annotation import Annotation`.)

- [ ] **Step 4: Run** — `.venv/bin/pytest tests/test_annotation_copy_paste.py tests/test_main_window.py tests/test_state.py -q` — PASS.
- [ ] **Step 5: Gates** — ruff + mypy on `oeapp/ui/main_window.py` and the test file.
- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/main_window.py tests/test_annotation_copy_paste.py
git commit -m "feat: refuse and log an invalid Copied Annotation

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Docs, help, final gates

**Files:**
- Modify: `doc/source/architecture/adr_0006_copied_annotation.rst` (Status → Accepted once Tasks 1-3 merged)
- Check: `oeapp/help/` pages and `doc/` for copy/paste annotation text

- [ ] **Step 1:** `grep -rniE "copy.*annotation|paste.*annotation" oeapp/help doc/source --include=* -l` — if a help page describes copy/paste, add one sentence: copying fails with "Cannot copy annotation: invalid data" and details go to the log. If none mention it, skip.
- [ ] **Step 2:** Set the ADR `:Status:` to `Accepted`.
- [ ] **Step 3: Full gates** — `.venv/bin/pytest tests -q`; `.venv/bin/ruff check oeapp tests`; `.venv/bin/mypy oeapp`; `make napoleon-gate` (report, do not chase); `graphify update .`.
- [ ] **Step 4: Commit** (`docs: accept ADR 0006` plus any help change, with the Co-Authored-By line).
