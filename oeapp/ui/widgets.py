from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QTextEdit


class OldEnglishTextEdit(QTextEdit):
    """
    QTextEdit that emits a signal when clicked.  Used for the Old English text
    edit.

    This currently handles:

    - Mouse clicks
    - Double mouse clicks
    - Key presses for annotation copy/paste

    """

    clicked = Signal(QPoint, object)  # position, modifiers
    double_clicked = Signal(QPoint)
    # Signals for annotation copy/paste
    copy_annotation_requested = Signal()
    paste_annotation_requested = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse press event and emit clicked signal.

        Args:
            event: Mouse press event

        """
        super().mousePressEvent(event)
        self.clicked.emit(event.position().toPoint(), event.modifiers())

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse double-click event and emit double_clicked signal.

        Args:
            event: Mouse double-click event

        """
        super().mouseDoubleClickEvent(event)
        self.double_clicked.emit(event.position().toPoint())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Handle key press events for annotation copy/paste.

        Intercepts Cmd/Ctrl+C and Cmd/Ctrl+V to emit signals for annotation
        copy/paste when a token is selected.

        Args:
            event: Key event

        """
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_annotation_requested.emit()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_annotation_requested.emit()
            event.accept()
            return

        # For arrow keys, ignore them so they bubble up to SentenceCard
        # when a token is selected (SentenceCard will handle navigation)
        # ONLY if we are in read-only mode (not editing OE)
        if self.isReadOnly() and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            event.ignore()
            return

        # For all other keys, use default behavior
        super().keyPressEvent(event)
