from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from PySide6.QtGui import QColor

    from oeapp.ui.highlighting import HighlighterCommandBase


class SentenceFilterDialog(AnnotationLookupsMixin, QDialog):
    """
    Dialog for selecting which items to highlight in an Old English sentence.
    """

    #: Title of the dialog
    TITLE: ClassVar[str] = "Select Items to Highlight"
    #: Colors for the items
    COLORS: ClassVar[dict[str | None, "QColor"]] = {}
    #: Mapping of codes to names.  We use this to display the name of the item
    #: in the checkbox.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str]] = {}

    # Signal emitted when selected items change
    selection_changed = Signal(set)
    # Signal emitted when dialog is closed
    dialog_closed = Signal()

    @classmethod
    def full_filter_selection(cls) -> set[str]:
        """
        Get the full filter selection.

        Returns:
            Set of all possible filter selections codes

        """
        if cls.CODE_TO_NAME_MAPPING is None:
            return set()
        return {
            k
            for k in cast("dict[str, str | None]", cls.CODE_TO_NAME_MAPPING)
            if k != ""
        }

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the mixin.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self.command: HighlighterCommandBase | None = None
        self.checkboxes: dict[str, QCheckBox] = {}
        self.filter_selection: set[str] = set()
        self.reset_filter_selection()
        self.build()

    def reset_filter_selection(self) -> None:
        """
        Reset the filter selection to all possible values.
        """
        self.filter_selection = self.full_filter_selection()

    def build(self) -> None:
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title label
        title_label = QLabel(self.TITLE)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        for code in self.CODE_TO_NAME_MAPPING:
            if code is None or code == "":
                continue
            row = self.build_row(code)
            layout.addLayout(row)

        button_layout = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_button)
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def build_row(self, code: str) -> QHBoxLayout:
        """
        Build the rows for the checkboxes.

        Args:
            code: Code for the item

        Returns:
            QHBoxLayout containing checkbox and color indicator

        """
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Create checkbox
        name = self.CODE_TO_NAME_MAPPING.get(code, code)
        checkbox = QCheckBox(name)
        checkbox.setChecked(True)  # Default: all selected
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        self.checkboxes[code] = checkbox
        row_layout.addWidget(checkbox)

        # Create color indicator
        color = self.COLORS.get(code)
        if color:
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            # Convert QColor to RGB for stylesheet
            rgb = f"rgb({color.red()}, {color.green()}, {color.blue()})"
            color_label.setStyleSheet(
                f"background-color: {rgb}; border: 1px solid #999;"
            )
            color_label.setToolTip(f"Color for {name}")
            row_layout.addWidget(color_label)

        row_layout.addStretch()
        return row_layout

    def _on_checkbox_changed(self) -> None:
        """Handle checkbox state change and emit signal."""
        selected = set()
        for code, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.add(code)
        self.filter_selection = selected
        self.selection_changed.emit(selected)

    def _select_all(self) -> None:
        """Select all case checkboxes."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselect all case checkboxes."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_items(self) -> set[str]:
        """
        Get the currently selected items.

        Returns:
            Set of selected item codes

        """
        return self.filter_selection.copy()

    def set_selected_items(self, items: set[str]) -> None:
        """
        Set which items are selected.

        Args:
            items: Set of item codes to select

        """
        self.filter_selection = items.copy()
        # Block signals temporarily to avoid multiple emissions
        for checkbox in self.checkboxes.values():
            checkbox.blockSignals(True)  # noqa: FBT003
        for code, checkbox in self.checkboxes.items():
            checkbox.setChecked(code in items)
        for checkbox in self.checkboxes.values():
            checkbox.blockSignals(False)  # noqa: FBT003
        # Emit signal once with final state
        self.selection_changed.emit(self.filter_selection)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """
        Handle dialog close event.

        Args:
            event: Close event

        """
        self.dialog_closed.emit()
        super().closeEvent(event)


class PartOfSpeechFilterDialog(SentenceFilterDialog):
    """
    Dialog for selecting which parts of speech to highlight.
    """

    #: Title of the dialog
    TITLE: ClassVar[str] = "Select Parts of Speech to Highlight"
    #: Colors for the parts of speech
    COLORS: ClassVar[dict[str | None, "QColor"]] = AnnotationLookupsMixin.POS_COLORS
    #: Mapping of codes to names.  We use this to display the name of the part of speech
    #: in the checkbox.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str]] = (
        AnnotationLookupsMixin.PART_OF_SPEECH_MAP
    )


class CaseFilterDialog(SentenceFilterDialog):
    """
    Dialog for selecting which cases to highlight.
    """

    #: Title of the dialog
    TITLE: ClassVar[str] = "Select Cases to Highlight"
    #: Colors for the cases
    COLORS: ClassVar[dict[str | None, "QColor"]] = AnnotationLookupsMixin.CASE_COLORS
    #: Mapping of codes to names.  We use this to display the name of the case
    #: in the checkbox.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str]] = (
        AnnotationLookupsMixin.CASE_MAP
    )


class NumberFilterDialog(SentenceFilterDialog):
    """
    Dialog for selecting which numbers to highlight.
    """

    #: Title of the dialog
    TITLE: ClassVar[str] = "Select Numbers to Highlight"
    #: Colors for the numbers
    COLORS: ClassVar[dict[str | None, "QColor"]] = AnnotationLookupsMixin.NUMBER_COLORS
    #: Mapping of codes to names.  We use this to display the name of the number
    #: in the checkbox.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str]] = (
        AnnotationLookupsMixin.PRONOUN_NUMBER_MAP
    )
