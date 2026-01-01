from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSpinBox, QVBoxLayout

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class SettingsDialog:
    """
    Settings dialog for backup configuration.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 400
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 200

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize settings dialog.
        """
        self.main_window = main_window
        self.settings = QSettings()

    def get_setting_value(self, key: str, default: int) -> int:
        """
        Get the value of a setting key that has an integer value.

        Args:
            key: Key for the settings value
            default: Default value for the setting

        Returns:
            Value for the setting

        """
        value = cast("int", self.settings.value(key, default, type=int))
        return int(value) if value is not None else default

    def build(self) -> None:
        """
        Build the settings dialog.
        """
        self.create_layout()
        # Number of backups
        num_backups = self.get_setting_value("backup/num_backups", 5)
        self.num_backups_spin = self.add_spin_box(
            "Number of backups to keep:", 1, 100, num_backups
        )
        interval = self.get_setting_value("backup/interval_minutes", 720)
        self.interval_spin = self.add_spin_box(
            "Backup interval (minutes):", 1, 1440, interval
        )

        self.button_box = self.add_button_box()

    def create_layout(self) -> None:
        """
        Create a layout for the settings dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Preferences")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

    def add_spin_box(
        self, label: str, minimum: int, maximum: int, value: int
    ) -> QSpinBox:
        """
        Create a spin box for a settings key that has an integer value.

        Args:
            label: Label for the spin box
            key: Key for the settings value
            minimum: Minimum value for the spin box
            maximum: Maximum value for the spin box
            value: Value for the spin box

        Returns:
            Spin box widget

        """
        spin_box = QSpinBox(self.dialog)
        spin_box.setMinimum(minimum)
        spin_box.setMaximum(maximum)
        spin_box.setValue(value)
        self.layout.addWidget(QLabel(label))
        self.layout.addWidget(spin_box)
        return spin_box

    def add_button_box(self) -> QDialogButtonBox:
        """
        Add the button box to the dialog.  The button box will be used to accept
        or cancel the dialog.

        Returns:
            Button box widget

        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)
        return self.button_box

    def save_settings(self) -> None:
        """Save settings to QSettings."""
        self.settings.setValue("backup/num_backups", self.num_backups_spin.value())
        self.settings.setValue("backup/interval_minutes", self.interval_spin.value())
        self.dialog.accept()

    def execute(self) -> None:
        """
        Execute the settings dialog.
        """
        self.build()
        self.dialog.exec()
