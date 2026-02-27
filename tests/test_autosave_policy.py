"""Tests for the suite-level autosave policy."""

import time
from unittest.mock import MagicMock

import pytest

from oeapp.services.autosave import AutosaveService


def test_autosave_disabled_by_default(qapp):
    """Autosave trigger should be disabled unless a test opts in."""
    callback = MagicMock()
    service = AutosaveService(callback, debounce_ms=50)

    service.trigger()
    time.sleep(0.1)
    qapp.processEvents()

    callback.assert_not_called()


@pytest.mark.enable_autosave
def test_autosave_can_be_enabled_per_test(qapp):
    """Opt-in marker should restore real autosave behavior."""
    callback = MagicMock()
    service = AutosaveService(callback, debounce_ms=50)

    service.trigger()
    time.sleep(0.1)
    qapp.processEvents()

    callback.assert_called_once()
