import sys
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QSettings

from oeapp.commands import CommandManager
from oeapp.db import SessionLocal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.ui.main_window import MainWindow


#: The key for the copied annotation.
COPIED_ANNOTATION = "annotation:copy"
#: The key for the current project ID loaded in the application.
CURRENT_PROJECT_ID = "project:current:id"
#: The key for the selected sentence card in the main window.
SELECTED_SENTENCE_CARD = "sentence:card:selected"


class ApplicationState(dict):
    """
    Application state singleton.

    This is a singleton that stores the application state.  It is used to store the
    application state during sessions.  It is also used to store the application
    state for the main window.
    """

    _instance: ApplicationState | None = None
    #: The SQLAlchemy session.
    _session: Session | None = None
    #: Settings
    settings: QSettings
    #: Command manager
    command_manager: CommandManager
    #: Main window
    main_window: MainWindow | None = None

    def __new__(cls) -> ApplicationState:  # noqa: PYI034
        """
        Create a new instance of the application state singleton.

        - If the instance is not initialized, initialize it by calling :meth:`reset`.
        - Return the instance.

        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reset()
        return cast("ApplicationState", cls._instance)

    def __del__(self) -> None:
        """Delete the application state singleton."""
        if self._session is not None:
            self._session.close()
            self._session = None
        self.__class__._instance = None

    @property
    def session(self) -> Session:
        """
        Get the SQLAlchemy session.

        If the session is not initialized, initialize it.

        Returns:
            The SQLAlchemy session.

        """
        if self._session is None:
            self._session = SessionLocal()
        return cast("Session", self._session)

    @session.setter
    def session(self, session: Session) -> None:
        """
        Set the SQLAlchemy session.  This is used for our tests.

        Args:
            session: The SQLAlchemy session to set.

        """
        self._session = session
        self.command_manager.session = session

    def set_main_window(self, main_window: MainWindow) -> None:
        """
        Set the main window.

        Args:
            main_window: The main window to set.

        """
        self.main_window = main_window

    def reset(self) -> None:
        """
        Reset the application state.

        - Close the current session.
        - Set the session to ``None`.
        - Set the main window to ``None``.
        - Clear the application state dictionary.
        - Set the command manager to a new CommandManager object with the new session.
        - Set the settings to a new QSettings object.
        """
        self.session.close()
        self._session = None
        self.command_manager = CommandManager(self.session)
        self.main_window = None
        self.settings = QSettings()
        self.clear()

    def show_message(self, message: str, duration: int = 2000) -> None:
        """
        Show a message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            duration: Duration of the message in milliseconds (default: 2000)

        """
        main_window = cast("MainWindow", self.main_window)
        if main_window:
            main_window.show_message(message, duration=duration)
        else:
            sys.stderr.write(message + "\n")

    def show_error(self, message: str, title: str = "Error") -> None:
        """
        Show an error message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message

        """
        main_window = cast("MainWindow", self.main_window)
        if main_window:
            main_window.show_error(message, title)
        else:
            sys.stderr.write(f"[{title}] " + message + "\n")

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """
        Show a warning message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message

        """
        main_window = cast("MainWindow", self.main_window)
        if main_window:
            main_window.show_warning(message, title)
        else:
            sys.stderr.write(f"[{title}] " + message + "\n")

    def show_information(self, message: str, title: str = "Information") -> None:
        """
        Show an information message in the status bar.
        """
        main_window = cast("MainWindow", self.main_window)
        if main_window:
            main_window.show_information(message, title)
        else:
            sys.stderr.write(f"[{title}] " + message + "\n")

    def undo(self) -> None:
        """
        Undo last action.

        - If there is no command manager or the command manager cannot undo, do nothing.
        - If the command manager can undo, undo the last action.
        - If the undo fails, show a message in the status bar.
        """
        main_window = cast("MainWindow", self.main_window)
        assert main_window is not None, "Main window not set"  # noqa: S101
        if self.command_manager and self.command_manager.can_undo():
            # Check if the command to undo is a structural change (like merge or
            # add sentence)
            needs_full_reload = False
            if self.command_manager.undo_stack:
                last_command = self.command_manager.undo_stack[-1]
                needs_full_reload = last_command.needs_full_reload
            if self.command_manager.undo():
                self.show_message("Undone")
                # After undo, the command is in redo_stack, check if it was a
                # structural change
                if not needs_full_reload and self.command_manager.redo_stack:
                    last_undone = self.command_manager.redo_stack[-1]
                    needs_full_reload = last_undone.needs_full_reload

                if needs_full_reload:
                    # Reload entire project structure after structural change
                    main_window.reload_project_structure()
                else:
                    main_window.refresh_all_cards()
            else:
                self.show_message("Undo failed")

    def redo(self) -> None:
        """
        Redo last undone action.

        - If there is no command manager or the command manager cannot redo, do nothing.
        - If the command manager can redo, redo the last action.
        - If the redo fails, show a message in the status bar.
        """
        main_window = cast("MainWindow", self.main_window)
        assert main_window is not None, "Main window is not set"  # noqa: S101
        if self.command_manager and self.command_manager.can_redo():
            # Check if the command to redo is a structural change (like merge or
            # add sentence)
            needs_full_reload = False
            if self.command_manager.redo_stack:
                last_command = self.command_manager.redo_stack[-1]
                needs_full_reload = last_command.needs_full_reload

            if self.command_manager.redo():
                self.show_message("Redone")
                # After redo, the command is in undo_stack, check if it was a
                # structural change
                if not needs_full_reload and self.command_manager.undo_stack:
                    last_redone = self.command_manager.undo_stack[-1]
                    needs_full_reload = last_redone.needs_full_reload

                if needs_full_reload:
                    # Reload entire project structure after structural change
                    main_window.reload_project_structure()
                else:
                    main_window.refresh_all_cards()
            else:
                self.show_message("Redo failed")
