"""Tests for the log viewer dialog."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from oeapp.ui.dialogs.log_viewer import LogTableModel, LogViewerDialog


@pytest.fixture
def log_file(tmp_path):
    """Create a temporary log file for testing."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_path = log_dir / "oe_annotator.log.json"
    
    logs = [
        {"timestamp": "2026-01-01T10:00:00Z", "level": "info", "event": "First log"},
        {"timestamp": "2026-01-01T10:01:00Z", "level": "warning", "event": "Second log", "user": "alice"},
        {"timestamp": "2026-01-01T10:02:00Z", "level": "error", "event": "Third log", "status": 500},
    ]
    
    with open(log_path, "w", encoding="utf-8") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
            
    return log_path


def test_log_table_model():
    """Test the LogTableModel filtering and data retrieval."""
    model = LogTableModel()
    logs = [
        {"timestamp": "2026-01-01T10:00:00Z", "level": "info", "event": "Info message"},
        {"timestamp": "2026-01-01T10:01:00Z", "level": "error", "event": "Error message", "extra": "data"},
    ]
    model.set_logs(logs)
    
    # Check reverse order and formatting
    assert model.rowCount() == 2
    assert model.data(model.index(0, 2)) == "Error message extra=data"
    assert model.data(model.index(1, 2)) == "Info message"
    
    # Test level filtering
    model.set_filter_level("ERROR")
    assert model.rowCount() == 1
    assert model.data(model.index(0, 2)) == "Error message extra=data"
    
    # Test text filtering on extra data
    model.set_filter_level("INFO")
    model.set_filter_text("extra=data")
    assert model.rowCount() == 1
    assert model.data(model.index(0, 2)) == "Error message extra=data"
    
    model.set_filter_text("info")
    assert model.rowCount() == 1
    assert model.data(model.index(0, 2)) == "Info message"


def test_log_viewer_dialog_initial_load(qtbot, log_file, monkeypatch):
    """Test that LogViewerDialog loads initial logs."""
    monkeypatch.setattr("oeapp.ui.dialogs.log_viewer.get_log_file_path", lambda: log_file)
    
    dialog = LogViewerDialog()
    qtbot.addWidget(dialog)
    
    assert dialog.model.rowCount() == 3
    # Check order (reverse chronological) and formatting
    assert dialog.model.data(dialog.model.index(0, 2)) == "Third log status=500"
    assert dialog.model.data(dialog.model.index(1, 2)) == "Second log user=alice"


def test_log_viewer_dialog_filtering(qtbot, log_file, monkeypatch):
    """Test UI filtering controls."""
    monkeypatch.setattr("oeapp.ui.dialogs.log_viewer.get_log_file_path", lambda: log_file)
    
    dialog = LogViewerDialog()
    qtbot.addWidget(dialog)
    
    # Test text filter
    dialog.search_input.setText("Second")
    assert dialog.model.rowCount() == 1
    assert dialog.model.data(dialog.model.index(0, 2)) == "Second log user=alice"
    
    # Test level filter
    dialog.search_input.setText("")
    dialog.level_combo.setCurrentText("ERROR")
    assert dialog.model.rowCount() == 1
    assert dialog.model.data(dialog.model.index(0, 2)) == "Third log status=500"


def test_log_viewer_export(qtbot, log_file, tmp_path, monkeypatch):
    """Test log export functionality."""
    monkeypatch.setattr("oeapp.ui.dialogs.log_viewer.get_log_file_path", lambda: log_file)
    
    dialog = LogViewerDialog()
    qtbot.addWidget(dialog)
    
    export_path = tmp_path / "exported_logs.txt"
    
    # Mock QFileDialog to return our export path
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(export_path), "Text Files (*.txt)")
    )
    
    dialog.on_export_clicked()
    
    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "First log" in content
    assert "Second log user=alice" in content
    assert "Third log status=500" in content


def test_log_viewer_local_time(qtbot, log_file, monkeypatch):
    """Test local time toggle and dataChanged signal."""
    monkeypatch.setattr("oeapp.ui.dialogs.log_viewer.get_log_file_path", lambda: log_file)
    
    dialog = LogViewerDialog()
    qtbot.addWidget(dialog)
    
    # Check initial UTC display (YYYY-MM-DD HH:MM:SS)
    utc_time = dialog.model.data(dialog.model.index(0, 0))
    assert "2026-01-01 10:02:00" in utc_time
    
    # Toggle local time
    # This triggers dataChanged.emit with the fix
    dialog.local_time_btn.click()
    assert dialog.model._display_local_time is True
    
    # Data should still be there (though formatting might differ based on system tz)
    local_time = dialog.model.data(dialog.model.index(0, 0))
    assert local_time is not None
    assert local_time != ""


def test_log_viewer_live_update(qtbot, log_file, monkeypatch):
    """Test live update with new log lines."""
    monkeypatch.setattr("oeapp.ui.dialogs.log_viewer.get_log_file_path", lambda: log_file)
    
    dialog = LogViewerDialog()
    qtbot.addWidget(dialog)
    
    assert dialog.model.rowCount() == 3
    
    # Append a new log line to the file
    new_log = {"timestamp": "2026-01-01T10:03:00Z", "level": "info", "event": "New log"}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(new_log) + "\n")
        
    # Trigger manual update
    dialog.update_logs()
    
    assert dialog.model.rowCount() == 4
    assert dialog.model.data(dialog.model.index(0, 2)) == "New log"
