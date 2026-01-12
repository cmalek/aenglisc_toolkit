"""Log viewer dialog for Ænglisc Toolkit."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Literal, cast

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from oeapp.services.logs import get_log_file_path

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogTableModel(QAbstractTableModel):
    """Table model for displaying log entries."""

    # A list of the column names.
    COLUMNS: Final[list[str]] = ["Timestamp", "Level", "Message"]
    # A dictionary of the column names to their indexes.
    COLUMN_INDEXES: Final[dict[str, int]] = {
        val: index for index, val in enumerate(COLUMNS)
    }
    # A dictionary of the log levels to their integer values.
    LEVEL_MAP: Final[dict[str, int]] = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._logs: list[dict[str, Any]] = []
        self._display_local_time = False
        self._filter_text = ""
        self._filter_level = "INFO"
        self._all_logs: list[dict[str, Any]] = []
        self._max_lines = 1000

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        """
        Get the number of rows in the model.

        Args:
            parent: The parent index.

        """
        if parent is not None and parent.isValid():
            return 0
        return len(self._logs)

    def columnCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        """
        Get the number of columns in the model.

        Args:
            parent: The parent index.

        """
        if parent is not None and parent.isValid():
            return 0
        return len(self.COLUMNS)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """
        Get the header data for the given section.  This is used to display the
        column headers in the table view.

        Args:
            section: The section index.
            orientation: The orientation of the header.
            role: The role of the header.

        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.COLUMNS[section]
        return None

    def format_message(self, log: dict[str, Any]) -> str:
        """Format the log message with extra key-value pairs."""
        event = str(log.get("event", ""))
        extra_parts = []
        for key, value in log.items():
            if key not in ("event", "level", "timestamp"):
                extra_parts.append(f"{key}={value}")

        if extra_parts:
            return f"{event} {' '.join(extra_parts)}"
        return event

    def data(  # noqa: PLR0911
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._logs)):
            return None

        log = self._logs[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == self.COLUMN_INDEXES["Timestamp"]:  # Timestamp
                ts_str = log.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts_str)
                    if self._display_local_time:
                        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    return ts_str
            elif column == self.COLUMN_INDEXES["Level"]:  # Level
                return log.get("level", "").upper()
            elif column == self.COLUMN_INDEXES["Message"]:  # Message
                return self.format_message(log)

        return None

    def set_logs(self, logs: list[dict[str, Any]]) -> None:
        """
        Set the complete list of log lines and apply filters.

        Args:
            logs: The new list of log lines.

        """
        self._all_logs = logs
        self._apply_filters()

    def add_log(self, log: dict[str, Any]) -> None:
        """
        Add a one log line and apply filters, maintaining 1000 line limit.

        ``log`` is a dictionary with the following keys:

        - timestamp: The timestamp of the log line.
        - level: The log level of the log line.
        - event: The message text of the log line.
        - any other keys will be appended to the message.

        Args:
            log: The new log line.

        """
        self.add_logs([log])

    def add_logs(self, logs: list[dict[str, Any]]) -> None:
        """
        Add multiple log lines and apply filters, maintaining 1000 line limit.

        Args:
            logs: The new log lines.

        """
        if not logs:
            return

        self._all_logs.extend(logs)
        if len(self._all_logs) > self._max_lines:
            self._all_logs = self._all_logs[-self._max_lines :]
        self._apply_filters()

    def set_display_local_time(self, local: bool) -> None:  # noqa: FBT001
        """
        Set the display local time flag.  This toggles the display of the
        timestamp from UTC to local time and vice versa.  Default is False
        (UTC).

        Args:
            local: The new display local time flag.

        """
        self._display_local_time = local
        if self._logs:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._logs) - 1, len(self.COLUMNS) - 1),
            )

    def set_filter_text(self, text: str) -> None:
        """
        Set the filter text.  This filters the logs by the message text.  If the
        text is empty, all logs are displayed.

        Args:
            text: The new filter text.

        """
        self._filter_text = text.lower()
        self._apply_filters()

    def set_filter_level(self, level: LogLevel) -> None:
        """
        Set the filter level.  This filters the logs by log level.  If the level
        is empty, all logs are displayed.

        Valid levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.

        Args:
            level: The new filter level.

        """
        self._filter_level = level.upper()
        self._apply_filters()

    def _apply_filters(self) -> None:
        """
        Apply the filters to the logs and update the model.

        This will reset the model and display the logs that match the filters.

        The filters are:
        - Text: The message text.
        - Level: The log level.

        Args:
            None

        """
        self.beginResetModel()
        min_level_val = self.LEVEL_MAP.get(self._filter_level, 0)

        self._logs = []
        # Display in reverse chronological order
        for log in reversed(self._all_logs):
            level = log.get("level", "").upper()
            level_val = self.LEVEL_MAP.get(level, 0)
            message = self.format_message(log).lower()

            if level_val >= min_level_val and (
                not self._filter_text or self._filter_text in message
            ):
                self._logs.append(log)

            if len(self._logs) >= self._max_lines:
                break
        self.endResetModel()

    def get_log_at(self, row: int) -> dict[str, Any]:
        """
        Get the log line at the given row.

        Args:
            row: The row index.

        Returns:
            The log at the given row.

        """
        if 0 <= row < len(self._logs):
            return self._logs[row]
        return {}


class LogViewerDialog(QDialog):
    """
    Non-modal dialog for viewing application logs.

    Args:
        parent: The parent widget.

    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Application Logs")
        self.resize(800, 600)
        self.setModal(False)

        self._log_file: Path = get_log_file_path()
        self._last_position: int = 0

        self.build()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_logs)
        self._timer.start(2000)  # Check every 2 seconds

        self.load_initial_logs()

    def build(self) -> None:
        """
        Build the UI for the log viewer dialog.

        This will create the layout and add the widgets to the dialog.
        """
        layout = QVBoxLayout(self)

        # Filters row
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search messages...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.search_input)

        filter_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.level_combo)

        layout.addLayout(filter_layout)

        # Options row
        options_layout = QHBoxLayout()

        self.live_btn = QPushButton("Live: ON")
        self.live_btn.setCheckable(True)
        self.live_btn.setChecked(True)
        self.live_btn.toggled.connect(self.on_live_toggled)
        options_layout.addWidget(self.live_btn)

        self.local_time_btn = QPushButton("Local Time: OFF")
        self.local_time_btn.setCheckable(True)
        self.local_time_btn.toggled.connect(self.on_local_time_toggled)
        options_layout.addWidget(self.local_time_btn)

        options_layout.addStretch()

        self.export_btn = QPushButton("Export...")
        self.export_btn.clicked.connect(self.on_export_clicked)
        options_layout.addWidget(self.export_btn)

        layout.addLayout(options_layout)

        # Log table
        self.table_view = QTableView()
        self.model = LogTableModel(self)
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setWordWrap(True)
        layout.addWidget(self.table_view)

        # Initial column widths
        self.table_view.setColumnWidth(0, 150)
        self.table_view.setColumnWidth(1, 80)

    def load_initial_logs(self) -> None:
        """
        Load the initial logs from the log file.

        This will load the last 1000 logs from the log file.
        """
        if not self._log_file.exists():
            return

        logs = []
        try:
            with self._log_file.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            self._last_position = self._log_file.stat().st_size
        except OSError:
            return

        # Limit to last 1000 logs
        self.model.set_logs(logs[-1000:])

    def update_logs(self) -> None:
        """
        Update the logs from the log file.  This will only update the logs if
        the "Live" toggle is enabled and the log file exists.

        This will read the log file and add the new logs to the model.
        """
        if not self.live_btn.isChecked() or not self._log_file.exists():
            return

        current_size = self._log_file.stat().st_size
        if current_size <= self._last_position:
            if current_size < self._last_position:
                # File was likely rotated or truncated, reset
                self._last_position = 0
                self.load_initial_logs()
            return

        new_logs = []
        try:
            with self._log_file.open(encoding="utf-8") as f:
                f.seek(self._last_position)
                for line in f:
                    try:
                        new_logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                self._last_position = f.tell()

            if new_logs:
                self.model.add_logs(new_logs)
        except OSError:
            pass

    def _write_log_line(self, f: Any, log: dict[str, Any]) -> None:
        """
        Write a log line to the file.

        Args:
            f: The file object.
            log: The log line.

        """
        ts = log.get("timestamp", "")
        level = log.get("level", "").upper()
        message = self.model.format_message(log)
        f.write(f"[{ts}] {level:8} {message}\n")

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def on_filter_changed(self) -> None:
        """
        Handle the filter text and level changes.

        This will update the model with the new filter text and level.

        """
        self.model.set_filter_text(self.search_input.text())
        self.model.set_filter_level(
            cast("LogLevel", self.level_combo.currentText().upper())
        )

    def on_live_toggled(self, checked: bool) -> None:  # noqa: FBT001
        """
        Handle the "Live" toggle.

        This will start or stop the live update of the logs.

        Args:
            checked: The new live toggle state.

        """
        if checked:
            self.live_btn.setText("Live: ON")
            self.update_logs()
        else:
            self.live_btn.setText("Live: OFF")

    def on_local_time_toggled(self, checked: bool) -> None:  # noqa: FBT001
        """
        Handle the "Local Time" toggle.

        This will toggle the display of the timestamp from UTC to local time and
        vice versa.

        Args:
            checked: The new local time toggle state.

        """
        if checked:
            self.local_time_btn.setText("Local Time: ON")
        else:
            self.local_time_btn.setText("Local Time: OFF")
        self.model.set_display_local_time(checked)

    def on_export_clicked(self) -> None:
        selection = self.table_view.selectionModel().selectedRows()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            "oe_annotator_logs.txt",
            "Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return

        _file_path = Path(file_path)

        try:
            with _file_path.open(mode="w", encoding="utf-8") as f:
                if selection:
                    # Export selected rows
                    # Sort by row index to maintain the order shown in UI (which
                    # is reverse chronological)
                    rows = sorted([idx.row() for idx in selection])
                    for row in rows:
                        log = self.model.get_log_at(row)
                        self._write_log_line(f, log)
                else:
                    # Export all visible logs
                    for row in range(self.model.rowCount()):
                        log = self.model.get_log_at(row)
                        self._write_log_line(f, log)
        except OSError as e:
            app = QApplication.instance()
            if app and hasattr(app, "main_window"):
                app.main_window.messages.show_error(f"Failed to export logs: {e!s}")
