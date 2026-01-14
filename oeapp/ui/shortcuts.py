from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QWidget

    from oeapp.ui.dialogs.annotation_modal import AnnotationModal
    from oeapp.ui.main_window import MainWindow


class ShortcutsMixin:
    """
    Mixin for keyboard shortcuts.
    """

    def __init__(self, parent: QWidget):
        self.parent = parent

    def add_shortcut(self, key: str, action: Callable[[], None]) -> None:
        """
        Add a keyboard shortcut to the application.
        """
        shortcut = QShortcut(QKeySequence(key), self.parent)
        shortcut.activated.connect(action)


class GlobalShortcuts(ShortcutsMixin):
    """
    Global keyboard shortcuts for the application.

    The following shortcuts are set up here:

    - J/K for next/previous sentence
    - T for focus translation
    - Undo: Ctrl+Z
    - Redo: Ctrl+R or Ctrl+Shift+R

    """

    def __init__(self, parent: MainWindow):
        """Initialize the shortcuts."""
        super().__init__(parent)
        self.main_window = parent

    def execute(self) -> None:
        """
        Add all the shortcuts to the main window.
        """
        self.add_shortcut("J", self.main_window.action_service.next_sentence)
        self.add_shortcut("K", self.main_window.action_service.prev_sentence)
        self.add_shortcut("T", self.main_window.action_service.focus_translation)
        self.add_shortcut("N", self.main_window.action_service.next_match)
        self.add_shortcut("Shift+N", self.main_window.action_service.prev_match)
        self.add_shortcut("Escape", self.main_window._on_clear_search_clicked)
        self.add_shortcut("Ctrl+Z", self.main_window.application_state.undo)
        self.add_shortcut("Ctrl+R", self.main_window.application_state.redo)
        self.add_shortcut("Ctrl+Shift+R", self.main_window.application_state.redo)
        self.add_shortcut("Ctrl+F", self.main_window.action_service.focus_search_input)
        self.add_shortcut("Ctrl+G", self.main_window.action_service.focus_first_match)
        self.add_shortcut("Shift+Down", self.main_window.action_service.scroll_to_end)
        self.add_shortcut("Shift+Up", self.main_window.action_service.scroll_to_start)


class AnnotationModalShortcuts(ShortcutsMixin):
    """
    Keyboard shortcuts for the annotation modal.
    """

    def __init__(self, parent: AnnotationModal):
        super().__init__(parent)
        self.annotation_modal = parent

    def execute(self) -> None:
        """
        Add all the shortcuts to the annotation modal.
        """
        for key in self.annotation_modal.PART_OF_SPEECH_MAP:
            if key is not None:
                self.add_shortcut(
                    key,
                    lambda k=key: self.annotation_modal._select_pos_by_key(k),  # type: ignore[misc]
                )
        self.add_shortcut("Enter", self.annotation_modal.save)
        self.add_shortcut("Ctrl+S", self.annotation_modal.save)
        self.add_shortcut("Escape", self.annotation_modal.reject)
