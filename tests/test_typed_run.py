"""A Typed Run in the Modern English editor is one undo step."""

from unittest.mock import MagicMock, patch

import pytest
from oeapp.commands import EditSentenceCommand, UndoCommand, push_command
from oeapp.models.project import Project
from oeapp.state import AppContext
from oeapp.ui.main_window import MainWindow
from oeapp.ui.typed_run import TypedRun
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtTest import QTest


@pytest.fixture
def mock_services():
    """Mock MigrationService and BackupService."""
    with (
        patch("oeapp.ui.main_window.MigrationService") as mock_mig,
        patch("oeapp.ui.main_window.BackupService") as mock_back,
    ):
        mock_mig.return_value.migrate.return_value = MagicMock(
            migration_version="abc", app_version="1.0.0"
        )
        yield mock_mig, mock_back


@pytest.fixture
def main_window(qapp, db_session, mock_services):
    """Show a MainWindow with a two-sentence project loaded."""
    project = Project.create(
        text="Se cyning cōm. Hē wæs gōd.", name=f"Typed Run {id(db_session)}"
    )
    window = MainWindow(app_context=AppContext(session=db_session))
    window.app_context.current_project_id = project.id
    window.load_project(project)
    window.show()
    window.activateWindow()
    qapp.processEvents()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


@pytest.fixture
def card(main_window):
    """Return the first sentence card."""
    assert len(main_window.sentence_cards) >= 2  # noqa: PLR2004
    return main_window.sentence_cards[0]


@pytest.fixture
def run(main_window):
    """Return the application Typed Run."""
    return main_window.app_context.typed_run


def _type(card, text: str, qtbot) -> None:
    card.translation_edit.setFocus()
    card.translation_edit.moveCursor(
        card.translation_edit.textCursor().MoveOperation.End
    )
    qtbot.keyClicks(card.translation_edit, text)


def _top(card):
    stack = card.undo_stack
    return stack.command(stack.index() - 1)


def _assert_new_step_after(card, qtbot) -> None:
    """Typing ``c`` after ``ab`` must be its own step that starts at ``ab``."""
    count = card.undo_stack.count()
    _type(card, "c", qtbot)
    assert card.undo_stack.count() == count + 1
    top = _top(card)
    assert top.command.before == "ab"
    assert top.command.after == "abc"


def _assert_same_step_after(card, qtbot) -> None:
    count = card.undo_stack.count()
    _type(card, "c", qtbot)
    assert card.undo_stack.count() == count
    top = _top(card)
    assert top.command.before == ""
    assert top.command.after == "abc"


# ---------------------------------------------------------------------------
# Merge rules
# ---------------------------------------------------------------------------


def _wrap(sentence_id: int, field: str = "text_modern", before="", after="x"):
    command = EditSentenceCommand(
        sentence_id=sentence_id, field=field, before=before, after=after
    )
    return UndoCommand(command, {})


def test_id_is_one_for_every_translation_edit_and_minus_one_otherwise():
    closed = _wrap(1)
    assert closed.id() == 1
    closed.run_open = True
    assert closed.id() == 1
    assert _wrap(1, field="text_oe").id() == -1


def test_merge_requires_open_receiver_and_same_sentence():
    receiver = _wrap(1, before="", after="a")
    other = _wrap(1, before="a", after="ab")
    assert receiver.mergeWith(other) is False
    receiver.run_open = True
    assert receiver.mergeWith(_wrap(2, before="a", after="ab")) is False
    assert receiver.mergeWith(_wrap(1, field="text_oe")) is False
    assert receiver.mergeWith(other) is True
    assert receiver.command.before == ""
    assert receiver.command.after == "ab"


def test_failed_translation_write_does_not_merge_into_open_run(qapp):
    stack = QUndoStack()
    with patch.object(EditSentenceCommand, "execute", return_value=True):
        push_command(
            stack,
            EditSentenceCommand(
                sentence_id=1, field="text_modern", before="", after="a"
            ),
        )
    receiver = stack.command(0)
    TypedRun().open_for(receiver)
    with patch.object(EditSentenceCommand, "execute", return_value=False):
        ok = push_command(
            stack,
            EditSentenceCommand(
                sentence_id=1, field="text_modern", before="a", after="ab"
            ),
        )
    assert ok is False
    assert stack.count() == 1
    assert receiver.command.after == "a"


def test_end_closes_the_open_command_and_clears_fields():
    typed_run = TypedRun()
    command = _wrap(7)
    typed_run.open_for(command)
    assert typed_run.sentence_id == 7  # noqa: PLR2004
    assert typed_run.open_command is command
    assert command.run_open is True
    typed_run.end()
    assert command.run_open is False
    assert typed_run.sentence_id is None
    assert typed_run.open_command is None


# ---------------------------------------------------------------------------
# Typing
# ---------------------------------------------------------------------------


def test_two_keystrokes_are_one_step(card, qtbot):
    _type(card, "ab", qtbot)
    assert card.undo_stack.count() == 1
    card.undo_stack.undo()
    assert card.sentence.text_modern == ""


def test_typing_after_undo_is_a_new_step(card, qtbot):
    _type(card, "ab", qtbot)
    card.undo_stack.undo()
    _type(card, "z", qtbot)
    assert card.undo_stack.count() == 1
    card.undo_stack.undo()
    assert card.sentence.text_modern == ""
    card.undo_stack.undo()
    assert card.undo_stack.canUndo() is False


def test_app_undo_and_redo_end_the_run(main_window, card, run, qtbot):
    _type(card, "ab", qtbot)
    with (
        patch.object(main_window, "reload_project"),
        patch.object(main_window, "refresh_project"),
    ):
        main_window.app_context.undo()
        assert run.open_command is None
        main_window.app_context.redo()
    assert run.open_command is None
    _assert_new_step_after(card, qtbot)


def test_second_visit_after_end_is_a_second_step(card, run, qtbot):
    _type(card, "ab", qtbot)
    run.end()
    _assert_new_step_after(card, qtbot)


def test_typing_in_another_sentence_is_a_new_step(main_window, card, qtbot):
    other = main_window.sentence_cards[1]
    _type(card, "ab", qtbot)
    _type(other, "x", qtbot)
    assert card.undo_stack.count() == 2  # noqa: PLR2004
    _assert_new_step_after(card, qtbot)


def test_destroying_the_open_editor_ends_the_run(card, run, qtbot):
    _type(card, "ab", qtbot)
    command = run.open_command
    card.translation_edit.destroyed.emit()
    assert run.open_command is None
    assert command.run_open is False


# ---------------------------------------------------------------------------
# Gestures that keep the run open
# ---------------------------------------------------------------------------


def test_menu_open_and_dismiss_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    for button in (card.add_sentence_button, card.toggle_paragraph_button):
        menu = button.menu()
        menu.aboutToShow.emit()
        menu.aboutToHide.emit()
    _assert_same_step_after(card, qtbot)


def test_highlighting_change_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    combo = card.highlighting_combo
    combo.setCurrentIndex((combo.currentIndex() + 1) % combo.count())
    _assert_same_step_after(card, qtbot)


def test_show_token_table_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    card.token_table_toggle_button.click()
    _assert_same_step_after(card, qtbot)


def test_single_click_in_old_english_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    QTest.mouseClick(
        card.oe_text_edit.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(5, 5)
    )
    _assert_same_step_after(card, qtbot)


def test_selecting_token_on_same_card_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    token = card.oe_text_edit.tokens[0]
    card.token_selected_for_details.emit(token, card.sentence, card)
    _assert_same_step_after(card, qtbot)


def test_single_click_on_note_keeps_run(card, qtbot):
    _type(card, "ab", qtbot)
    with patch.object(card.oe_text_edit, "highlight_note"):
        card.notes_panel._on_note_clicked(MagicMock())
    _assert_same_step_after(card, qtbot)


# ---------------------------------------------------------------------------
# Gestures that end the run
# ---------------------------------------------------------------------------


def test_edit_oe_ends_run(card, qtbot):
    _type(card, "ab", qtbot)
    card._on_edit_oe_clicked()
    card._on_cancel_edit_clicked()
    _assert_new_step_after(card, qtbot)


def test_add_note_dismissed_ends_run(card, qtbot):
    _type(card, "ab", qtbot)
    with (
        patch.object(
            type(card.oe_text_edit),
            "selected_tokens",
            new=(card.oe_text_edit.tokens[0], card.oe_text_edit.tokens[0]),
        ),
        patch("oeapp.ui.sentence_card.NoteDialog") as dialog,
    ):
        card._on_add_note_clicked()
    dialog.return_value.exec.assert_called_once()
    _assert_new_step_after(card, qtbot)


def test_note_double_click_ends_run(card, qtbot):
    _type(card, "ab", qtbot)
    with patch("oeapp.ui.notes_panel.NoteDialog") as dialog:
        card.notes_panel._on_note_double_clicked(MagicMock(start_token=1, end_token=1))
    dialog.return_value.exec.assert_called_once()
    _assert_new_step_after(card, qtbot)


def test_annotation_modal_dismissed_ends_run(card, qtbot):
    _type(card, "ab", qtbot)
    with patch.object(card.controller, "open_annotation_modal") as modal:
        card._open_annotation_modal()
    modal.assert_called_once()
    _assert_new_step_after(card, qtbot)


@pytest.mark.parametrize(
    ("slot", "delegate"),
    [
        ("_on_add_sentence_before_clicked", "on_add_sentence_before_clicked"),
        ("_on_add_sentence_after_clicked", "on_add_sentence_after_clicked"),
        ("_on_merge_clicked", "on_merge_clicked"),
        ("_on_delete_clicked", "on_delete_clicked"),
        ("_on_split_paragraph_clicked", "on_split_paragraph_clicked"),
        ("_on_merge_paragraph_clicked", "on_merge_paragraph_clicked"),
        ("_on_split_section_clicked", "on_split_section_clicked"),
        ("_on_merge_section_clicked", "on_merge_section_clicked"),
        ("_on_split_chapter_clicked", "on_split_chapter_clicked"),
        ("_on_merge_chapter_clicked", "on_merge_chapter_clicked"),
    ],
)
def test_sentence_actions_end_run(card, qtbot, slot, delegate):
    _type(card, "ab", qtbot)
    with (
        patch.object(card.controller, delegate, return_value=False),
        patch("oeapp.ui.sentence_card.QMessageBox"),
    ):
        getattr(card, slot)()
    _assert_new_step_after(card, qtbot)


def test_find_ends_run(main_window, card, qtbot):
    _type(card, "ab", qtbot)
    main_window.action_service.focus_search_input()
    _assert_new_step_after(card, qtbot)


def test_search_scope_change_ends_run(main_window, card, qtbot):
    _type(card, "ab", qtbot)
    with patch.object(main_window.action_service, "perform_search"):
        main_window._on_search_scope_changed(0)
    _assert_new_step_after(card, qtbot)


@pytest.mark.parametrize(
    ("slot", "loader"),
    [
        ("_on_chapter_changed", "update_sections_for_chapter"),
        ("_on_section_changed", "load_section"),
    ],
)
def test_chapter_or_section_choice_ends_run(main_window, card, qtbot, slot, loader):
    _type(card, "ab", qtbot)
    with patch.object(main_window.project_ui, loader):
        getattr(main_window, slot)(0)
    _assert_new_step_after(card, qtbot)


@pytest.mark.parametrize(
    "slot",
    [
        "_on_prev_chapter_clicked",
        "_on_next_chapter_clicked",
        "_on_prev_section_clicked",
        "_on_next_section_clicked",
    ],
)
def test_previous_and_next_end_run(main_window, card, qtbot, slot):
    _type(card, "ab", qtbot)
    getattr(main_window, slot)()
    _assert_new_step_after(card, qtbot)


def test_token_on_different_sentence_ends_run(main_window, card, qtbot):
    other = main_window.sentence_cards[1]
    _type(card, "ab", qtbot)
    token = other.oe_text_edit.tokens[0]
    other.token_selected_for_details.emit(token, other.sentence, other)
    _assert_new_step_after(card, qtbot)


@pytest.mark.parametrize(
    ("menu_attr", "method", "dialog_path"),
    [
        ("tools_menu", "_show_pos_presets_dialog", "AnnotationPresetManagementDialog"),
        (
            "tools_menu",
            "_show_global_remembered_annotations_dialog",
            "RememberedAnnotationsDialog",
        ),
        (
            "tools_menu",
            "_show_project_remembered_annotations_dialog",
            "RememberedAnnotationsDialog",
        ),
        ("file_menu_obj", "_show_new_project_dialog", "NewProjectDialog"),
        ("file_menu_obj", "_show_open_project_dialog", "OpenProjectDialog"),
        ("project_menu", "_show_append_text_dialog", "AppendTextDialog"),
        ("window_menu_obj", "_show_log_viewer", "LogViewerDialog"),
    ],
)
def test_menu_dialogs_end_run(  # noqa: PLR0913
    main_window, card, qtbot, menu_attr, method, dialog_path
):
    _type(card, "ab", qtbot)
    menu = getattr(main_window.main_menu, menu_attr)
    with (
        patch(f"oeapp.ui.menus.{dialog_path}"),
        patch.object(
            main_window.action_service, "show_project_remembered_annotations_dialog"
        ),
    ):
        getattr(menu, method)()
    _assert_new_step_after(card, qtbot)
