from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from oeapp.utils import get_logo_pixmap

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
    #: Themes
    THEMES: Final[dict[str, str]] = {
        "dark": "nord",
        "light": "modern_light",
    }

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize settings dialog.
        """
        self.main_window = main_window
        self.settings = QSettings()

    def get_int_value(self, key: str, default: int) -> int:
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

    def get_str_value(self, key: str, default: str) -> str:
        """
        Get the value of a setting key that has a string value.

        Args:
            key: Key for the settings value
            default: Default value for the setting

        Returns:
            Value for the setting

        """
        value = cast("str", self.settings.value(key, default, type=str))
        return value if value is not None else default

    def build(self) -> None:
        """
        Build the settings dialog.
        """
        self.create_layout()
        # Number of backups
        num_backups = self.get_int_value("backup/num_backups", 5)
        self.num_backups_spin = self.add_spin_box(
            "Number of backups to keep:", 1, 100, num_backups
        )
        interval = self.get_int_value("backup/interval_minutes", 720)
        self.interval_spin = self.add_spin_box(
            "Backup interval (minutes):", 1, 1440, interval
        )
        theme = self.get_str_value("theme/name", "nord")
        self.theme_combo = self.add_combo_box("Theme:", ["dark", "light"], theme)
        self.layout.addWidget(self.theme_combo)

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

    def add_combo_box(self, label: str, items: list[str], value: str) -> QComboBox:
        """
        Create a combo box for a settings key that has a string value.

        Args:
            label: Label for the combo box
            items: Items for the combo box
            value: Value for the combo box

        Returns:
            Combo box widget

        """
        combo = QComboBox(self.dialog)
        combo.addItems(items)
        combo.setCurrentText(value)
        self.layout.addWidget(QLabel(label))
        self.layout.addWidget(combo)
        return combo

    def save_settings(self) -> None:
        """
        Save settings to QSettings.
        """
        self.settings.setValue("backup/num_backups", self.num_backups_spin.value())
        self.settings.setValue("backup/interval_minutes", self.interval_spin.value())
        old_theme = self.get_str_value("theme/name", "dark")
        new_theme = self.theme_combo.currentText()
        if old_theme != new_theme:
            QTimer.singleShot(0, self._on_theme_changed)
        self.settings.setValue("theme/name", new_theme)
        self.dialog.accept()

    def _on_theme_changed(self) -> None:
        """
        Handle theme change by opening a confirmation dialog that tells the user
        that the theme will be changed  once they quit and restart the
        application.
        """
        # Confirmation dialog
        # Confirm deletion
        new_theme = self.theme_combo.currentText()
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Theme Change",
            f'You have changed the theme to "{new_theme}". This will '
            "take effect once you quit and restart the application.",
            QMessageBox.StandardButton.Ok,
            self.dialog,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        msg_box.exec()

    def execute(self) -> None:
        """
        Execute the settings dialog.
        """
        self.build()
        self.dialog.exec()

    def get_theme(self) -> str:
        """
        Get the ``qt_themes`` theme name.
        """
        theme = self.get_str_value("theme/name", "dark")
        return self.THEMES[theme]
