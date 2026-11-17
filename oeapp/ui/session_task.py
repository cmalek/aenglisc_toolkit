"""Run one database callable on a ``QThreadPool`` thread."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QEventLoop, QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QProgressDialog, QWidget
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from oeapp.db import (
    drop_ui_db_idle,
    get_runtime_session,
    on_ui_db_idle,
    pop_ui_db_busy,
    push_ui_db_busy,
    thread_runtime_session,
    ui_db_busy,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


class SessionTaskSignals(QObject):
    """
    Signals emitted on the UI thread when a pool task finishes.

    Args:
        parent: Widget that owns the task.

    """

    #: The callable's return value.
    succeeded = Signal(object)
    #: The exception the callable raised.
    failed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the instance.

        Args:
            parent: Widget that owns the task.

        """
        super().__init__(parent)
        #: Kept alive until ``run`` returns. ``QRunnable`` is not a ``QObject``.
        self.runnable: SessionRunnable | None = None
        #: GUI callback for a successful result.
        self._success_handler: Callable[[object], None] | None = None
        #: GUI callback for a failed result.
        self._failure_handler: Callable[[object], None] | None = None

    def connect_handlers(
        self,
        on_success: Callable[[object], None],
        on_failure: Callable[[object], None],
    ) -> None:
        """
        Deliver results to the GUI callbacks.

        Args:
            on_success: Slot called with the callable's return value.
            on_failure: Slot called with the exception the callable raised.

        """
        self._success_handler = on_success
        self._failure_handler = on_failure
        self.succeeded.connect(self._relay_success)
        self.failed.connect(self._relay_failure)

    @Slot(object)
    def _relay_success(self, result: object) -> None:
        """
        Release the database reservation and deliver a result.

        Args:
            result: The worker's return value.

        """
        pop_ui_db_busy()
        if self._success_handler is not None:
            self._success_handler(result)

    @Slot(object)
    def _relay_failure(self, exc: object) -> None:
        """
        Release the database reservation and deliver a failure.

        Args:
            exc: The exception raised on the worker.

        """
        pop_ui_db_busy()
        if self._failure_handler is not None:
            self._failure_handler(exc)


class SessionRunnable(QRunnable):
    """
    Call one function on a pool thread with a private SQLAlchemy session.

    Args:
        engine: Engine shared with the UI session.
        fn: Work to run. It must not touch widgets or the UI session.
        signals: UI-thread signals.

    """

    def __init__(
        self, engine: Engine, fn: Callable[[], Any], signals: SessionTaskSignals
    ) -> None:
        """
        Initialize the instance.

        Args:
            engine: Engine shared with the UI session. The worker opens its
                own session on it.
            fn: Work to run. It must not touch widgets or the UI session.
            signals: UI-thread signals.

        """
        super().__init__()
        self.setAutoDelete(False)
        #: Database engine.
        self._engine = engine
        #: Work callable.
        self._fn = fn
        #: Completion signals.
        self._signals = signals

    def run(self) -> None:
        """Run the callable and emit the outcome."""
        session = Session(bind=self._engine)
        try:
            with thread_runtime_session(session):
                result = self._fn()
                session.commit()
            self._signals.succeeded.emit(result)
        except Exception as exc:  # noqa: BLE001 - re-raised on the UI thread
            session.rollback()
            self._signals.failed.emit(exc)
        finally:
            session.close()


def _copy_pending(
    session: Session,
) -> tuple[
    list[tuple[object, dict[str, object]]],
    list[tuple[object, str, object]],
    list[tuple[object, str, tuple[object, ...], tuple[object, ...]]],
    list[object],
    list[tuple[object, str, object]],
    list[object],
]:
    """
    Record unsaved session state so a rollback can be undone in memory.

    Args:
        session: UI session about to release its SQLite lock.

    Returns:
        Column edits, changed scalar links, collection edits, new objects,
        links on those new objects, and deleted objects.

    """
    columns: list[tuple[object, dict[str, object]]] = []
    scalars: list[tuple[object, str, object]] = []
    collections: list[tuple[object, str, tuple[object, ...], tuple[object, ...]]] = []
    for obj in list(session.dirty):
        if obj in session.new or obj in session.deleted:
            continue
        _copy_object(obj, columns, scalars, collections)
    new_links = [
        (obj, key, value)
        for obj in list(session.new)
        for key, value in _scalar_values(obj)
    ]
    return (
        columns,
        scalars,
        collections,
        list(session.new),
        new_links,
        list(session.deleted),
    )


def _copy_object(
    obj: object,
    columns: list[tuple[object, dict[str, object]]],
    scalars: list[tuple[object, str, object]],
    collections: list[tuple[object, str, tuple[object, ...], tuple[object, ...]]],
) -> None:
    """
    Record one persistent object's unsaved column and relationship edits.

    Args:
        obj: Persistent instance that is dirty.
        columns: Column edits collected for restore.
        scalars: Many-to-one edits collected for restore.
        collections: Collection edits collected for restore.

    """
    insp = sa_inspect(obj)
    if insp is None:
        return
    changed = {
        column.key: getattr(obj, column.key)
        for column in insp.mapper.column_attrs
        if insp.attrs[column.key].history.has_changes()
    }
    if changed:
        columns.append((obj, changed))
    for rel in insp.mapper.relationships:
        history = insp.attrs[rel.key].history
        if not history.has_changes():
            continue
        if rel.uselist:
            collections.append(
                (obj, rel.key, tuple(history.added), tuple(history.deleted))
            )
        else:
            scalars.append((obj, rel.key, getattr(obj, rel.key)))


def _scalar_values(obj: object) -> list[tuple[str, object]]:
    """
    Return many-to-one values on a new object.

    Args:
        obj: Instance that has not been committed.

    Returns:
        ``(attribute, value)`` pairs for scalar relationships.

    """
    insp = sa_inspect(obj)
    if insp is None:
        return []
    return [
        (rel.key, getattr(obj, rel.key))
        for rel in insp.mapper.relationships
        if not rel.uselist
    ]


def _restore_pending(
    session: Session,
    pending: tuple[
        list[tuple[object, dict[str, object]]],
        list[tuple[object, str, object]],
        list[tuple[object, str, tuple[object, ...], tuple[object, ...]]],
        list[object],
        list[tuple[object, str, object]],
        list[object],
    ],
) -> None:
    """
    Put unsaved edits back after the database transaction was rolled back.

    Args:
        session: UI session whose transaction was rolled back.
        pending: State captured by :func:`_copy_pending`.

    """
    columns, scalars, collections, new_objects, new_links, deleted = pending
    for obj in new_objects:
        session.add(obj)
    for obj, key, value in new_links:
        setattr(obj, key, value)
    for obj, values in columns:
        for key, value in values.items():
            setattr(obj, key, value)
    for obj, key, value in scalars:
        setattr(obj, key, value)
    for obj, key, added, removed in collections:
        group = getattr(obj, key)
        for item in added:
            if item not in group:
                group.append(item)
        for item in removed:
            if item in group:
                group.remove(item)
    for obj in deleted:
        session.delete(obj)


def _release_ui_lock(session: Session) -> None:
    """
    Drop the UI connection's SQLite lock without saving or losing edits.

    Side Effects:
        Rolls the database transaction back. Unsaved objects are put back
        on the session in memory only.

    Args:
        session: UI runtime session.

    """
    # ponytail: reapply the identity map after rollback. Commit would persist
    # edits the user had not saved, including from the automatic backup timer.
    pending = _copy_pending(session)
    session.rollback()
    _restore_pending(session, pending)


def _wait_until_db_idle() -> None:
    """Block until no other pool task is using the database."""
    if not ui_db_busy():
        return
    loop = QEventLoop()

    def stop() -> None:
        loop.quit()

    on_ui_db_idle(stop)
    try:
        if ui_db_busy():
            loop.exec()
    finally:
        drop_ui_db_idle(stop)


def _worker_engine() -> Engine:
    """
    Return the engine behind the UI session.

    Side Effects:
        Ends the UI session's database transaction so SQLite drops its lock.
        Unsaved edits stay in memory and are not written.

    Returns:
        The engine the worker session should bind.

    Raises:
        RuntimeError: If the UI session has no engine.

    """
    session = get_runtime_session()
    _release_ui_lock(session)
    bind = session.get_bind()
    if isinstance(bind, Connection):
        return bind.engine
    if isinstance(bind, Engine):
        return bind
    msg = "Runtime session has no database engine."
    raise RuntimeError(msg)


def start_session_task(
    parent: QObject,
    fn: Callable[[], Any],
    on_success: Callable[[object], None],
    on_failure: Callable[[object], None],
) -> SessionTaskSignals:
    """
    Start ``fn`` on the global pool and return before it finishes.

    The callbacks run on the UI thread. ``fn`` must return plain values, not
    ORM instances: its session is closed before the callback runs.

    Args:
        parent: Owner of the signal object.
        fn: Work that uses :func:`oeapp.db.get_runtime_session`.
        on_success: Slot called with ``fn``'s return value.
        on_failure: Slot called with the exception ``fn`` raised.

    Returns:
        The signal object. It keeps the runnable alive.

    """
    _wait_until_db_idle()
    push_ui_db_busy()
    try:
        signals = SessionTaskSignals(parent)
        runnable = SessionRunnable(_worker_engine(), fn, signals)
        signals.runnable = runnable
        signals.connect_handlers(on_success, on_failure)
        QThreadPool.globalInstance().start(runnable)
    except Exception:
        pop_ui_db_busy()
        raise
    return signals


class _ModalSessionTask(QObject):
    """
    Show a busy dialog until one pool task finishes.

    Args:
        parent: Dialog parent.
        label: Progress text.

    """

    def __init__(self, parent: QWidget, label: str) -> None:
        """
        Initialize the instance.

        Args:
            parent: Dialog parent.
            label: Progress text.

        """
        super().__init__(parent)
        #: Progress dialog.
        self._dialog = QProgressDialog(label, "", 0, 0, parent)
        #: Nested loop that keeps the caller's stack until the task ends.
        self._loop = QEventLoop(self)
        #: Set once the task has emitted.
        self._done = False
        #: Return value from the worker.
        self._result: Any = None
        #: Exception from the worker.
        self._error: BaseException | None = None
        self._dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._dialog.setMinimumDuration(0)
        self._dialog.setCancelButton(None)
        self._dialog.setAutoClose(False)
        self._dialog.setAutoReset(False)

    def run(self, fn: Callable[[], Any]) -> Any:
        """
        Run ``fn`` and block the caller without freezing the window.

        Args:
            fn: Work that uses :func:`oeapp.db.get_runtime_session`.

        Returns:
            Whatever ``fn`` returned.

        Raises:
            Exception: Whatever ``fn`` raised.

        """
        signals = start_session_task(self, fn, self._on_success, self._on_failure)
        self._dialog.show()
        if not self._done:
            self._loop.exec()
        self._dialog.close()
        self._dialog.deleteLater()
        signals.runnable = None
        if self._error is not None:
            raise self._error
        return self._result

    @Slot(object)
    def _on_success(self, result: object) -> None:
        """
        Store a successful result and leave the nested loop.

        Args:
            result: The worker's return value.

        """
        self._result = result
        self._finish()

    @Slot(object)
    def _on_failure(self, exc: object) -> None:
        """
        Store a failure and leave the nested loop.

        Args:
            exc: The exception raised on the worker.

        """
        if isinstance(exc, BaseException):
            self._error = exc
        self._finish()

    def _finish(self) -> None:
        """Mark the task done and quit the nested loop if it is running."""
        self._done = True
        if self._loop.isRunning():
            self._loop.quit()


def run_session_task[T](parent: QWidget, label: str, fn: Callable[[], T]) -> T:
    """
    Run ``fn`` on the pool while a modal progress dialog is visible.

    The caller stays synchronous: menu actions and tests get the return value
    or the exception. The window still paints, because this waits in a nested
    event loop rather than in the database call.

    ponytail: no cancel button. The export and backup functions do not poll a
    stop flag, and ``QRunnable`` has no ``requestInterruption``.

    Args:
        parent: Dialog parent.
        label: Progress text.
        fn: Work that uses :func:`oeapp.db.get_runtime_session`. It must
            return plain values, not ORM instances.

    Returns:
        Whatever ``fn`` returned.

    Raises:
        Exception: Whatever ``fn`` raised.

    """
    task = _ModalSessionTask(parent, label)
    try:
        return cast("T", task.run(fn))
    finally:
        task.deleteLater()
