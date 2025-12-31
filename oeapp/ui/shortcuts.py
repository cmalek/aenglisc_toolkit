from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence, QShortcut

if TYPE_CHECKING:
    from collections.abc import Callable

    from oeapp.ui.main_window import MainWindow


class GlobalShortcuts:
    """
    Global shortcuts for the application.

    The following shortcuts are set up here:

    - J/K for next/previous sentence
    - T for focus translation
    - Undo: Ctrl+Z
    - Redo: Ctrl+R or Ctrl+Shift+R

    """

    def __init__(self, main_window: MainWindow):
        """Initialize the shortcuts."""
        self.main_window = main_window

    def execute(self) -> None:
        """
        Add all the shortcuts to the main window.
        """
        self.add_shortcut("J", self.main_window.action_service.next_sentence)
        self.add_shortcut("K", self.main_window.action_service.prev_sentence)
        self.add_shortcut("T", self.main_window.action_service.focus_translation)
        self.add_shortcut("Ctrl+Z", self.main_window.application_state.undo)
        self.add_shortcut("Ctrl+R", self.main_window.application_state.redo)
        self.add_shortcut("Ctrl+Shift+R", self.main_window.application_state.redo)

    def add_shortcut(self, key: str, action: Callable[[], None]) -> None:
        """
        Add a shortcut to the application.

        Args:
            key: The key sequence to bind to the action, e.g. "Ctrl+N"
            action: The action to perform when the key is pressed.  This should
                be a callable that takes no arguments and returns None.

        """
        shortcut = QShortcut(QKeySequence(key), self.main_window)
        shortcut.activated.connect(action)
