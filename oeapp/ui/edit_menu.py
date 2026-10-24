"""The Edit menu: Undo, Redo, and Find."""

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence, QUndoStack

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QMenu

    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.menus import MainMenu


class EditMenu:
    """
    An "Edit" menu with Undo, Redo, and Find.

    Undo and Redo come from :meth:`QUndoStack.createUndoAction` and
    :meth:`QUndoStack.createRedoAction`, so their text and enabled state follow
    the application undo stack. Triggering them runs ``AppContext.undo`` and
    ``AppContext.redo`` so the window refreshes and failures are reported.
    When the context replaces its stack, both actions are rebuilt on the new
    stack.

    Args:
        main_menu: Main menu.
        main_window: Main window.

    """

    def __init__(self, main_menu: "MainMenu", main_window: "MainWindow") -> None:
        """
        Initialize the instance and populate the menu.

        Args:
            main_menu: Main menu.
            main_window: Main window.

        """
        #: Main window.
        self.main_window = main_window
        #: Main menu.
        self.main_menu = main_menu
        #: The Edit menu widget.
        self.edit_menu: QMenu = self.main_menu.add_menu("&Edit")
        self.edit_menu.setObjectName("edit_menu")
        #: Undo action bound to the current undo stack.
        self.undo_action: QAction
        #: Redo action bound to the current undo stack.
        self.redo_action: QAction
        #: Find action.
        self.find_action: QAction
        self.populate()
        self.main_window.app_context.undo_stack_replaced.connect(self.rebind)

    def populate(self) -> None:
        """
        Add Undo, Redo, and Find to the menu.

        Side Effects:
            Adds three actions to :attr:`edit_menu`.

        """
        stack = self.main_window.app_context.undo_stack
        self.undo_action = self._undo_action(stack)
        self.redo_action = self._redo_action(stack)
        self.find_action = QAction("Find", self.edit_menu)
        self.find_action.triggered.connect(
            self.main_window.action_service.focus_search_input
        )
        self._configure(self.find_action, QKeySequence.StandardKey.Find)
        for action in (self.undo_action, self.redo_action, self.find_action):
            self.edit_menu.addAction(action)

    def rebind(self, stack: QUndoStack) -> None:
        """
        Replace Undo and Redo with actions bound to ``stack``.

        Args:
            stack: The context's new undo stack.

        Side Effects:
            Swaps the Undo and Redo actions in :attr:`edit_menu` in place and
            schedules the old actions for deletion.

        """
        old_undo, old_redo = self.undo_action, self.redo_action
        self.undo_action = self._undo_action(stack)
        self.redo_action = self._redo_action(stack)
        for old, new in ((old_undo, self.undo_action), (old_redo, self.redo_action)):
            self.edit_menu.insertAction(old, new)
            self.edit_menu.removeAction(old)
            old.deleteLater()

    def _undo_action(self, stack: QUndoStack) -> QAction:
        """
        Build the Undo action for ``stack``.

        Args:
            stack: Undo stack the action tracks.

        Returns:
            Configured Undo action.

        """
        action = stack.createUndoAction(self.edit_menu)
        self._route(action, self.main_window.app_context.undo)
        self._configure(action, QKeySequence.StandardKey.Undo)
        return action

    def _redo_action(self, stack: QUndoStack) -> QAction:
        """
        Build the Redo action for ``stack``.

        Args:
            stack: Undo stack the action tracks.

        Returns:
            Configured Redo action.

        """
        action = stack.createRedoAction(self.edit_menu)
        self._route(action, self.main_window.app_context.redo)
        self._configure(action, QKeySequence.StandardKey.Redo)
        return action

    @staticmethod
    def _route(action: QAction, handler: "Callable[[], None]") -> None:
        """
        Send ``action``'s trigger to ``handler`` instead of the stack.

        Args:
            action: Action from ``createUndoAction`` or ``createRedoAction``.
            handler: ``AppContext.undo`` or ``AppContext.redo``.

        Side Effects:
            Drops the stack's own ``triggered`` connection.

        """
        action.triggered.disconnect()
        action.triggered.connect(handler)

    @staticmethod
    def _configure(action: QAction, key: QKeySequence.StandardKey) -> None:
        """
        Give ``action`` its standard shortcut and keep it out of the app menu.

        Must run before the action is added to a menu, or macOS may move it.

        Args:
            action: Action to configure.
            key: Platform standard key for the action.

        Side Effects:
            Sets the action's shortcut and menu role.

        """
        action.setShortcut(QKeySequence(key))
        action.setMenuRole(QAction.MenuRole.NoRole)
