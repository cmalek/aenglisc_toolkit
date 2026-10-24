from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

if TYPE_CHECKING:
    from oeapp.models.project import Project
    from oeapp.ui.main_window import MainWindow


class ImportProjectDialog:
    """
    Dialog shown after importing a project.

    Args:
        main_window: Main window instance
        project: The imported project
        was_renamed: Whether the project name was changed due to collision

    Keyword Args:
        ambiguous_spellings: Saved spellings that share one partial spelling.
            Each item is already joined, for example ``ðæt / þæt``.

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 400
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 200

    def __init__(
        self,
        main_window: "MainWindow",
        project: "Project",
        was_renamed: bool,
        *,
        ambiguous_spellings: list[str] | None = None,
    ) -> None:
        """
        Initialize import project dialog.

        Args:
            main_window: Main window instance
            project: The imported project
            was_renamed: Whether the project name was changed

        Keyword Args:
            ambiguous_spellings: Saved spellings that share one partial spelling.

        """
        #: Main window.
        self.main_window = main_window
        #: Project.
        self.project = project
        #: Was renamed.
        self.was_renamed = was_renamed
        #: Spellings imported together that Apply will not use.
        self.ambiguous_spellings = list(ambiguous_spellings or [])
        #: Should open.
        self.should_open = False

    def build(self) -> None:
        """
        Build the import project dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Import Successful")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        message_label = QLabel(self._message())
        message_label.setWordWrap(True)
        self.layout.addWidget(message_label)

        # Button box
        self.button_box = QDialogButtonBox(self.dialog)
        open_button = self.button_box.addButton(
            "Open Project", QDialogButtonBox.ButtonRole.AcceptRole
        )
        close_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Close)
        open_button.clicked.connect(self._open_project)
        close_button.clicked.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def _message(self) -> str:
        """
        Build the import result text.

        Returns:
            Dialog body.

        """
        message = f"Project '{self.project.name}' imported successfully."
        if self.was_renamed:
            message += (
                "\n\nThe project name was changed to avoid a collision with an "
                "existing project."
            )
        if not self.ambiguous_spellings:
            return message
        named = "\n".join(f"- {spelling}" for spelling in self.ambiguous_spellings)
        return (
            f"{message}\n\n"
            "These remembered annotations share a spelling and were kept as "
            f"separate entries:\n{named}\n\n"
            "Delete one of each pair. Apply Remembered Annotations will not "
            "use that spelling until you do."
        )

    def _open_project(self) -> None:
        """Handle open project button click."""
        self.should_open = True
        self.dialog.accept()

    def execute(self) -> bool:
        """
        Execute the import project dialog.

        Returns:
            True if user chose to open project, False otherwise

        """
        self.build()
        self.dialog.exec()
        return self.should_open
