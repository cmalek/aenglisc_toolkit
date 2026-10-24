"""Tests for the Edit menu and its standard key bindings."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from oeapp.commands import Command, push_command
from oeapp.state import AppContext
from oeapp.ui.main_window import MainWindow
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMenu

HELP_DIR = Path(__file__).resolve().parent.parent / "oeapp" / "help"
ASSETS_KEYBINDINGS = HELP_DIR / "assets" / "keybindings.html"
MACOS_KEYBINDINGS = (
    HELP_DIR
    / "macos"
    / "AengliscToolkit.help"
    / "Contents"
    / "Resources"
    / "en.lproj"
    / "keybindings.html"
)
EDIT_KEYS = (
    QKeySequence.StandardKey.Undo,
    QKeySequence.StandardKey.Redo,
    QKeySequence.StandardKey.Find,
)
ASSETS_FROZEN = [
    "Ctrl+Z",
    "Alt+Backspace",
    "Ctrl+Y",
    "Ctrl+Shift+Z",
    "Alt+Shift+Backspace",
    "Ctrl+F",
    "Undo",
    "Redo",
    "Find",
]
MACOS_FROZEN = [
    "Command+Z",
    "Command+Shift+Z",
    "Command+F",
    "Undo",
    "Redo",
    "Find",
]


class _OkCommand(Command):
    """Command whose ``execute`` and ``undo`` always succeed."""

    def execute(self) -> bool:
        """Succeed."""
        return True

    def undo(self) -> bool:
        """Succeed."""
        return True

    def menu_text(self) -> str:
        """Describe the command."""
        return "Edit translation"


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
    """Create a MainWindow with mocked services."""
    window = MainWindow(app_context=AppContext(session=db_session))
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def _edit_menu(main_window) -> QMenu:
    menu = main_window.findChild(QMenu, "edit_menu")
    assert menu is not None
    return menu


def _window_shortcut_keys(main_window) -> set[str]:
    return {
        shortcut.key().toString()
        for shortcut in main_window.findChildren(QShortcut)
        if shortcut.parent() is main_window
    }


def _editing_section(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    match = re.search(r"<h2>Editing</h2>(.*?)<h2>", html, re.DOTALL)
    assert match is not None
    return match.group(1)


def _undo_support_paragraph(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    match = re.search(r"<p><strong>Undo support:</strong>(.*?)</p>", html, re.DOTALL)
    assert match is not None
    return match.group(1)


def _runtime_bindings(macos: bool) -> list[str]:
    names = [
        binding.toString()
        for key in EDIT_KEYS
        for binding in QKeySequence.keyBindings(key)
    ]
    if macos:
        names = [name.replace("Ctrl+", "Command+") for name in names]
    return names


def test_edit_menu_roles_and_standard_keys(main_window):
    edit = _edit_menu(main_window)
    titles = [
        action.text().split("\t")[0]
        for action in edit.actions()
        if not action.isSeparator()
    ]
    assert titles == ["Undo", "Redo", "Find"]
    undo, redo, find = edit.actions()[0], edit.actions()[1], edit.actions()[2]
    assert undo.menuRole() == QAction.MenuRole.NoRole
    assert redo.menuRole() == QAction.MenuRole.NoRole
    assert find.menuRole() == QAction.MenuRole.NoRole
    assert undo.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)
    assert redo.shortcut() == QKeySequence(QKeySequence.StandardKey.Redo)
    assert find.shortcut() == QKeySequence(QKeySequence.StandardKey.Find)


def test_edit_menu_sits_between_file_and_project(main_window):
    titles = [
        action.text().replace("&", "") for action in main_window.menuBar().actions()
    ]
    assert titles.index("Edit") == titles.index("File") + 1
    assert titles.index("Project") == titles.index("Edit") + 1


def test_undo_action_shows_plain_command_name(main_window):
    push_command(main_window.app_context.undo_stack, _OkCommand())
    undo = _edit_menu(main_window).actions()[0]
    assert undo.text() == "Undo Edit translation"
    assert undo.isEnabled()


def test_undo_and_redo_go_through_app_context(main_window):
    context = main_window.app_context
    push_command(context.undo_stack, _OkCommand())
    undo, redo = _edit_menu(main_window).actions()[:2]
    with patch.object(main_window, "refresh_project") as refresh:
        undo.trigger()
        assert context.undo_stack.index() == 0
        redo.trigger()
        assert context.undo_stack.index() == 1
    assert refresh.call_count == 2


def test_find_focuses_search_input(main_window, qapp):
    main_window.show()
    main_window.activateWindow()
    qapp.processEvents()
    find = _edit_menu(main_window).actions()[2]
    find.trigger()
    qapp.processEvents()
    assert QApplication.focusWidget() is main_window.search_input


def test_actions_follow_the_new_stack_after_reset(main_window, qapp):
    context = main_window.app_context
    context.reset()
    context.set_main_window(main_window)
    qapp.processEvents()
    push_command(context.undo_stack, _OkCommand())
    undo, redo, find = _edit_menu(main_window).actions()
    assert undo.text() == "Undo Edit translation"
    assert undo.isEnabled()
    assert undo.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)
    assert redo.shortcut() == QKeySequence(QKeySequence.StandardKey.Redo)
    assert undo.menuRole() == QAction.MenuRole.NoRole
    assert redo.menuRole() == QAction.MenuRole.NoRole
    assert find.text().split("\t")[0] == "Find"
    with patch.object(main_window, "refresh_project"):
        undo.trigger()
    assert context.undo_stack.index() == 0


def test_window_shortcuts_drop_edit_chords(main_window):
    keys = _window_shortcut_keys(main_window)
    for removed in ("Ctrl+Z", "Ctrl+R", "Ctrl+Shift+R", "Ctrl+F"):
        assert removed not in keys
    for kept in ("N", "Shift+N", "Esc", "Ctrl+G", "Shift+Up", "Shift+Down"):
        assert kept in keys


@pytest.mark.parametrize(
    ("path", "frozen"),
    [(ASSETS_KEYBINDINGS, ASSETS_FROZEN), (MACOS_KEYBINDINGS, MACOS_FROZEN)],
)
def test_keybindings_list_frozen_bindings(path, frozen):
    editing = _editing_section(path)
    for name in frozen:
        assert f"<strong>{name}</strong>" in editing, name


def test_keybindings_list_runtime_bindings(qapp):
    macos = QGuiApplication.platformName() == "cocoa"
    path = MACOS_KEYBINDINGS if macos else ASSETS_KEYBINDINGS
    editing = _editing_section(path)
    for name in _runtime_bindings(macos):
        assert f"<strong>{name}</strong>" in editing, name


@pytest.mark.parametrize("path", [ASSETS_KEYBINDINGS, MACOS_KEYBINDINGS])
def test_keybindings_drop_ctrl_r(path):
    assert "Ctrl+R" not in _editing_section(path)
    assert "Ctrl+R" not in _undo_support_paragraph(path)
