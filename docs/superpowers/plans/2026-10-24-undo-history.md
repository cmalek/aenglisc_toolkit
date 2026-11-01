# Undo History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `CommandManager` with one project-scoped `QUndoStack`, and make one Modern English Typed Run a single Undo step that still lands on the sentence it changed.

**Architecture:** Existing command dataclasses keep their database behavior. A `QUndoCommand` wrapper is what the stack owns. `AppContext` holds one stack, clears it when the open project changes or Old English text is appended, and does not keep a second list of commands. A `TypedRun` remembers which translation command is still open so later keystrokes merge into it. An `UndoPresenter` writes an in-place translation undo into the open editor, or loads that sentence's section when the card is gone. After a command that deletes a sentence or retokenizes, a walk marks dead stack entries obsolete and retargets annotation locators. Qt removes obsolete commands on the next `push`, `undo`, `redo`, or `setIndex` (Qt 6.8 `QUndoCommand.setObsolete`).

**Tech Stack:** Python 3.14, PySide6 6.12 (`QUndoStack` and `QUndoCommand` from `PySide6.QtGui`), pytest-qt, the existing command dataclasses.

**Spec:** `doc/source/architecture/adr_0009_project_scoped_qundostack.rst` and `doc/source/architecture/adr_0010_typed_run_undo.rst`. `CONTEXT.md` defines **Undo History** and **Typed Run**.

## Global Constraints

- Undo limit is 50 on the application stack. `tests/conftest.py` `command_setup` uses 10.
- A command whose `execute()` returns `False` does not remain on the stack.
- The stack owns commands after `push()`. Do not keep a second Python list of them.
- No command macros, no `beginMacro` / `endMacro`, and no `setClean`. Idiom creation stays the one command ADR 0002 already specified. Annotation paste and a full menu bar are out of scope.
- Edit menu actions use `QKeySequence.StandardKey` and `QAction.MenuRole.NoRole`, set before the action is added to the menu. Qt prefixes the command text with "Undo " and "Redo ".
- Command text is the plain list in ADR 0009 D3, with no database ids.
- Only the two `keybindings.html` files change. Other help pages that mention `Ctrl+R` stay as they are.
- `EditSentenceCommand` for `text_modern` stores absolute `before` and `after`. `mergeWith` keeps the original `before` and replaces `after`. It does not store a delta.
- Database sentence ids are locators. `display_order_changes` and the before-state dicts are that command's own undo snapshot. Do not rewrite snapshots so a later insert "renumbers" them.
- Undo and Redo of a Typed Run close the run before the stack moves. The write into the editor is guarded so `textChanged` does not push another command.
- Status text stays "Undone", "Redone", and "Undo failed" / "Redo failed".
- New Python follows the napoleon docstring contract. Methods stay at or under 60 lines. UI stays in `oeapp.ui`. No new ORM model and no Alembic migration.
- Package decision: reuse installed PySide6. The catalog search for a separate undo library returned `no_match`. Do not add a dependency.
- Tests: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest`. After each Python task: `.venv/bin/ruff check` and `.venv/bin/mypy` on the touched files, then `make napoleon-gate`.

## Review Focus

These are the failures a person would hit that the spec implies and that are easy to miss. Each one has a test in the task named here.

- Undo after a chapter or section change rewrites whatever sentence is now on screen. Expected: load the edited sentence's section, scroll to its card, undo, and blink only that translation. Task 7.
- Another keystroke after the run has ended merges into the previous translation. Expected: a second Undo step, same sentence id or not. Task 6.
- The platform Undo key inside the Modern English editor undoes one character. Expected: the application Undo runs and reverts the whole run. Task 5.
- Delete a sentence, then Undo, and a following Undo applies an older translation step to a new row or a missing id. Expected: one Undo restores the sentence as the delete captured it, including that translation; the older step is gone. Task 8.
- Undo after opening another project, or after closing this one, still changes the previous project's sentence. Expected: the stack is empty, and append does that too while Edit Project metadata does not. Task 2.

## File Structure

- `oeapp/commands/undo_command.py` — `UndoCommand` and `push_command`. The only `QUndoCommand` type.
- `oeapp/commands/stack_maintenance.py` — walk the stack after a command reports an adjustment. Commands record the adjustment; this module applies it.
- `oeapp/commands/abstract.py` — `Command` gains `menu_text`, `locators`, and `last_adjustment`. `CommandManager` is deleted in Task 2.
- `oeapp/ui/typed_run.py` — which sentence's translation command is still open.
- `oeapp/ui/undo_presenter.py` — in-place editor write, off-screen navigation, blink.
- `oeapp/ui/translation_undo_filter.py` — consumes Undo and Redo `ShortcutOverride` on the Modern English editor only.
- `oeapp/state.py` — one `QUndoStack` on the app context, cleared when the project id changes.
- `oeapp/ui/menus.py` — Edit menu, built from `MainMenu.build` after File and before Project.
- Call sites that execute commands today go through `push_command`. They are listed on Task 2.

---

### Task 1: UndoCommand wrapper

**Files:**
- Create: `oeapp/commands/undo_command.py`
- Create: `tests/test_undo_command.py`
- Modify: `oeapp/commands/__init__.py`

**Interfaces:**
- Consumes: `Command.execute() -> bool`, `Command.undo() -> bool`, `Command.get_description() -> str`
- Produces:
  - `class UndoCommand(QUndoCommand)` with `command: Command`, `_run_open: bool = False`
  - `def push_command(stack: QUndoStack, command: Command) -> bool`
  - `UndoCommand.redo` calls `execute()`. On `False`, `setObsolete(True)`.
  - `UndoCommand.undo` calls `command.undo()`.
  - `UndoCommand.id() -> int` returns `1` when `_run_open` else `-1`. Do not return the sentence id.
  - The constructor passes `get_description()` as the command text. Task 3 switches that to `menu_text()`.
  - `mergeWith` returns `False` in this task. Task 6 fills it in.

- [ ] **Step 1: Write the failing test**

```python
def test_failed_execute_is_not_kept(qapp):
    stack = QUndoStack()
    assert push_command(stack, FailCommand()) is False
    assert stack.count() == 0
    assert stack.canUndo() is False


def test_stack_owns_the_command_after_the_name_is_dropped(qapp):
    stack = QUndoStack()
    log: list[str] = []
    push_command(stack, LogCommand(log))
    gc.collect()
    stack.undo()
    stack.redo()
    assert log == ["redo", "undo", "redo"]
```

`FailCommand.execute` returns `False`. `LogCommand` appends `"redo"` from `execute` and `"undo"` from `undo`.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_command.py -q`
Expected: FAIL, `push_command` is not defined.

- [ ] **Step 3: Implement `push_command` and `UndoCommand`**

`push_command` records success on a dict the caller holds, then pushes. `redo` sets that flag from `execute()` before `setObsolete`, so a command Qt deletes on failure can still report `False`. Do not store the wrapper on the command manager or on a list.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_command.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/commands/undo_command.py oeapp/commands/__init__.py tests/test_undo_command.py
git commit -m "feat: wrap undo commands in QUndoCommand"
```

### Task 2: One project-scoped stack

**Files:**
- Modify: `oeapp/state.py`, `oeapp/commands/abstract.py`, `oeapp/commands/__init__.py`
- Modify: `oeapp/ui/main_window.py`, `oeapp/ui/sentence_card.py`, `oeapp/ui/sentence_card_controller.py`, `oeapp/ui/project_workspace.py`, `oeapp/ui/oe_text_edit.py`, `oeapp/ui/dialogs/note_dialog.py`, `oeapp/ui/dialogs/append_text.py`
- Modify: `tests/conftest.py`, `tests/test_state.py`, `tests/test_commands.py`, `tests/test_main_window.py`, `tests/test_sentence_card.py`, `tests/test_sentence_card_hierarchy.py`, `tests/test_notes_panel.py`, `tests/test_note_dialog.py`, `tests/test_highlighting.py`, `tests/test_highlight_layers.py`, `tests/test_oe_text_edit.py`, `tests/test_idioms.py`, `tests/test_annotation_integration.py`, `tests/test_annotation_propagation.py`, `tests/test_annotation_copy_paste.py`, `tests/test_remembered_annotations.py`, `tests/test_selection_edges.py`, `tests/test_token_selection_robustness.py`, `tests/test_user_repro_clicks.py`
- Test: `tests/test_state.py`, `tests/test_append_text_dialog.py`

**Interfaces:**
- Consumes: `push_command` from Task 1.
- Produces:
  - `AppContext.undo_stack: QUndoStack` with `setUndoLimit(50)`
  - `current_project_id` setter calls `undo_stack.clear()` only when the id changes, including to `None`
  - `AppContext.undo` / `redo` call `undo_stack.undo()` / `redo()`, then `reload_project` when the command's `needs_full_reload` is true and `refresh_project` otherwise. Task 5 changes the translation case.
  - `command_setup` returns `undo_stack` limited to 10, not a `CommandManager`
  - Sentence cards take `undo_stack: QUndoStack`. Session access uses the app session, not a manager attribute.

- [ ] **Step 1: Write the failing test**

Build the `AppContext` the way `tests/test_state.py` builds it. `OkCommand.execute` and `OkCommand.undo` return `True`.

```python
def test_same_project_id_keeps_history(context):
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = 7
    context.current_project_id = 7
    assert context.undo_stack.canUndo() is True


def test_project_change_and_close_clear_history(context):
    context.current_project_id = 7
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = 8
    assert context.undo_stack.canUndo() is False
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = None
    assert context.undo_stack.canUndo() is False


def test_undo_limit_is_50(context):
    for _ in range(51):
        push_command(context.undo_stack, OkCommand())
    assert context.undo_stack.count() == 50
```

Add `test_append_clears_history`: stub the ingest, call `AppendTextDialog.append_text`, and assert `canUndo()` is false. Add `test_edit_project_leaves_history`: save through `EditProjectDialog` (`oeapp/ui/dialogs/edit_project.py`) without changing `current_project_id`, and assert `canUndo()` stays true.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_state.py::test_same_project_id_keeps_history tests/test_state.py::test_project_change_and_close_clear_history tests/test_state.py::test_undo_limit_is_50 -q`
Expected: FAIL, `AppContext` has no `undo_stack`.

- [ ] **Step 3: Replace `CommandManager`**

Delete `CommandManager`. Every `command_manager.execute(cmd)` becomes `push_command(undo_stack, cmd)`. `can_undo` / `can_redo` become `canUndo` / `canRedo`. `oe_text_edit.py` refreshes through the session, not `command_manager.session`. `AppendTextDialog.append_text` clears the stack after a successful append and before the project reload. Do not clear on chapter or section change, on `load()` of the already-open project, or in Edit Project. `AppContext.reset` builds a new stack.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_state.py tests/test_commands.py tests/test_undo_command.py -q`
Expected: PASS, and `rg CommandManager` finds nothing. Then the full suite, ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp tests/conftest.py tests/test_state.py tests/test_commands.py tests/test_main_window.py tests/test_sentence_card.py tests/test_sentence_card_hierarchy.py tests/test_notes_panel.py tests/test_note_dialog.py tests/test_highlighting.py tests/test_highlight_layers.py tests/test_oe_text_edit.py tests/test_idioms.py tests/test_annotation_integration.py tests/test_annotation_propagation.py tests/test_annotation_copy_paste.py tests/test_remembered_annotations.py tests/test_selection_edges.py tests/test_token_selection_robustness.py tests/test_user_repro_clicks.py tests/test_append_text_dialog.py
git commit -m "feat: replace CommandManager with one project-scoped QUndoStack"
```

Do not stage the untracked ADRs, `assets/DOE.ttf`, or the Institutes of Polity texts.

### Task 3: Plain undo names

**Files:**
- Modify: `oeapp/commands/sentence.py`, `oeapp/commands/paragraph.py`, `oeapp/commands/hierarchy.py`, `oeapp/commands/annotation.py`, `oeapp/commands/note.py`, `oeapp/commands/abstract.py`
- Test: `tests/test_undo_command.py`

**Interfaces:**
- Consumes: `UndoCommand` sets its text from `command.menu_text()` at construction.
- Produces: `Command.menu_text() -> str` with these exact values:
  - `text_modern` → `Edit translation`; `text_oe` → `Edit Old English`
  - `Merge sentences`, `Add sentence`, `Delete sentence`
  - `Split paragraph`, `Merge paragraphs`, `Split section`, `Merge sections`, `Split chapter`, `Merge chapters`
  - `Annotate`, `Apply remembered annotations`, `Propagate annotation`
  - `Add note`, `Update note`, `Delete note`

- [ ] **Step 1: Write the failing test**

Push one command of each class onto a stack and assert `stack.undoText()` is `Undo ` plus the string above. No assertion contains a digit from a database id.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_command.py::test_undo_text_has_no_database_id -q`
Expected: FAIL. Current descriptions look like `Edit sentence 1 text_modern`.

- [ ] **Step 3: Implement `menu_text` on each command**

`get_description` returns `menu_text()` so logs and the stack say the same thing. `UndoCommand.__init__` passes `command.menu_text()` to `QUndoCommand`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_command.py tests/test_commands.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/commands tests/test_undo_command.py
git commit -m "feat: name undo steps in plain language"
```

### Task 4: Edit menu and standard keys

**Files:**
- Create: `oeapp/ui/edit_menu.py`
- Modify: `oeapp/ui/menus.py` (`MainMenu.build`), `oeapp/ui/shortcuts.py`
- Modify: `oeapp/help/assets/keybindings.html`
- Modify: `oeapp/help/macos/AengliscToolkit.help/Contents/Resources/en.lproj/keybindings.html`
- Test: `tests/test_edit_menu.py`

**Interfaces:**
- Consumes: `AppContext.undo_stack`, `MainWindow.focus_search_input`
- Produces: an Edit menu with Undo, Redo, and Find only. Undo and Redo are `createUndoAction()` and `createRedoAction()`. Find calls `focus_search_input`. Each action's shortcut is the matching `QKeySequence.StandardKey`, and `menuRole` is `NoRole` before `addAction`.

- [ ] **Step 1: Write the failing test**

```python
def test_edit_menu_roles_and_standard_keys(main_window):
    edit = main_window.findChild(QMenu, "edit_menu")
    titles = [action.text().split("\t")[0] for action in edit.actions() if not action.isSeparator()]
    assert titles == ["Undo", "Redo", "Find"]
    undo, redo, find = edit.actions()[0], edit.actions()[1], edit.actions()[2]
    assert undo.menuRole() == QAction.MenuRole.NoRole
    assert redo.menuRole() == QAction.MenuRole.NoRole
    assert find.menuRole() == QAction.MenuRole.NoRole
    assert undo.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)
    assert redo.shortcut() == QKeySequence(QKeySequence.StandardKey.Redo)
    assert find.shortcut() == QKeySequence(QKeySequence.StandardKey.Find)
```

`EditMenu` sets `objectName` to `edit_menu`. `_window_shortcut_keys` collects `QShortcut.key().toString()` from shortcuts whose parent is the main window. Assert `Ctrl+Z`, `Ctrl+R`, `Ctrl+Shift+R`, and `Ctrl+F` are absent.

Assert N, Shift+N, Escape, Ctrl+G, Shift+Up, and Shift+Down are still window shortcuts. Assert both keybindings files list every string from `QKeySequence.keyBindings` for Undo, Redo, and Find for the platform that file is for. The macOS file's frozen list is Command+Z, Command+Shift+Z, and Command+F, plus any further bindings `keyBindings` reports on macOS. The assets file's frozen list is Ctrl+Z, Alt+Backspace, Ctrl+Y, Ctrl+Shift+Z, Alt+Shift+Backspace, and Ctrl+F, plus any further non-macOS bindings. Neither file's Editing section or its "Undo support" paragraph may contain `Ctrl+R`.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_edit_menu.py -q`
Expected: FAIL, there is no Edit menu.

- [ ] **Step 3: Add the Edit menu and delete the four window shortcuts**

`GlobalShortcuts.execute` no longer binds Ctrl+Z, Ctrl+R, Ctrl+Shift+R, or Ctrl+F. Update both keybindings copies: the Editing table's Undo and Redo rows, a Find row, and the Undo support paragraph. One chord is not the whole row when the platform has several.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_edit_menu.py tests/test_main_window.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/edit_menu.py oeapp/ui/menus.py oeapp/ui/shortcuts.py oeapp/help tests/test_edit_menu.py
git commit -m "feat: put Undo, Redo, and Find on the Edit menu"
```

### Task 5: Translation undo is the application undo

**Files:**
- Create: `oeapp/ui/translation_undo_filter.py`
- Create: `oeapp/ui/undo_presenter.py`
- Modify: `oeapp/ui/sentence_card.py` (translation editor setup), `oeapp/commands/sentence.py` (`needs_full_reload`), `oeapp/state.py`
- Test: `tests/test_translation_undo_keys.py`

**Interfaces:**
- Consumes: `UndoCommand`, `AppContext.undo_stack`, `SentenceCard.translation_edit`, `OldEnglishTextEdit.in_edit_mode`
- Produces:
  - `TranslationUndoFilter.eventFilter` returns `True` for `ShortcutOverride` when the key matches `StandardKey.Undo` or `StandardKey.Redo`
  - The filter is installed only on the Modern English `QTextEdit`, which also has document undo disabled
  - `EditSentenceCommand.needs_full_reload` is `False` when `field == "text_modern"` and `True` otherwise
  - `UndoPresenter.apply_translation(sentence_id: int, *, blink: bool) -> None` sets that card's editor to `sentence.text_modern` while a guard makes `on_translation_changed` return without pushing
  - In this task `blink` is ignored. Task 7 uses it.
  - Visible-card undo of `text_modern` calls `apply_translation` and does not call `refresh_project` or `reload_project`

- [ ] **Step 1: Write the failing test**

Build a sentence card, type two characters into `translation_edit`, and send the platform Undo key to that editor. Assert the editor text is what it was before the first character, and that `undoText()` is empty afterward. Send the same key to the read-only Old English editor and to the token table while a translation step is on the stack; assert the application undo runs. Enter OE edit mode, type a character, send Undo, and assert the OE editor undid the character and the application stack did not move.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_translation_undo_keys.py -q`
Expected: FAIL. The editor accepts the key or the undo reloads the project.

- [ ] **Step 3: Install the filter and write the editor in place**

Do not install the filter on the Old English editor, the token table, the highlighting combo, or the note dialog. Leave document undo on for the editable Old English text and the note dialog. `AppContext.undo` and `redo` ask `UndoPresenter` to handle a `text_modern` command; every other command still reloads or refreshes as it does now.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_translation_undo_keys.py tests/test_commands.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/translation_undo_filter.py oeapp/ui/undo_presenter.py oeapp/ui/sentence_card.py oeapp/commands/sentence.py oeapp/state.py tests/test_translation_undo_keys.py
git commit -m "feat: make translation undo the application undo step"
```

### Task 6: Typed Run

**Files:**
- Create: `oeapp/ui/typed_run.py`
- Modify: `oeapp/commands/undo_command.py` (`mergeWith`), `oeapp/ui/sentence_card_controller.py` (`on_translation_changed`), `oeapp/ui/sentence_card.py`, `oeapp/ui/notes_panel.py`, `oeapp/ui/main_window.py`, `oeapp/ui/menus.py`
- Test: `tests/test_typed_run.py`

**Interfaces:**
- Consumes: `UndoCommand._run_open`, `UndoCommand.id`, `push_command`
- Produces:
  - `class TypedRun` with `sentence_id: int | None`, `open_command: UndoCommand | None`, `end() -> None`, `open_for(command: UndoCommand) -> None`
  - `end` sets `_run_open = False` on `open_command` and clears both fields
  - `UndoCommand.mergeWith` returns `True` only when both commands are `text_modern` edits of the same `sentence_id` and the receiver's `_run_open` is `True`. It assigns `self.command.after = other.command.after` and leaves `before` alone.
  - `on_translation_changed` pushes one `EditSentenceCommand` per change. The first push of a closed run calls `open_for`. A push while that sentence's run is open relies on `mergeWith`.

- [ ] **Step 1: Write the failing test**

```python
def test_two_keystrokes_are_one_step(card):
    _type(card, "ab")
    assert card.undo_stack.count() == 1
    card.undo_stack.undo()
    assert card.sentence.text_modern == ""


def test_typing_after_undo_is_a_new_step(card):
    _type(card, "ab")
    card.undo_stack.undo()
    _type(card, "z")
    assert card.undo_stack.count() == 1
    card.undo_stack.undo()
    assert card.sentence.text_modern == ""
    card.undo_stack.undo()
    assert card.undo_stack.canUndo() is False
```

`_type(card, "ab")` is `qtbot.keyClicks(card.translation_edit, "ab")`. Also assert the run stays one step across: menu open and dismiss with no choice, highlighting combo change, Show Token Table, a single click in that card's Old English text, selecting a token on that card, and a single click on a note. Assert a new step after: Edit OE, Add Note, double-click on a note, `_open_annotation_modal` (covers the Old English double-click, the token-table double-click, and the A key), choosing Before or After, choosing a Mark as action, Merge, Delete, Find, `_on_search_scope_changed`, a chapter or section choice including previous and next, and a token on a different sentence. Dismissing the annotation modal, Add Note, or Edit OE without saving does not merge the next keystroke into the old run. A second visit to the same sentence after `end()` is a second step.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_typed_run.py::test_two_keystrokes_are_one_step -q`
Expected: FAIL. Each character is its own command.

- [ ] **Step 3: Merge while the run is open, and end it on the listed gestures**

`AppContext.undo` and `redo` call `typed_run.end()` before moving the stack. Call `end()` from `_on_edit_oe_clicked`, `_on_add_note_clicked`, `_open_annotation_modal`, `NotesPanel._on_note_double_clicked`, the Add Sentence and Mark as action slots (not `aboutToShow`), merge, delete, `focus_search_input`, and `_on_search_scope_changed`. Call `end()` at the start of the menu slots that open `LogViewerDialog`, `NewProjectDialog`, `OpenProjectDialog`, `AnnotationPresetManagementDialog`, `RememberedAnnotationsDialog`, and `AppendTextDialog`. Do not call `end()` from `_toggle_token_table`, `_on_note_clicked`, the highlighting slot, or a single click in the Old English text. Destroying the open sentence's editor calls `end()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_typed_run.py tests/test_translation_undo_keys.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/typed_run.py oeapp/commands/undo_command.py oeapp/ui tests/test_typed_run.py
git commit -m "feat: merge one typed run into one translation undo"
```

### Task 7: Undo returns to that sentence

**Files:**
- Modify: `oeapp/ui/undo_presenter.py`, `oeapp/ui/project_workspace.py`, `oeapp/ui/main_window.py`
- Test: `tests/test_undo_navigation.py`

**Interfaces:**
- Consumes: `UndoPresenter.apply_translation`, `ProjectUI.load_section`, `MainWindow.scroll_to_start`
- Produces:
  - `focus_section_start()` focuses the Old English editor of the first card now shown, the same widget `scroll_to_start` focuses
  - User chapter and section changes, including previous and next, call `load_section` and then `focus_section_start`. A chapter change shows that chapter's first section first. `load_section` itself does not move focus.
  - `UndoPresenter.undo_translation(sentence_id: int)`: if that card is already shown, `apply_translation(sentence_id, blink=False)`. If it is not, load the section that contains the sentence now, scroll to that card, apply the stack step, then `apply_translation(sentence_id, blink=True)`. Redo uses the same path.
  - `blink_translation(editor: QTextEdit) -> None` flashes the editor background and restores it. It does not push a command.

- [ ] **Step 1: Write the failing test**

Type a translation on a sentence in section A, choose section B, and undo. Assert the visible section is A's, the card for that sentence id is in view, its translation is the earlier text, and the blink helper ran once. Undo again with that card already shown and assert the blink helper did not run and `load_section` was not called. Choose a chapter and assert focus is the first sentence's Old English editor, not the translation box.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_navigation.py -q`
Expected: FAIL. Undo writes the sentence that is on screen, or reloads the whole project.

- [ ] **Step 3: Navigate, then undo, then blink**

Find the section through the sentence's paragraph. Do this work in the presenter, before and after `undo_stack.undo()`, so `redo()` of the command is not the place that opens a section. The presenter's `load_section` must not call `focus_section_start`. The history guard stays on while the editor text is replaced, and this load does not open a new Typed Run.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_undo_navigation.py tests/test_typed_run.py -q`
Expected: PASS. Then ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/undo_presenter.py oeapp/ui/project_workspace.py oeapp/ui/main_window.py tests/test_undo_navigation.py
git commit -m "feat: return translation undo to the sentence it changed"
```

### Task 8: Stack entries follow the sentence and the token

**Files:**
- Create: `oeapp/commands/stack_maintenance.py`
- Modify: `oeapp/commands/abstract.py`, `oeapp/commands/sentence.py`, `oeapp/commands/annotation.py`, `oeapp/commands/undo_command.py`
- Test: `tests/test_stack_maintenance.py`

**Interfaces:**
- Consumes: `QUndoStack.command(index)`, `QUndoCommand.setObsolete`
- Produces:
  - `CommandLocators` with `sentence_ids`, `token_ids`, and `idiom_ids`
  - `StackAdjustment` with `obsolete_sentence_ids: set[int]`, `token_sentence: dict[int, int]`, `obsolete_token_ids: set[int]`, `obsolete_idiom_ids: set[int]`
  - `Command.locators() -> CommandLocators` and `Command.last_adjustment: StackAdjustment`
  - `Command.is_removal_of(sentence_id: int) -> bool`, default `False`. `DeleteSentenceCommand` is the removal of `sentence_id`. `MergeSentenceCommand` is the removal of `next_sentence_id`.
  - `maintain_stack(stack: QUndoStack, source: Command) -> None` walks every command. A command whose sentence locators are all in `obsolete_sentence_ids` is `setObsolete(True)` unless `is_removal_of` that id. A command that also names a surviving sentence stays, and its later undo skips the gone ids. A locator token or idiom in the obsolete sets is dropped the same way. `token_sentence` updates locator sentence ids for those token ids and does not change token ids.
  - `push_command`, and the presenter's undo and redo, call `maintain_stack` after the stack operation returns, never from inside `redo()` or `undo()`.

- [ ] **Step 1: Write the failing test**

```python
def test_delete_drops_the_translation_step_and_undo_restores_the_capture(setup):
    push_command(setup.undo_stack, edit_translation(setup.sentence_id, "", "hello"))
    push_command(setup.undo_stack, delete_sentence(setup.sentence_id))
    setup.undo_stack.undo()
    sentences = Sentence.list(setup.project_id)
    assert len(sentences) == 1
    assert sentences[0].text_modern == "hello"
    assert setup.undo_stack.canUndo() is False


def test_insert_keeps_the_translation_on_the_same_sentence_id(setup):
    push_command(setup.undo_stack, edit_translation(sentence_id, "", "hello"))
    push_command(setup.undo_stack, add_sentence_before(sentence_id))
    setup.undo_stack.undo()  # undo the insert
    setup.undo_stack.undo()
    assert Sentence.get(sentence_id).text_modern == ""
```

Also: merge moves a token onto the surviving sentence and the annotation command's locator sentence id follows that token id; undo of the merge records the new sentence id on the removal command and points the annotation locator at that new id. An Old English edit that drops a token's surface makes the annotation command for that token obsolete, and an edit that keeps the surface leaves it. `display_order_changes` on the add command is unchanged by the later walk.

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_stack_maintenance.py -q`
Expected: FAIL. The translation step is still undoable after the sentence is gone, or undo looks up the old id.

- [ ] **Step 3: Record adjustments and walk after the stack settles**

`DeleteSentenceCommand.execute` records the deleted sentence id. Its `undo` writes the restored sentence's new id onto `sentence_id`. `MergeSentenceCommand.execute` records the next sentence id and `token_id -> current_sentence_id` for tokens it moved. Its `undo` records `token_id -> new next sentence id` and stores that id on `next_sentence_id`. `EditSentenceCommand` for `text_oe` diffs token and idiom ids around `Token.update_from_sentence` and records the ones that disappeared. `AnnotateTokenCommand` stores the sentence id, token id, and idiom id it targets. `ApplyRememberedAnnotationsCommand` and `ApplyAnnotationPropagationCommand` store every sentence and token they touch. Paragraph and hierarchy commands do not delete sentences; they do not record sentence removals. Do not assign new database ids onto surviving sentences. Do not rewrite `display_order_changes`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_stack_maintenance.py tests/test_commands.py tests/test_typed_run.py tests/test_undo_navigation.py -q`
Expected: PASS. Then the full suite, ruff, mypy, and `make napoleon-gate`.

- [ ] **Step 5: Commit**

```bash
git add oeapp/commands tests/test_stack_maintenance.py
git commit -m "feat: drop undo steps whose sentence or token is gone"
```

Run `graphify update .` after this commit.

## Spec coverage

- ADR 0009 D1 is Tasks 1 and 2. D2 is Task 2. D3 is Tasks 3 and 4. D4 is the global constraints; there is no macro task.
- ADR 0010 D1 is Tasks 5 and 6. D2 is Tasks 5 and 7. D3 is Task 5. D4 is Task 8.
- The read-only full-translation view is left without its own undo. No task adds one.

## Self-review

- Spec coverage is the list above. Annotation paste, a full menu bar, clean-state tracking, and help pages other than the two keybindings files have no task because the spec leaves them out.
- `push_command`, `UndoCommand.id`, `TypedRun.end`, `menu_text`, and `maintain_stack` use the same names in later tasks as in the task that produces them.
- `display_order_changes` is an undo snapshot. The walk does not treat it as a locator. Task 8's insert test locks that.
- The obsolete-command removal is Qt's, on the next stack operation, not a second list and not a rebuild that would call `redo()` again.
