"""Route the platform Undo and Redo keys out of the Modern English editor."""

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeyEvent, QKeySequence

#: Standard keys the Modern English editor must leave to the Edit menu.
APPLICATION_KEYS: tuple[QKeySequence.StandardKey, ...] = (
    QKeySequence.StandardKey.Undo,
    QKeySequence.StandardKey.Redo,
)


class TranslationUndoFilter(QObject):
    """
    Keep the Modern English editor from claiming the Undo and Redo keys.

    A :class:`~PySide6.QtWidgets.QTextEdit` accepts ``ShortcutOverride`` for
    Undo and Redo, which would turn them into document character undo. This
    filter consumes that override without accepting it, so the key goes to the
    Edit menu's Undo and Redo actions and runs the application undo.

    Args:
        parent: The Modern English editor that owns the filter.

    """

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the filter.

        Args:
            parent: The Modern English editor that owns the filter.

        """
        super().__init__(parent)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """
        Claim ``ShortcutOverride`` for the platform Undo and Redo keys.

        Args:
            watched: The editor the filter is installed on.
            event: The incoming event.

        Returns:
            ``True`` for an Undo or Redo ``ShortcutOverride``, so the editor
            never sees it; ``False`` for every other event.

        """
        if event.type() != QEvent.Type.ShortcutOverride or not isinstance(
            event, QKeyEvent
        ):
            return super().eventFilter(watched, event)
        return any(event.matches(key) for key in APPLICATION_KEYS)
