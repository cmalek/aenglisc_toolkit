# Project Export Reading-Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `Project → Export` into one submenu with three items: JSON Project file, Old English `.txt`, and Translation `.txt`, per ADR 0003.

**Architecture:** A new export-only `ReadingTextExporter` in `oeapp/services/export_reading_text.py` builds UTF-8 strings from persisted `Project.sentences` using `oeapp.models.text_flow` (`visible_titles`, `sentence_separator_kind`, `plain_text_separator`). Full Translation widgets stay independent (notes and annotation markup stay in the window). Menu actions save first, then write files. Import rejects `.txt` with copy that names the three export kinds.

**Tech Stack:** Python 3, PySide6, SQLAlchemy, pytest, existing `text_flow` helpers. No new packages.

**Spec:** `doc/source/architecture/adr_0003_project_export_reading_text.rst` (binding). Glossary: `CONTEXT.md` (Project Export, Old English Text Export, Translation Export).

## Global Constraints

- Do not scrape or call `FullProjectOldEnglishTextEdit` / `FullProjectModernEnglishTextEdit`.
- Both `.txt` payloads exclude notes and annotation markup; use `sentence.text_oe` / `sentence.text_modern`, never token walks or note superscripts.
- Official titles only: `visible_titles()` (auto titles omitted).
- Verse indent is four spaces per non-empty line (`"    "`).
- Verse numbers in `.txt` files: print the integer `5`, `10`, `15`, … after every five counted verse lines; if the last group has fewer than five lines, print no number. This may diverge from stored `verse_line_end` and from the Full Translation window.
- Translation: empty `text_modern` (None or blank) emits no `[...]`; do not print a verse number when the sentence being closed has empty Modern English.
- Default names: `ProjectExporter.sanitize_filename(project.name) + ".json"` (unchanged), `+ "-oe.txt"`, `+ "-translation.txt"`.
- Menu: parent `&Export` (submenu, no ellipsis); children `&Project file...`, `&Old English...`, `&Translation...`; no new shortcut (`Ctrl+E` stays File DOCX).
- Disable Old English and Translation when the project has no sentences; disable Translation when no sentence has non-blank `text_modern`. Refresh enablement on `load_project` **and** after `autosave` (so typing a translation or appending OE text does not leave items stuck disabled).
- Save (`MainWindowActions.autosave`) before any of the three Export writes; then re-read persisted sentences for render/write.
- `.txt` is paste/email/plain interchange; File DOCX and Full Translation PDF remain formatted / side-by-side copies.
- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. `/usr/bin/cd` to change directories.
- Napoleon docstrings + `#:` on new attributes; `make napoleon-gate` after Python edits.
- After Python changes: `graphify update .`

## File map

| File | Role |
|------|------|
| Create `oeapp/services/export_reading_text.py` | `ReadingTextExporter` — render + write UTF-8 `.txt` |
| Modify `oeapp/services/__init__.py` | Export `ReadingTextExporter` |
| Modify `oeapp/services/import_export.py` | Reject `.txt` / `.text` before JSON parse |
| Modify `oeapp/ui/menus.py` | `Export` submenu, enablement helpers |
| Modify `oeapp/ui/main_window.py` | Save-then-export actions; refresh menu enablement on load |
| Modify `oeapp/help/topics/project-export-import.md` | Three Project Export items + cannot import `.txt` |
| Test `tests/test_export_reading_text.py` | Layout, titles, verse numbers, empty ME |
| Test `tests/test_import_export.py` | Import rejection copy |
| Test `tests/test_menus.py` | Submenu labels + enablement |
| Test `tests/test_main_window.py` | Save-before-export + dialog defaults (mocked `QFileDialog`) |

---

### Task 1: `ReadingTextExporter` (strings only)

**Files:**
- Create: `oeapp/services/export_reading_text.py`
- Modify: `oeapp/services/__init__.py`
- Test: `tests/test_export_reading_text.py`

**Interfaces:**
- Consumes: `Project.sentences` (iterate `sorted(project.sentences, key=lambda s: s.display_order)`); `visible_titles`, `sentence_separator_kind`, `plain_text_separator` from `oeapp.models.text_flow`; `Sentence.text_oe`, `Sentence.text_modern`, `Sentence.is_verse`.
- Produces:

```python
class ReadingTextExporter:
    VERSE_NUMBER_INTERVAL: Final[int] = 5
    VERSE_INDENT: Final[str] = "    "

    def render_old_english(self, project: Project) -> str: ...
    def render_translation(self, project: Project) -> str: ...
    def write_utf8(self, path: Path, text: str) -> None: ...
```

`write_utf8` writes UTF-8 with `\n` newlines, no BOM. If `path.suffix.lower() != ".txt"`, append `.txt` (mirror DOCX extension enforcement). On `OSError` / `PermissionError`, raise `ValueError` with `Failed to write export file:` plus the OS message (same pattern as `ProjectExporter.export_project_json`).

Render algorithm (both methods share a private `_render(project, *, translation: bool) -> str`):

1. `parts: list[str] = []`, `previous = None`, `verse_line_count = 0`.
2. For each sentence in display order:
   - `titles = visible_titles(previous, sentence)`
   - If titles: if `parts` non-empty, append `"\n\n"`; append `"\n".join(titles) + "\n"`.
   - Append `plain_text_separator(sentence_separator_kind(previous, sentence, bool(titles)))`.
   - Body: OE → `sentence.text_oe`; Translation → `sentence.text_modern or ""` (never `"[...]"`).
   - If `sentence.is_verse` and body: indent with `VERSE_INDENT` on each non-empty line (same rule as `_indent_multiline_plain` in `oeapp/ui/full_translation_window.py`).
   - Append body.
   - If `sentence.is_verse`: `n = len(body.split("\n")) if body else 0`; `verse_line_count += n`; if `n` and `verse_line_count % VERSE_NUMBER_INTERVAL == 0`: emit `"\n" + str(verse_line_count)` **unless** `translation` and not `(sentence.text_modern or "").strip()`.
   - `previous = sentence`.
3. Return `"".join(parts)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export_reading_text.py`:

```python
# ruff: noqa: ARG002, S101

from __future__ import annotations

from oeapp.models.note import Note
from oeapp.models.project import Project
from oeapp.models.token import Token
from oeapp.services.export_reading_text import ReadingTextExporter


def _mark_verse(sentence, start: int, end: int) -> None:
    sentence.verse_line_start = start
    sentence.verse_line_end = end


def _require_n_sentences(project: Project, n: int) -> None:
    assert len(project.sentences) == n, (
        f"splitter yielded {len(project.sentences)} sentences, need {n}; "
        "build with Sentence.create like tests/test_export_docx.py"
    )


class TestReadingTextExporter:
    def test_prose_uses_text_oe_without_notes(self, db_session) -> None:
        project = Project.create(name="Prose", text="Hwæt. We Gardena.")
        first = project.sentences[0]
        token = Token.list(first.id)[0]
        Note.create(
            sentence_id=first.id,
            start_token_id=token.id,
            end_token_id=token.id,
            note_text_md="should not appear",
        )
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "Hwæt" in text
        assert "should not appear" not in text

    def test_omits_auto_titles_includes_manual(self, db_session) -> None:
        project = Project.create(name="Titles", text="Line one.")
        sentence = project.sentences[0]
        section = sentence.paragraph.section
        chapter = section.chapter
        chapter.title = "Auto Chapter"
        chapter.title_auto = True
        section.title = "Lines 1-25"
        section.title_auto = True
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "Auto Chapter" not in text
        assert "Lines 1-25" not in text

        chapter.title = "Beowulf"
        chapter.title_auto = False
        section.title = "The opening"
        section.title_auto = False
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert text.startswith("Beowulf\nThe opening\n")

    def test_verse_indent_and_every_five_numbers(self, db_session) -> None:
        lines = " ".join(f"Line{i}." for i in range(1, 8))
        project = Project.create(name="Verse", text=lines)
        _require_n_sentences(project, 7)
        for i, sentence in enumerate(project.sentences, start=1):
            _mark_verse(sentence, i, i)
            sentence.text_oe = f"OE{i}"
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "    OE1" in text
        assert "\n5\n" in text or text.endswith("\n5")
        assert "\n5\n    OE6" in text or "5\n    OE6" in text
        assert "\n7" not in text  # short remainder, no number

    def test_translation_empty_no_placeholder_no_number(self, db_session) -> None:
        lines = " ".join(f"Line{i}." for i in range(1, 6))
        project = Project.create(name="EmptyME", text=lines)
        _require_n_sentences(project, 5)
        for i, sentence in enumerate(project.sentences, start=1):
            _mark_verse(sentence, i, i)
            sentence.text_oe = f"OE{i}"
            sentence.text_modern = "ok" if i < 5 else None
        db_session.commit()
        text = ReadingTextExporter().render_translation(project)
        assert "[...]" not in text
        assert "ok" in text
        assert not text.rstrip().endswith("5")

    def test_translation_uses_modern_english_body(self, db_session) -> None:
        project = Project.create(name="MEBody", text="Hwæt.")
        project.sentences[0].text_modern = "Listen."
        db_session.commit()
        text = ReadingTextExporter().render_translation(project)
        assert "Listen." in text
        assert "Hwæt" not in text

    def test_write_utf8_forces_txt(self, db_session, tmp_path) -> None:
        project = Project.create(name="Write", text="A.")
        path = tmp_path / "out"
        exporter = ReadingTextExporter()
        exporter.write_utf8(path, exporter.render_old_english(project))
        written = tmp_path / "out.txt"
        assert written.exists()
        assert "A" in written.read_text(encoding="utf-8")
```

If `_require_n_sentences` fails, do not weaken the assert — construct seven (or five) verse sentences with `Sentence.create` as in `tests/test_export_docx.py::test_export_hides_auto_titles_and_numbers_verse_stanzas`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_export_reading_text.py -v`

Expected: FAIL collecting or importing `ReadingTextExporter`.

- [ ] **Step 3: Implement `ReadingTextExporter`**

Add `oeapp/services/export_reading_text.py` with Napoleon class/method docs and `#:` on `VERSE_NUMBER_INTERVAL` / `VERSE_INDENT`. Export the class from `oeapp/services/__init__.py` (`__all__` too).

Keep methods ≤ 60 lines: split indent helper and verse-number helper.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_export_reading_text.py -v`

Expected: PASS.

- [ ] **Step 5: Quality gate + graphify + commit**

Run:

```bash
.venv/bin/ruff check oeapp/services/export_reading_text.py oeapp/services/__init__.py tests/test_export_reading_text.py
.venv/bin/mypy oeapp/services/export_reading_text.py
make napoleon-gate
graphify update .
```

```bash
git add oeapp/services/export_reading_text.py oeapp/services/__init__.py tests/test_export_reading_text.py
git commit -m "$(cat <<'EOF'
Add export-only reading-text renderer for OE and Translation shares.

EOF
)"
```

---

### Task 2: Import rejects reading-text files

**Files:**
- Modify: `oeapp/services/import_export.py` (`ProjectImporter._load_json_payload`)
- Test: `tests/test_import_export.py`

**Interfaces:**
- Consumes: `Path` passed to `import_project_json` / `_load_json_payload`.
- Produces: `ValueError` with this exact message (`READING_TEXT_IMPORT_ERROR`) when the file cannot be treated as Project Export JSON:

```
This file is not a Project Export. Old English Text Export and Translation Export are reading copies and cannot be imported. Choose a .json or .json.gz Project file.
```

Raise it when `path.suffix.lower()` is `.txt` or `.text`, **and** when `json.loads` raises `JSONDecodeError` (Import dialog still has `All Files (*)`). Keep gzip/read `OSError` messages as they are. Valid JSON that fails schema/`migration_version` keeps existing errors (that is a broken Project Export, not a reading copy).

- [ ] **Step 1: Write the failing test**

Add to `TestProjectImporter` in `tests/test_import_export.py`:

```python
    def test_import_rejects_reading_text_txt(self, db_session, tmp_path) -> None:
        path = tmp_path / "Beowulf-oe.txt"
        path.write_text("    Hwæt\n5\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Old English Text Export"):
            ProjectImporter().import_project_json(str(path))

    def test_import_rejects_non_json_via_all_files(self, db_session, tmp_path) -> None:
        path = tmp_path / "notes-without-suffix"
        path.write_text("plain reading copy", encoding="utf-8")
        with pytest.raises(ValueError, match="Old English Text Export"):
            ProjectImporter().import_project_json(str(path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_import_export.py::TestProjectImporter::test_import_rejects_reading_text_txt tests/test_import_export.py::TestProjectImporter::test_import_rejects_non_json_via_all_files -v`

Expected: FAIL (`Failed to load project data` or JSON decode, not the new copy).

- [ ] **Step 3: Implement the check**

Define the message once on `ProjectImporter` (class constant). At the top of `_load_json_payload`, if suffix is `.txt`/`.text`, raise it. In the existing `json.loads` `except`, raise the same message from `JSONDecodeError` (do not swallow `UnicodeDecodeError` into that copy unless it is also clearly non-JSON text; mapping `JSONDecodeError` is required).

- [ ] **Step 4: Run importer tests**

Run: `.venv/bin/pytest tests/test_import_export.py -v`

Expected: PASS (including existing gzip/JSON cases).

- [ ] **Step 5: Quality gate + graphify + commit**

```bash
.venv/bin/ruff check oeapp/services/import_export.py tests/test_import_export.py
.venv/bin/mypy oeapp/services/import_export.py
make napoleon-gate
graphify update .
git add oeapp/services/import_export.py tests/test_import_export.py
git commit -m "$(cat <<'EOF'
Reject reading-text .txt files on Project Import with named export kinds.

EOF
)"
```

---

### Task 3: Export submenu, enablement, save-then-write

**Files:**
- Modify: `oeapp/ui/menus.py` (`ProjectMenu`)
- Modify: `oeapp/ui/main_window.py` (`MainWindow.load_project`, `MainWindowActions`)
- Test: `tests/test_menus.py`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `ReadingTextExporter.render_old_english` / `render_translation` / `write_utf8`; `ProjectExporter.sanitize_filename`; existing `export_project_json`; `MainWindowActions.autosave`.
- Produces:
  - `ProjectMenu.export_submenu: QMenu`
  - `ProjectMenu.export_project_file_action`, `export_old_english_action`, `export_translation_action: QAction`
  - `ProjectMenu.update_reading_export_enabled(project: Project | None) -> None`
  - `MainWindowActions.export_old_english_text() -> bool`
  - `MainWindowActions.export_translation_text() -> bool`
  - `export_project_json` / the two new methods call `self.autosave()` after the no-project check and **before** the file dialog; then `update_reading_export_enabled` on the current project; then render from DB.

**Naming:** `MainMenu.project_menu` is the `ProjectMenu` instance (`oeapp/ui/menus.py` `self.project_menu = ProjectMenu(...)`). That instance also has `self.project_menu` as the `QMenu`. From `MainWindow` use `self.main_menu.project_menu.update_reading_export_enabled(project)` — never invent `project_menu_handler`. Do not call enablement on the inner `QMenu`.

Enablement: `project is None or not project.sentences` → OE and Translation disabled. Translation also disabled when `not any((s.text_modern or "").strip() for s in project.sentences)`. Project file item stays enabled (warn on click if no project, same as today). Refresh on `load_project` and at the start of each of the three export methods after `autosave` (covers append-OE / typed translation without a full reload). If after save Translation is still disabled, `export_translation_text` should `show_warning` and return `False` without opening a dialog (menu should already prevent the click).

Dialogs:

| Item | Title | Default name | Filter |
|------|--------|----------------|--------|
| Project file | `Export Project` | `{sanitized}.json` | unchanged JSON/gz |
| Old English | `Export Old English Text` | `{sanitized}-oe.txt` | `Text Files (*.txt);;All Files (*)` |
| Translation | `Export Translation` | `{sanitized}-translation.txt` | same txt filter |

Cancel (`file_path` empty) → `False`, no write, no success toast. Force `.txt` via `write_utf8`. Success copy: `show_information` like JSON, naming the path.

Call `update_reading_export_enabled` from `MainWindow.load_project` after `project_ui.load`, and from `ProjectMenu.__init__`/`build` with `Project.get(current_id)` if any.

- [ ] **Step 1: Write the failing tests**

`tests/test_menus.py` — add to `class TestProjectMenu`:

```python
    def test_project_menu_export_submenu_items(self, db_session, mock_main_window, qapp):
        main_menu = MainMenu(mock_main_window)
        project_menu = ProjectMenu(main_menu, mock_main_window)
        texts = [a.text() for a in project_menu.project_menu.actions() if not a.isSeparator()]
        assert "&Export..." not in texts
        assert "&Export" in texts
        child_texts = [a.text() for a in project_menu.export_submenu.actions()]
        assert child_texts == ["&Project file...", "&Old English...", "&Translation..."]

    def test_reading_export_disabled_without_sentences(
        self, db_session, mock_main_window, qapp
    ):
        from oeapp.models.project import Project
        from tests.conftest import create_test_project

        main_menu = MainMenu(mock_main_window)
        project_menu = ProjectMenu(main_menu, mock_main_window)
        empty = create_test_project(db_session, name="EmptyMenu", text="")
        project_menu.update_reading_export_enabled(empty)
        assert not project_menu.export_old_english_action.isEnabled()
        assert not project_menu.export_translation_action.isEnabled()

        filled = Project.create(name="FilledMenu", text="Hwæt.")
        project_menu.update_reading_export_enabled(filled)
        assert project_menu.export_old_english_action.isEnabled()
        assert not project_menu.export_translation_action.isEnabled()
        filled.sentences[0].text_modern = "Lo."
        db_session.commit()
        project_menu.update_reading_export_enabled(filled)
        assert project_menu.export_translation_action.isEnabled()
```

If `Project.create(..., text="")` is invalid, use a project with sentences deleted or the existing empty-project helper from `tests/test_export_docx.py::test_export_empty_project_creates_document`.

`tests/test_main_window.py` — follow `test_export_callback_uses_current_project` (`create_test_project`, `create_test_sentence`, mock `QFileDialog.getSaveFileName`, mock messages). Fixture is `main_window`, not a nonexistent extra window fixture. **Do not** replace `autosave` with a no-op.

```python
    def test_export_old_english_persists_then_writes(
        self, main_window, db_session, tmp_path, monkeypatch
    ):
        from oeapp.models.sentence import Sentence
        from tests.conftest import create_test_project, create_test_sentence

        project = create_test_project(db_session, name="Save First")
        sentence = create_test_sentence(db_session, project.id, "Hwæt.")
        main_window.app_context.current_project_id = project.id
        main_window.load_project(project)
        sentence.text_oe = "UNSAVED"
        db_session.flush()  # dirty in session; autosave/project.save must commit

        out = tmp_path / "Save_First-oe.txt"
        monkeypatch.setattr(
            "oeapp.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args, **_kwargs: (str(out), "Text Files (*.txt)"),
        )
        monkeypatch.setattr(main_window.messages, "show_warning", MagicMock())
        monkeypatch.setattr(main_window.messages, "show_information", MagicMock())
        monkeypatch.setattr(main_window.messages, "show_error", MagicMock())

        assert main_window.action_service.export_old_english_text() is True
        assert out.exists()
        assert "UNSAVED" in out.read_text(encoding="utf-8")
        db_session.expire_all()
        assert Sentence.get(sentence.id).text_oe == "UNSAVED"

    def test_export_old_english_cancel_writes_nothing(
        self, main_window, db_session, tmp_path, monkeypatch
    ):
        from tests.conftest import create_test_project, create_test_sentence

        project = create_test_project(db_session, name="Cancel OE")
        create_test_sentence(db_session, project.id, "Hwæt.")
        main_window.app_context.current_project_id = project.id
        monkeypatch.setattr(
            "oeapp.ui.main_window.QFileDialog.getSaveFileName",
            lambda *_args, **_kwargs: ("", ""),
        )
        assert main_window.action_service.export_old_english_text() is False
        assert list(tmp_path.iterdir()) == []
```

If `load_project` plus in-session dirty state is awkward, set `text_oe` on the ORM object, call real `autosave`, then export — the file must contain the new string. Do not monkeypatch `autosave` away.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_menus.py::TestProjectMenu::test_project_menu_export_submenu_items tests/test_menus.py::TestProjectMenu::test_reading_export_disabled_without_sentences tests/test_main_window.py::TestMainWindowInitialization::test_export_old_english_persists_then_writes tests/test_main_window.py::TestMainWindowInitialization::test_export_old_english_cancel_writes_nothing -v`

Put the persist/cancel tests on `TestMainWindowInitialization` next to `test_export_callback_uses_current_project`. Put the menu tests on `TestProjectMenu`.

Expected: FAIL on missing submenu / missing methods.

- [ ] **Step 3: Implement menu and actions**

`ProjectMenu`: replace single `&Export...` with `export_submenu = self.project_menu.addMenu("&Export")` and three `QAction`s wired to `export_project_json`, `export_old_english_text`, `export_translation_text`.

`MainWindowActions`: add the two methods (clone `export_project_json` structure: no project → `show_warning("No project open")`; dialog; `ReadingTextExporter`; information toast). Call `self.autosave()` at the start of all three export methods after the no-project check.

`load_project`: `self.main_menu.project_menu.update_reading_export_enabled(project)` (`MainMenu.project_menu` is the `ProjectMenu` instance).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_menus.py tests/test_main_window.py tests/test_export_reading_text.py -v`

Expected: PASS.

- [ ] **Step 5: Quality gate + graphify + commit**

```bash
.venv/bin/ruff check oeapp/ui/menus.py oeapp/ui/main_window.py tests/test_menus.py tests/test_main_window.py
.venv/bin/mypy oeapp/ui/menus.py oeapp/ui/main_window.py
make napoleon-gate
graphify update .
git add oeapp/ui/menus.py oeapp/ui/main_window.py tests/test_menus.py tests/test_main_window.py
git commit -m "$(cat <<'EOF'
Add Project Export submenu for JSON, Old English, and Translation files.

EOF
)"
```

---

### Task 4: Help copy for the three Project Export items

**Files:**
- Modify: `oeapp/help/topics/project-export-import.md`
- Generated: `make help-assets` (rewrites `oeapp/help/assets/project-export-import.html` and the macOS help copy)

**Interfaces:**
- Consumes: ADR 0003 menu labels and job split.
- Produces: Help that says `Project → Export` has three items; `.txt` cannot be imported; JSON remains Toolkit interchange; DOCX/PDF stay separate.

- [ ] **Step 1: Rewrite the Project Menu section in the markdown topic**

In `oeapp/help/topics/project-export-import.md`:

- Fix “Three Types of Export” / “two different export options” so counts are true: File DOCX, Full Translation PDF, and **Project → Export** (three items).
- Replace `### JSON Export (Project Menu)` and `## Exporting a Project` step list with:

```markdown
### Project Export submenu (Project Menu)

- **Location**: Project → Export
- **Items**:
  - **Project file...** — JSON (optionally `.json.gz`). Complete project data for sharing between Toolkit installations or archiving that project. This is a Project Export; it can be imported. Default name: `my_project.json`.
  - **Old English...** — UTF-8 `.txt` reading copy of the Old English text (official titles, verse indent, a line number every five verse lines). No notes or annotations. Default name: `my_project-oe.txt`. Disabled if the project has no sentences.
  - **Translation...** — UTF-8 `.txt` reading copy of the Modern English translation (same layout rules; empty sentences stay empty). Default name: `my_project-translation.txt`. Disabled if there is no translation yet.
- **Not for**: side-by-side reading (use File → DOCX Export or Full Translation → Export PDF).
- **Import**: only Project file JSON / `.json.gz`. Old English and Translation `.txt` files cannot recreate a project.
```

Update Import steps: if the user selects a `.txt`, they get an error naming those export kinds.

Do not call JSON a Backup (Backup is database-wide).

Grep `oeapp/help/topics` for `Project → Export...`. Only `project-export-import.md` currently has it; if another topic grows a stale pointer, update it in this task. Leave File → DOCX `Export...` / `Ctrl+E` alone.

- [ ] **Step 2: Rebuild help assets**

Run: `make help-assets`

Expected: `project-export-import.html` in assets and macos help bundle mention `Project file`.

- [ ] **Step 3: Commit**

```bash
git add oeapp/help/topics/project-export-import.md oeapp/help/assets/project-export-import.html oeapp/help/macos
git commit -m "$(cat <<'EOF'
Document Project Export submenu and non-importable reading-text files.

EOF
)"
```

---

## Spec coverage (self-review)

| ADR 0003 decision | Task |
|-------------------|------|
| Export submenu, three items, mnemonics, no new shortcut | 3 |
| Project file JSON unchanged (plus save-first) | 3 |
| OE/Translation `.txt` names, dialogs, force `.txt` | 1 + 3 |
| Export-only service; no Full Translation coupling | 1 |
| `visible_titles`; no auto titles | 1 |
| Every-five verse numbers; short last stanza silent | 1 |
| No `[...]`; no number on empty ME verse | 1 |
| No notes/annotation markup | 1 |
| Save before export | 3 |
| Disable empty / no-translation items | 3 |
| Import reject reading-text / non-JSON decode | 2 |
| Help job split vs DOCX/PDF | 4 |
| Enablement refresh after save | 3 |
| Cancel dialog writes nothing | 3 |
| Write failures surface as Export Error | 1 + 3 |
| Translation body is Modern English | 1 |
| No Source/Project Notes header | (out of scope — do not add) |
| No paired OE+ME `.txt` | (out of scope) |
