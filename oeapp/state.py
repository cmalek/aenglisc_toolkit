"""Qt-native application context for stable app-wide collaborators."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Final, cast

from PySide6.QtCore import QObject, QSettings, Signal

from oeapp.commands import CommandManager
from oeapp.db import clear_runtime_session, get_runtime_session, set_runtime_session

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.ui.main_window import MainWindow


class AppContext(QObject):
    """
    Stable application-wide Qt context.

    `AppContext` owns only app-lifetime collaborators and stable shared state.
    Transient selection, focus, and other widget-local state belong to the
    owning workspace or controller, not here.

    Args:
        session: Optional SQLAlchemy session to register as the runtime session.
        settings: Optional application settings object.
        parent: Optional Qt parent object.

    """

    #: Emitted when the active project id changes.
    current_project_id_changed = Signal(object)
    #: Emitted when the active chapter id changes.
    current_chapter_id_changed = Signal(object)
    #: Emitted when the active section id changes.
    current_section_id_changed = Signal(object)
    #: Emitted when copied annotation payload changes.
    copied_annotation_changed = Signal(object)

    def __init__(
        self,
        session: Session | None = None,
        settings: QSettings | None = None,
        parent: QObject | None = None,
    ) -> None:
        """
        Initialize the app context.

        Keyword Args:
            session: Optional SQLAlchemy session to register globally.
            settings: Optional settings object to reuse.
            parent: Optional Qt parent.

        """
        super().__init__(parent)
        if session is not None:
            set_runtime_session(session)
        #: Settings object for persisted preferences.
        self.settings = settings or QSettings()
        #: Main window registered with the context, if available.
        self.main_window: MainWindow | None = None
        #: Backing store for current project id.
        self._current_project_id: int | None = None
        #: Backing store for current chapter id.
        self._current_chapter_id: int | None = None
        #: Backing store for current section id.
        self._current_section_id: int | None = None
        #: Backing store for copied annotation payload.
        self._copied_annotation: dict[str, Any] | None = None
        #: Command manager for undoable app actions.
        self.command_manager = CommandManager(self.session)

    @property
    def session(self) -> Session:
        """
        Return the runtime SQLAlchemy session.

        Returns:
            Shared runtime session.

        """
        return get_runtime_session()

    @session.setter
    def session(self, session: Session) -> None:
        """
        Set the runtime SQLAlchemy session.

        Args:
            session: Session to register as the runtime session.

        Side Effects:
            Updates the command manager session.

        """
        set_runtime_session(session)
        self.command_manager.session = session

    def close_session(self) -> None:
        """
        Close and clear the runtime SQLAlchemy session.

        Side Effects:
            Closes and unregisters the runtime session.

        """
        clear_runtime_session()

    def set_main_window(self, main_window: MainWindow) -> None:
        """
        Register the main window with the context.

        Args:
            main_window: Main window bound to shared messaging and reload flows.

        """
        self.main_window = main_window

    @property
    def current_project_id(self) -> int | None:
        """
        Return the active project id.

        Returns:
            Active project id, or ``None`` when no project is open.

        """
        return self._current_project_id

    @current_project_id.setter
    def current_project_id(self, project_id: int | None) -> None:
        """
        Set or clear the active project id.

        Args:
            project_id: Active project id, or ``None`` to clear it.

        Side Effects:
            Emits :attr:`current_project_id_changed` when value changes.

        """
        if self._current_project_id == project_id:
            return
        self._current_project_id = project_id
        self.current_project_id_changed.emit(project_id)

    @property
    def current_chapter_id(self) -> int | None:
        """
        Return the active chapter id.

        Returns:
            Active chapter id, or ``None`` when no chapter is active.

        """
        return self._current_chapter_id

    @current_chapter_id.setter
    def current_chapter_id(self, chapter_id: int | None) -> None:
        """
        Set or clear the active chapter id.

        Args:
            chapter_id: Active chapter id, or ``None`` to clear it.

        Side Effects:
            Emits :attr:`current_chapter_id_changed` when value changes.

        """
        if self._current_chapter_id == chapter_id:
            return
        self._current_chapter_id = chapter_id
        self.current_chapter_id_changed.emit(chapter_id)

    @property
    def current_section_id(self) -> int | None:
        """
        Return the active section id.

        Returns:
            Active section id, or ``None`` when no section is active.

        """
        return self._current_section_id

    @current_section_id.setter
    def current_section_id(self, section_id: int | None) -> None:
        """
        Set or clear the active section id.

        Args:
            section_id: Active section id, or ``None`` to clear it.

        Side Effects:
            Emits :attr:`current_section_id_changed` when value changes.

        """
        if self._current_section_id == section_id:
            return
        self._current_section_id = section_id
        self.current_section_id_changed.emit(section_id)

    @property
    def copied_annotation(self) -> dict[str, Any] | None:
        """
        Return copied annotation payload for paste workflows.

        Returns:
            Copied annotation payload, or ``None`` when empty.

        """
        return self._copied_annotation

    @copied_annotation.setter
    def copied_annotation(self, annotation_state: dict[str, Any] | None) -> None:
        """
        Set or clear copied annotation payload.

        Args:
            annotation_state: Serialized annotation payload, or ``None`` to clear it.

        Side Effects:
            Emits :attr:`copied_annotation_changed` when value changes.

        """
        if self._copied_annotation == annotation_state:
            return
        self._copied_annotation = annotation_state
        self.copied_annotation_changed.emit(annotation_state)

    def has_current_project(self) -> bool:
        """
        Report whether an active project is set.

        Returns:
            ``True`` when an active project id is available.

        """
        return self.current_project_id is not None

    def reset(self) -> None:
        """
        Reset stable app-context state.

        Side Effects:
            Closes and recreates the runtime session, resets context state, and
            reinitializes the command manager.

        """
        self.close_session()
        self.command_manager = CommandManager(self.session)
        self.main_window = None
        self.current_project_id = None
        self.current_chapter_id = None
        self.current_section_id = None
        self.copied_annotation = None
        self.settings = QSettings()

    def show_message(self, message: str, duration: int = 2000) -> None:
        """
        Show a transient status message.

        Args:
            message: Message to show.

        Keyword Args:
            duration: Duration in milliseconds.

        """
        main_window = cast("MainWindow | None", self.main_window)
        if main_window is not None:
            main_window.messages.show_message(message, duration=duration)
        else:
            sys.stderr.write(message + "\n")

    def show_error(self, message: str, title: str = "Error") -> None:
        """
        Show an error message.

        Args:
            message: Message to show.

        Keyword Args:
            title: Message box title.

        """
        main_window = cast("MainWindow | None", self.main_window)
        if main_window is not None:
            main_window.messages.show_error(message, title)
        else:
            sys.stderr.write(f"[{title}] {message}\n")

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """
        Show a warning message.

        Args:
            message: Message to show.

        Keyword Args:
            title: Message box title.

        """
        main_window = cast("MainWindow | None", self.main_window)
        if main_window is not None:
            main_window.messages.show_warning(message, title)
        else:
            sys.stderr.write(f"[{title}] {message}\n")

    def show_information(self, message: str, title: str = "Information") -> None:
        """
        Show an informational message.

        Args:
            message: Message to show.

        Keyword Args:
            title: Message box title.

        """
        main_window = cast("MainWindow | None", self.main_window)
        if main_window is not None:
            main_window.messages.show_information(message, title)
        else:
            sys.stderr.write(f"[{title}] {message}\n")

    def undo(self) -> None:
        """
        Undo the most recent command.

        Side Effects:
            Refreshes or reloads the main window when an undo succeeds.

        """
        main_window = cast("MainWindow | None", self.main_window)
        assert main_window is not None, "Main window not set"  # noqa: S101
        if self.command_manager and self.command_manager.can_undo():
            needs_full_reload = False
            if self.command_manager.undo_stack:
                last_command = self.command_manager.undo_stack[-1]
                needs_full_reload = last_command.needs_full_reload
            if self.command_manager.undo():
                self.show_message("Undone")
                if not needs_full_reload and self.command_manager.redo_stack:
                    last_undone = self.command_manager.redo_stack[-1]
                    needs_full_reload = last_undone.needs_full_reload

                if needs_full_reload:
                    main_window.reload_project()
                else:
                    main_window.refresh_project()
            else:
                self.show_message("Undo failed")

    def redo(self) -> None:
        """
        Redo the most recently undone command.

        Side Effects:
            Refreshes or reloads the main window when a redo succeeds.

        """
        main_window = cast("MainWindow | None", self.main_window)
        assert main_window is not None, "Main window is not set"  # noqa: S101
        if self.command_manager and self.command_manager.can_redo():
            needs_full_reload = False
            if self.command_manager.redo_stack:
                last_command = self.command_manager.redo_stack[-1]
                needs_full_reload = last_command.needs_full_reload

            if self.command_manager.redo():
                self.show_message("Redone")
                if not needs_full_reload and self.command_manager.undo_stack:
                    last_redone = self.command_manager.undo_stack[-1]
                    needs_full_reload = last_redone.needs_full_reload

                if needs_full_reload:
                    main_window.reload_project()
                else:
                    main_window.refresh_project()
            else:
                self.show_message("Redo failed")


#: Default settings storage organization.
APP_SETTINGS_ORGANIZATION: Final[str] = "OpenAI"
