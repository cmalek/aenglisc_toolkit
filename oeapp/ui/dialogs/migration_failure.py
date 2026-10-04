import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class MigrationFailureDialog:
    """
    Dialog shown when migration fails during startup.

    Args:
        main_window: Main window instance
        error: The exception that occurred during migration
        backup_app_version: Application version from the backup

    Keyword Args:
        restored: Whether the database was automatically restored
        backup_path: Path of the pre-migration backup
        database_path: Path of the live database

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 700
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(  # noqa: PLR0913
        self,
        main_window: "MainWindow",
        error: Exception,
        backup_app_version: str | None,
        *,
        restored: bool = True,
        backup_path: Path | None = None,
        database_path: Path | None = None,
    ) -> None:
        """
        Initialize the instance.

        Args:
            main_window: Main window.
            error: Error.
            backup_app_version: Backup app version.

        Keyword Args:
            restored: Whether the database was automatically restored.
            backup_path: Path of the pre-migration backup.
            database_path: Path of the live database.

        """
        #: Main window.
        self.main_window = main_window
        #: Error.
        self.error = error
        #: Backup app version.
        self.backup_app_version = backup_app_version
        #: Whether the database was automatically restored.
        self.restored = restored
        #: Path of the pre-migration backup.
        self.backup_path = backup_path
        #: Path of the live database.
        self.database_path = database_path
        #: App context.
        self.app_context = main_window.app_context

    def _message_text(self) -> str:
        """
        Build the explanatory text for the top of the dialog.

        Returns:
            The restored or the restore-failed message

        """
        if self.restored:
            return self._restored_text()
        return self._not_restored_text()

    def _restored_text(self) -> str:
        """
        Build the text for a migration that was rolled back automatically.

        Returns:
            The message, naming the backup's application version when known

        """
        text = (
            "Database migration failed during startup.\n\n"
            "Your database has been automatically restored to the backup created "
            "before the migration attempt.\n\n"
        )
        if self.backup_app_version:
            text += (
                f"To continue working, please downgrade to application version "
                f"{self.backup_app_version}.\n\n"
                f"The restored backup was created with application version "
                f"{self.backup_app_version}."
            )
        return text

    def _not_restored_text(self) -> str:
        """
        Build the text for a migration whose automatic restore also failed.

        Returns:
            The message with the backup and database paths and recovery steps

        """
        text = (
            "Database migration failed during startup, and the automatic "
            "restore also failed. Your database may be partly migrated: do not "
            "use or edit it.\n\n"
            "Your pre-migration backup is safe. It is also listed in the "
            "Restore dialog.\n"
            f"Backup: {self.backup_path or 'unknown'}\n"
            f"Database: {self.database_path or 'unknown'}\n\n"
            "To recover:\n"
            "1. Close the application.\n"
            "2. Make a copy of the backup file.\n"
        )
        step = 3
        if self.backup_app_version:
            text += (
                f"{step}. Install application version {self.backup_app_version}, "
                "which made the backup.\n"
            )
            step += 1
        text += (
            f"{step}. Rename the copy to the database's file name, replacing "
            "the database file, and start the application.\n\n"
            "You can save or copy the stack trace below for a bug report."
        )
        return text

    def build(self) -> None:
        """
        Build the migration failure dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Migration Failed")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Error message
        error_label = QLabel(self._message_text())
        error_label.setWordWrap(True)
        self.layout.addWidget(error_label)

        # Stack trace
        trace_label = QLabel("Stack Trace:")
        self.layout.addWidget(trace_label)

        trace_text = QTextEdit(self.dialog)
        trace_text.setReadOnly(True)
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        trace_text.setPlainText(trace_str)
        trace_text.setMinimumHeight(200)
        self.layout.addWidget(trace_text)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save Stack Trace")
        save_button.clicked.connect(self.save_stack_trace)
        button_layout.addWidget(save_button)

        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_button)

        button_layout.addStretch()

        exit_button = QPushButton("Exit Application")
        exit_button.clicked.connect(self.dialog.accept)
        button_layout.addWidget(exit_button)

        self.layout.addLayout(button_layout)

    def save_stack_trace(self) -> None:
        """Save stack trace to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.dialog,
            "Save Stack Trace",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            # Format stack trace (should not fail)
            trace_str = "".join(
                traceback.format_exception(
                    type(self.error), self.error, self.error.__traceback__
                )
            )
            # Write to file - can fail with file system errors
            try:
                Path(file_path).write_text(trace_str, encoding="utf-8")
            except (OSError, PermissionError) as e:
                self.app_context.show_error(f"Failed to save stack trace: {e}")
                return

            self.app_context.show_information(
                f"Stack trace saved to:\n{file_path}", title="Saved"
            )

    def copy_to_clipboard(self) -> None:
        """Copy stack trace to clipboard."""
        clipboard = QApplication.clipboard()
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        clipboard.setText(trace_str)
        self.app_context.show_message("Stack trace copied to clipboard")

    def execute(self) -> None:
        """
        Execute the migration failure dialog.
        """
        self.build()
        self.dialog.exec()
