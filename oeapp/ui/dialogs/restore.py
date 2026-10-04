from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from oeapp.services import BackupService, MigrationService
from oeapp.utils import get_logo_pixmap

from .unknown_revision import describe_unknown_revision
from .utils import DateTimeTableWidgetItem

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class RestoreDialog:
    """
    Restore dialog for selecting a backup to restore.

    Args:
        main_window: Main window.

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 700
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize restore dialog.

        Args:
            main_window: Main window.

        """
        #: Main window.
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the restore dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Restore Backup")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Create table widget
        self.backup_table = QTableWidget(self.dialog)
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(
            ["Backup Date/Time", "File Size", "Migration Version", "App Version"]
        )
        self.backup_table.setSortingEnabled(True)
        self.backup_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.backup_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Configure column widths
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.layout.addWidget(self.backup_table)
        self.load_backup_list()
        self._add_button_box()

    def load_backup_list(self) -> None:
        """
        Load the list of available backups.
        """
        backup_service = BackupService()
        backups = backup_service.get_backup_list()

        # Disable sorting while populating
        self.backup_table.setSortingEnabled(False)
        self.backup_table.setRowCount(0)

        if not backups:
            self.main_window.messages.show_information(
                "No backups found.", title="No Backups"
            )
            self.backup_table.setSortingEnabled(True)
            return

        self.backup_table.setRowCount(len(backups))
        for row, backup in enumerate(backups):
            # Backup Date/Time - convert from UTC to local time for display
            backup_time = backup["backup_timestamp"]
            # If timezone-aware (UTC), convert to local time; otherwise assume
            # already local
            if backup_time.tzinfo is not None:
                backup_time_local = backup_time.astimezone()
                # Remove timezone info for display (naive datetime)
                backup_time_local = backup_time_local.replace(tzinfo=None)
            else:
                backup_time_local = backup_time
            time_str = backup_time_local.strftime("%b %d, %Y %I:%M %p")
            time_item = DateTimeTableWidgetItem(time_str, backup_time_local)
            time_item.setData(Qt.ItemDataRole.UserRole, backup["backup_path"])
            self.backup_table.setItem(row, 0, time_item)

            # File Size
            size_str = f"{backup['file_size'] / 1024:.1f} KB"
            size_item = QTableWidgetItem(size_str)
            self.backup_table.setItem(row, 1, size_item)

            # Migration Version
            migration_version = backup.get("migration_version") or "Unknown"
            migration_item = QTableWidgetItem(migration_version)
            self.backup_table.setItem(row, 2, migration_item)

            # App Version
            app_version = backup.get("application_version") or "Unknown"
            app_item = QTableWidgetItem(app_version)
            self.backup_table.setItem(row, 3, app_item)

        # Re-enable sorting after population
        self.backup_table.setSortingEnabled(True)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.restore_backup)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def restore_backup(self) -> None:
        """
        Restore the selected backup, then exit the application.

        A backup whose database revision this build does not know is refused
        before anything is overwritten.
        """
        selected_row = self.backup_table.currentRow()
        if selected_row < 0:
            self.main_window.messages.show_warning("Please select a backup to restore.")
            return
        time_item = self.backup_table.item(selected_row, 0)
        if not time_item:
            return
        backup_path = time_item.data(Qt.ItemDataRole.UserRole)
        if not backup_path:
            return

        backup_service = BackupService()
        metadata = backup_service.read_backup_metadata(Path(backup_path))
        if self._refuse_unknown_revision(metadata):
            return
        if not self._confirm_restore():
            return

        restored = backup_service.restore_backup(Path(backup_path))
        if restored is None:
            self.main_window.messages.show_error("Failed to restore backup.")
            return
        backup_migration = restored.get("migration_version")
        if backup_migration:
            QSettings().setValue("migration/last_working_version", backup_migration)
        self.main_window.messages.show_information(
            "Backup restored successfully. The application will now exit; "
            "start it again to continue.",
            title="Restore Complete",
        )
        self.dialog.accept()
        QApplication.quit()

    def _refuse_unknown_revision(self, metadata: dict[str, Any]) -> bool:
        """
        Refuse a backup whose database revision this build does not know.

        A backup with no recorded revision cannot be judged and is allowed.

        Args:
            metadata: The backup's sidecar metadata

        Returns:
            True if the restore was refused

        """
        revision = metadata.get("migration_version")
        if not revision or MigrationService().is_known_revision(revision):
            return False
        self.main_window.messages.show_warning(
            describe_unknown_revision(revision, metadata.get("application_version")),
            title="Cannot Restore Backup",
        )
        return True

    def _confirm_restore(self) -> bool:
        """
        Ask the user to confirm the restore.

        Returns:
            True if the user chose Yes

        """
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Restore",
            "This will replace your current database with the selected backup.\n"
            "A backup of your current database will be created first, and the "
            "application will exit afterwards.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self.dialog,
        )
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def execute(self) -> None:
        """
        Execute the restore dialog.
        """
        self.build()
        self.dialog.exec()
