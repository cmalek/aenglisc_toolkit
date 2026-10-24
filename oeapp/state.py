"""Qt-native application context for stable app-wide collaborators."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QUndoStack

from oeapp.commands import UndoCommand
from oeapp.db import clear_runtime_session, get_runtime_session, set_runtime_session
from oeapp.ui.typed_run import TypedRun
from oeapp.ui.undo_presenter import UndoPresenter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.models import AnnotationJson
    from oeapp.ui.main_window import MainWindow

#: Maximum number of commands kept on the application undo stack.
UNDO_LIMIT: Final[int] = 50


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
    #: Emitted with the new stack when :attr:`undo_stack` is replaced.
    undo_stack_replaced = Signal(object)

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
        #: Backing store for the Copied Annotation (validated payload).
        self._copied_annotation: AnnotationJson | None = None
        #: Project-scoped undo history for app actions.
        self.undo_stack: QUndoStack = self._new_undo_stack()
        #: Open run of Modern English typing that merges into one undo step.
        self.typed_run: TypedRun = TypedRun()

    def _new_undo_stack(self) -> QUndoStack:
        """
        Build an empty undo stack with the application undo limit.

        Returns:
            New stack parented to this context.

        """
        stack = QUndoStack(self)
        stack.setUndoLimit(UNDO_LIMIT)
        return stack

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

        """
        set_runtime_session(session)

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
            Clears :attr:`undo_stack` when leaving an open project and emits
            :attr:`current_project_id_changed` when value changes.

        """
        if self._current_project_id == project_id:
            return
        if self._current_project_id is not None:
            self.typed_run.end()
            self.undo_stack.clear()
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
    def copied_annotation(self) -> AnnotationJson | None:
        """
        Return the Copied Annotation for paste workflows.

        Returns:
            Validated annotation payload, or ``None`` when empty.

        """
        return self._copied_annotation

    @copied_annotation.setter
    def copied_annotation(self, annotation: AnnotationJson | None) -> None:
        """
        Set or clear the Copied Annotation.

        Args:
            annotation: Validated annotation payload, or ``None`` to clear it.

        Side Effects:
            Emits :attr:`copied_annotation_changed` with a plain JSON dict (or
            ``None``) when the value changes.

        """
        if self._copied_annotation == annotation:
            return
        self._copied_annotation = annotation
        self.copied_annotation_changed.emit(
            None if annotation is None else annotation.model_dump(mode="json")
        )

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
            replaces the undo stack with a new empty one and emits
            :attr:`undo_stack_replaced`.

        """
        self.close_session()
        self.typed_run.end()
        self.undo_stack.deleteLater()
        self.undo_stack = self._new_undo_stack()
        self.undo_stack_replaced.emit(self.undo_stack)
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
            Ends :attr:`typed_run`, then has :class:`UndoPresenter` undo the
            top of :attr:`undo_stack` and show the result, first loading the
            changed sentence's section for a translation edit. When the
            command's ``undo`` fails, puts the stack index back and shows
            "Undo failed" without refreshing.

        """
        main_window = cast("MainWindow | None", self.main_window)
        assert main_window is not None, "Main window not set"  # noqa: S101
        if not self.undo_stack.canUndo():
            return
        self.typed_run.end()
        command = self.undo_stack.command(self.undo_stack.index() - 1)
        UndoPresenter(main_window).run_step(command, self._undo_step)

    def _undo_step(self) -> bool:
        """
        Undo the top of :attr:`undo_stack`.

        Side Effects:
            Moves the stack index back and shows "Undone". When the command's
            ``undo`` fails, puts the index back and shows "Undo failed".

        Returns:
            ``True`` when the undo succeeded.

        """
        command = self.undo_stack.command(self.undo_stack.index() - 1)
        outcome = command.outcome if isinstance(command, UndoCommand) else {}
        self.undo_stack.undo()
        if not outcome.get("undo_ok", True):
            self.undo_stack.redo()
            self.show_message("Undo failed")
            return False
        self.show_message("Undone")
        return True

    def redo(self) -> None:
        """
        Redo the most recently undone command.

        Side Effects:
            Ends :attr:`typed_run`, then has :class:`UndoPresenter` redo the
            next command on :attr:`undo_stack` and show the result, the same
            way :meth:`undo` does. When ``execute`` fails, the stack drops the
            command and "Redo failed" is shown without refreshing.

        """
        main_window = cast("MainWindow | None", self.main_window)
        assert main_window is not None, "Main window is not set"  # noqa: S101
        if not self.undo_stack.canRedo():
            return
        self.typed_run.end()
        command = self.undo_stack.command(self.undo_stack.index())
        UndoPresenter(main_window).run_step(command, self._redo_step)

    def _redo_step(self) -> bool:
        """
        Redo the next command on :attr:`undo_stack`.

        Side Effects:
            Moves the stack index forward and shows "Redone". When ``execute``
            fails, the stack drops the command and "Redo failed" is shown.

        Returns:
            ``True`` when the redo succeeded.

        """
        command = self.undo_stack.command(self.undo_stack.index())
        outcome = command.outcome if isinstance(command, UndoCommand) else {}
        self.undo_stack.redo()
        if not outcome.get("ok", True):
            self.show_message("Redo failed")
            return False
        self.show_message("Redone")
        return True


#: Default settings storage organization.
APP_SETTINGS_ORGANIZATION: Final[str] = "OpenAI"
