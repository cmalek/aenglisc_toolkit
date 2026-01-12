"""Tests for logging configuration."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import structlog

from oeapp.services.logs import configure_logging, get_log_file_path, get_logger


@pytest.fixture
def temp_log_dir(tmp_path):
    """Fixture for a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    with patch("oeapp.services.logs.get_app_data_path", return_value=tmp_path):
        yield log_dir


def test_logging_configuration(temp_log_dir):
    """Test that logging is configured correctly."""
    configure_logging()
    
    logger = get_logger("test_logger")
    logger.info("test message", key="value")
    
    # Flush handlers to ensure log is written
    for handler in logging.getLogger().handlers:
        handler.flush()
    
    log_file = get_log_file_path()
    assert log_file.exists()
    
    with open(log_file, "r", encoding="utf-8") as f:
        log_entry = json.loads(f.read().strip())
        
    assert log_entry["event"] == "test message"
    assert log_entry["level"] == "info"
    assert log_entry["key"] == "value"
    assert "timestamp" in log_entry


def test_log_rotation(temp_log_dir):
    """Test that TimedRotatingFileHandler is set up."""
    configure_logging()
    
    root_logger = logging.getLogger()
    handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
    
    assert len(handlers) > 0
    handler = handlers[0]
    assert handler.when == "D"
    # TimedRotatingFileHandler converts interval to seconds internally for certain 'when' values
    assert handler.interval == 21 * 24 * 60 * 60
    assert handler.backupCount == 5
