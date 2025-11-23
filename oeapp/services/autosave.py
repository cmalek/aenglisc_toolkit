"""Autosave service with debounced writes."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer

if TYPE_CHECKING:
    from collections.abc import Callable


class AutosaveService(QObject):
    """
    Service for debounced autosave operations.

    Args:
        save_callback: Function to call when saving
        debounce_ms: Debounce delay in milliseconds

    """

    def __init__(
        self, save_callback: Callable[[], None], debounce_ms: int = 500
    ) -> None:
        super().__init__()
        #: The function to call when saving.
        self.save_callback = save_callback
        #: The debounce delay in milliseconds.
        self.debounce_ms = debounce_ms
        #: The timer for the debounce.
        self._timer: QTimer | None = None
        #: Whether there is a pending autosave.
        self._pending = False

    def trigger(self) -> None:
        """
        Trigger autosave (will be debounced).
        """
        self._pending = True
        # Cancel existing timer if any
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
        # Create and start new timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._save)
        self._timer.start(self.debounce_ms)

    def _save(self) -> None:
        """
        Execute the save callback.

        This method is either called manually by the user via the :meth:`save_now`
        method or called by the autosave timer when the debounce delay has
        elapsed. It checks if there is a pending autosave and if so, calls the
        save callback. If the save callback raises an exception, it is caught
        and the pending autosave is set to False.
        """
        if self._pending:
            try:
                self.save_callback()
                self._pending = False
            except Exception as e:  # noqa: BLE001
                print(f"Autosave error: {e}")
                self._pending = False

    def save_now(self) -> None:
        """
        Force immediate save (bypasses debounce), meaning the autosave timer is
        cancelled and the save callback is called immediately.

        """
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._pending = False
        try:
            self.save_callback()
        except Exception as e:  # noqa: BLE001
            print(f"Save error: {e}")

    def cancel(self) -> None:
        """
        Cancel pending autosave, meaning the autosave timer is cancelled and the
        save callback is not called.
        """
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._pending = False
