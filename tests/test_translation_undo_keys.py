"""Platform Undo and Redo keys in a sentence card run the application undo."""

from unittest.mock import MagicMock, patch

import pytest
from oeapp.commands import EditSentenceCommand
from oeapp.models.project import Project
from oeapp.state import AppContext
from oeapp.ui.main_window import MainWindow
from oeapp.ui.translation_undo_filter import TranslationUndoFilter
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


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
    """Show a MainWindow with a one-sentence project loaded."""
    project = Project.create(text="Se cyning", name=f"Undo Keys {id(db_session)}")
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
    """Return the only sentence card."""
    assert main_window.sentence_cards
    return main_window.sentence_cards[0]


def _press(widget, standard_key: QKeySequence.StandardKey, qapp) -> None:
    widget.setFocus()
    qapp.processEvents()
    combo = QKeySequence(standard_key)[0]
    QTest.keyClick(widget, combo.key(), combo.keyboardModifiers())
    qapp.processEvents()


def _type(widget, text: str, qapp) -> None:
    widget.setFocus()
    qapp.processEvents()
    for char in text:
        QTest.keyClick(widget, char)
    qapp.processEvents()


def _no_reload(main_window):
    return (
        patch.object(main_window, "reload_project"),
        patch.object(main_window, "refresh_project"),
    )


def test_filter_claims_undo_and_redo_shortcut_override():
    undo_filter = TranslationUndoFilter()
    for standard_key in (QKeySequence.StandardKey.Undo, QKeySequence.StandardKey.Redo):
        combo = QKeySequence(standard_key)[0]
        event = QKeyEvent(
            QEvent.Type.ShortcutOverride, combo.key(), combo.keyboardModifiers()
        )
        assert undo_filter.eventFilter(MagicMock(), event) is True
    plain = QKeyEvent(
        QEvent.Type.ShortcutOverride, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier
    )
    assert undo_filter.eventFilter(MagicMock(), plain) is False


def test_filter_only_on_modern_english_editor(card):
    edit = card.translation_edit
    assert not edit.document().isUndoRedoEnabled()
    assert card.oe_text_edit.document().isUndoRedoEnabled()
    assert edit.findChild(TranslationUndoFilter) is not None
    assert card.oe_text_edit.findChild(TranslationUndoFilter) is None
    assert card.token_table.findChild(TranslationUndoFilter) is None


def test_undo_key_in_translation_editor_is_application_undo(main_window, card, qapp):
    stack = main_window.app_context.undo_stack
    edit = card.translation_edit
    _type(edit, "ab", qapp)
    assert edit.toPlainText() == "ab"
    assert stack.index() == 1
    reload_patch, refresh_patch = _no_reload(main_window)
    with reload_patch as reload, refresh_patch as refresh:
        _press(edit, QKeySequence.StandardKey.Undo, qapp)
        assert edit.toPlainText() == ""
        assert stack.index() == 0
        assert stack.redoText() == "Edit translation"
        _press(edit, QKeySequence.StandardKey.Redo, qapp)
        assert edit.toPlainText() == "ab"
        assert stack.index() == 1
        assert stack.undoText() == "Edit translation"
    reload.assert_not_called()
    refresh.assert_not_called()
    assert stack.count() == 1
    assert card.sentence.text_modern == "ab"


def test_apply_translation_does_not_push(main_window, card, qapp):
    stack = main_window.app_context.undo_stack
    _type(card.translation_edit, "x", qapp)
    count = stack.count()
    main_window.app_context.undo()
    assert stack.count() == count
    assert card.translation_edit.toPlainText() == ""
    assert stack.index() == count - 1


@pytest.mark.parametrize("target", ["oe", "token_table"])
def test_undo_key_elsewhere_runs_application_undo(main_window, card, qapp, target):
    stack = main_window.app_context.undo_stack
    _type(card.translation_edit, "z", qapp)
    assert stack.index() == 1
    widget = card.oe_text_edit if target == "oe" else card.token_table.table
    if target == "token_table":
        card.token_table.setVisible(True)
        qapp.processEvents()
    reload_patch, refresh_patch = _no_reload(main_window)
    with reload_patch, refresh_patch:
        _press(widget, QKeySequence.StandardKey.Undo, qapp)
    assert stack.index() == 0
    assert card.translation_edit.toPlainText() == ""


def test_undo_key_in_oe_edit_mode_is_character_undo(main_window, card, qapp):
    stack = main_window.app_context.undo_stack
    _type(card.translation_edit, "z", qapp)
    assert stack.index() == 1
    card.controller.on_edit_oe_clicked()
    oe = card.oe_text_edit
    oe.setFocus()
    oe.moveCursor(oe.textCursor().MoveOperation.End)
    before = oe.toPlainText()
    _type(oe, "q", qapp)
    assert oe.toPlainText() == before + "q"
    _press(oe, QKeySequence.StandardKey.Undo, qapp)
    assert oe.toPlainText() == before
    assert stack.index() == 1
    assert QApplication.focusWidget() is oe


@pytest.mark.parametrize(("field", "full"), [("text_modern", False), ("text_oe", True)])
def test_needs_full_reload_by_field(field, full):
    command = EditSentenceCommand(sentence_id=1, field=field, before="", after="x")
    assert command.needs_full_reload is full
