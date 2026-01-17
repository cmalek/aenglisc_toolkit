from PySide6.QtWidgets import QFrame, QWidget


class HorizontalSeparatorWidget(QFrame):
    """
    A simple horizontal separator widget.

    Keyword Args:
        parent: Parent widget
        height: Height of the separator in pixels

    Example:
        >>> separator = HorizontalSeparatorWidget()
        >>> separator.setStyleSheet("border: 1px solid palette(border);")
        >>> separator.show()

    """

    def __init__(self, parent: QWidget | None = None, height: int = 3):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setLineWidth(height)
        self.setMidLineWidth(height)
        self.setStyleSheet(f"border: {height}px solid palette(border);")
