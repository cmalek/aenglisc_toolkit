from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from oeapp.exc import AlreadyExists
from oeapp.models.project import Project
from oeapp.state import ApplicationState

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class EditProjectDialog:
    """
    Edit project dialog. This gets opened when the user clicks the "Edit Project..."
    menu item from the Project menu.

    This dialog allows the user to edit the project title, source, translator,
    and notes.

    Args:
        main_window: Main window instance
        project: Project instance to edit
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: "MainWindow", project: Project) -> None:
        """
        Initialize edit project dialog.
        """
        self.main_window = main_window
        self.project = project
        self.state = ApplicationState()

    def build(self) -> None:
        """
        Build the edit project dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Edit Project")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        self._add_title_edit()
        self._add_metadata_fields()
        self.layout.addStretch()
        self._add_button_box()

    def _add_title_edit(self) -> None:
        """Add title edit."""
        self.title_edit = QLineEdit(self.dialog)
        self.title_edit.setText(self.project.name)
        self.layout.addWidget(QLabel("Project Title:"))
        self.layout.addWidget(self.title_edit)

    def _add_metadata_fields(self) -> None:
        """Add metadata fields."""
        self.source_edit = QTextEdit(self.dialog)
        self.source_edit.setPlainText(self.project.source or "")
        self.source_edit.setPlaceholderText("Enter bibliographic source...")
        self.source_edit.setMaximumHeight(100)
        self.layout.addWidget(QLabel("Source:"))
        self.layout.addWidget(self.source_edit)

        self.translator_edit = QLineEdit(self.dialog)
        self.translator_edit.setText(self.project.translator or "")
        self.translator_edit.setPlaceholderText("Enter translator name...")
        self.layout.addWidget(QLabel("Translator:"))
        self.layout.addWidget(self.translator_edit)

        self.notes_edit = QTextEdit(self.dialog)
        self.notes_edit.setPlainText(self.project.notes or "")
        self.notes_edit.setPlaceholderText("Enter project notes...")
        self.notes_edit.setMaximumHeight(100)
        self.layout.addWidget(QLabel("Notes:"))
        self.layout.addWidget(self.notes_edit)

    def _add_button_box(self) -> None:
        """Add button box."""
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_project)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def save_project(self) -> None:
        """Save project changes."""
        title = self.title_edit.text().strip()
        if not title:
            self.state.show_error("Please enter a project title.")
            return

        source = self.source_edit.toPlainText().strip() or None
        translator = self.translator_edit.text().strip() or None
        notes = self.notes_edit.toPlainText().strip() or None

        # Check if title changed and if new title already exists
        if title != self.project.name and Project.exists(title):
            self.state.show_error(f'Project with title "{title}" already exists.')
            return

        try:
            self.project.name = title
            self.project.source = source
            self.project.translator = translator
            self.project.notes = notes
            self.project.save()

            self.main_window.setWindowTitle(f"Ænglisc Toolkit - {self.project.name}")
            self.state.show_message("Project updated")
            self.dialog.accept()
        except Exception as e:
            self.state.show_error(f"Failed to update project: {e!s}")

    def execute(self) -> None:
        """Execute dialog."""
        self.build()
        self.dialog.exec()

