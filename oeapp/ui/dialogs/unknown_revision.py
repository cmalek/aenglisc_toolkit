"""Dialog shown when the database revision is unknown to this build."""

from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

if TYPE_CHECKING:
    from oeapp.exc import UnknownDatabaseRevision
    from oeapp.ui.main_window import MainWindow

#: FAQ entry that lists every known database version.
FAQ_URL: Final[str] = (
    "https://aenglisc-toolkit.readthedocs.io/en/latest/overview/faq.html"
    "#database-version-mismatch"
)


def describe_unknown_revision(revision: str, required_app_version: str | None) -> str:
    """
    Explain an unknown database revision to the user.

    Args:
        revision: The database's Alembic revision
        required_app_version: Application version that understands it, or None

    Returns:
        The message text

    """
    if required_app_version:
        return (
            "This database was last used by a newer version of Ænglisc Toolkit "
            f"(database revision {revision}).\n\n"
            f"Install application version {required_app_version} or later, then "
            "start the application again.\n\n"
            "Your data has not been changed."
        )
    return (
        f"Can't determine app version to use with db revision {revision}.\n\n"
        "See the FAQ entry 'Database version mismatch' for the list of known "
        f"versions: {FAQ_URL}\n\n"
        "Your data has not been changed."
    )


class UnknownRevisionDialog:
    """
    Dialog shown at startup when the database revision is unknown.

    Args:
        main_window: Main window instance
        error: The exception describing the revision and the version it needs

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 560
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 240

    def __init__(
        self, main_window: "MainWindow", error: "UnknownDatabaseRevision"
    ) -> None:
        """
        Initialize the instance.

        Args:
            main_window: Main window.
            error: Error.

        """
        #: Main window.
        self.main_window = main_window
        #: Error.
        self.error = error

    def build(self) -> None:
        """
        Build the dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Database Version Mismatch")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        layout = QVBoxLayout(self.dialog)
        #: Message label.
        self.message_label = QLabel(
            describe_unknown_revision(
                self.error.revision, self.error.required_app_version
            )
        )
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        exit_button = QPushButton("Exit Application")
        exit_button.clicked.connect(self.dialog.accept)
        layout.addWidget(exit_button)

    def execute(self) -> None:
        """
        Execute the dialog.
        """
        self.build()
        self.dialog.exec()
