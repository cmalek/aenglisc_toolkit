"""Remembered annotation management dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, cast

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.models import RememberedAnnotation
from oeapp.services.remembered_annotation_service import RememberedAnnotationService
from oeapp.ui.dialogs.annotation_modal import AnnotationModal

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation


class RememberedAnnotationsDialog(QDialog):
    """
    Manage remembered annotations for one scope.

    Args:
        project_id: Project scope to edit, or ``None`` for global entries.
        parent: Parent widget for the dialog.

    """

    #: Default dialog width in pixels.
    DIALOG_WIDTH: Final[int] = 760
    #: Default dialog height in pixels.
    DIALOG_HEIGHT: Final[int] = 420

    def __init__(self, project_id: int | None, parent: QWidget | None = None) -> None:
        """
        Initialize the remembered-annotation management dialog.

        Args:
            project_id: Project scope to edit, or ``None`` for global entries.
            parent: Parent widget for the dialog.

        """
        super().__init__(parent)
        #: Project scope being managed, or ``None`` for global remembered entries.
        self.project_id = project_id
        #: Service used to persist remembered annotation edits.
        self.service = RememberedAnnotationService()
        self._build()
        self._reload_entries()

    @property
    def title(self) -> str:
        """
        Return the dialog title for the current scope.

        Returns:
            The title string shown in the window chrome.

        """
        if self.project_id is None:
            return "Global Remembered Annotations"
        return "Project Remembered Annotations"

    def _build(self) -> None:
        """Build the remembered annotation management UI."""
        self.setWindowTitle(self.title)
        self.setModal(True)
        self.resize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)

        layout = QVBoxLayout(self)

        self.empty_label = QLabel("No remembered annotations in this scope.")
        layout.addWidget(self.empty_label)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Token", "POS", "Summary", "Root", "Modern English"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        new_button = QPushButton("New", self)
        new_button.clicked.connect(self._create_new)
        button_row.addWidget(new_button)
        edit_button = QPushButton("Edit", self)
        edit_button.clicked.connect(self._edit_selected)
        button_row.addWidget(edit_button)
        delete_button = QPushButton("Delete", self)
        delete_button.clicked.connect(self._delete_selected)
        button_row.addWidget(delete_button)
        button_row.addStretch()
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def _reload_entries(self) -> None:
        """Reload remembered entries for the current scope into the table."""
        entries = RememberedAnnotation.list_for_scope(self.project_id)
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            summary = " ".join(
                part
                for part in (
                    entry.format_pos(cast("Annotation", entry)),
                    entry.format_gender(cast("Annotation", entry)),
                    entry.format_context(cast("Annotation", entry)),
                )
                if part
            )
            values = [
                entry.token_text,
                entry.pos or "",
                summary,
                entry.root or "",
                entry.modern_english_meaning or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(1, entry.id)
                self.table.setItem(row, column, item)
        self.empty_label.setVisible(len(entries) == 0)
        self.table.setVisible(len(entries) > 0)

    def _selected_entry(self) -> RememberedAnnotation | None:
        """
        Return the currently selected remembered entry.

        Returns:
            The selected remembered annotation, or ``None`` when nothing valid
            is selected.

        """
        current_row = self.table.currentRow()
        if current_row < 0:
            return None
        item = self.table.item(current_row, 0)
        if item is None:
            return None
        entry_id = item.data(1)
        if not isinstance(entry_id, int):
            return None
        return RememberedAnnotation.get(entry_id)

    def _create_new(self) -> None:
        """Create a new remembered annotation entry."""
        token_text, accepted = QInputDialog.getText(
            self,
            "Remembered Token",
            "Exact token text:",
            text="",
        )
        if not accepted:
            return
        token_text = token_text.strip()
        if not token_text:
            QMessageBox.warning(self, "Invalid Token", "Token text cannot be empty.")
            return
        existing = RememberedAnnotation.get_for_scope(token_text, self.project_id)
        if existing is not None:
            QMessageBox.information(
                self,
                "Duplicate Token",
                "A remembered annotation for this token already exists in this scope. Opening it for editing.",  # noqa: E501
            )
            self._open_editor(existing)
            return
        self._open_editor(RememberedAnnotation(token_text=token_text))

    def _edit_selected(self) -> None:
        """Edit the currently selected remembered annotation."""
        entry = self._selected_entry()
        if entry is None:
            return
        self._open_editor(entry)

    def _open_editor(self, entry: RememberedAnnotation) -> None:
        """
        Open the remembered entry editor modal.

        Args:
            entry: Remembered annotation entry to edit and persist on save.

        """
        modal = AnnotationModal(remembered_annotation=entry, parent=self)
        if modal.exec():
            self.service.save_entry(
                token_text=entry.token_text,
                project_id=self.project_id,
                field_data=entry.annotation_payload(),
            )
            self._reload_entries()

    def _delete_selected(self) -> None:
        """Delete the currently selected remembered annotation with confirmation."""
        entry = self._selected_entry()
        if entry is None:
            return
        confirmed = QMessageBox.question(
            self,
            "Delete Remembered Annotation",
            f"Delete remembered annotation for '{entry.token_text}'?",
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        entry.delete()
        self._reload_entries()
