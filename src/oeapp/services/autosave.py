"""Autosave service with debounced writes."""

import threading
import time
from typing import Callable, Any
from queue import Queue


class AutosaveService:
    """Service for debounced autosave operations."""

    def __init__(self, save_callback: Callable[[], None], debounce_ms: int = 500):
        """Initialize autosave service.

        Args:
            save_callback: Function to call when saving
            debounce_ms: Debounce delay in milliseconds
        """
        self.save_callback = save_callback
        self.debounce_ms = debounce_ms / 1000.0  # Convert to seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._pending = False

    def trigger(self):
        """Trigger autosave (will be debounced)."""
        with self._lock:
            self._pending = True
            # Cancel existing timer if any
            if self._timer:
                self._timer.cancel()
            # Start new timer
            self._timer = threading.Timer(self.debounce_ms, self._save)
            self._timer.start()

    def _save(self):
        """Execute the save callback."""
        with self._lock:
            if self._pending:
                try:
                    self.save_callback()
                    self._pending = False
                except Exception as e:
                    print(f"Autosave error: {e}")
                    self._pending = False

    def save_now(self):
        """Force immediate save (bypasses debounce)."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._pending = False
        try:
            self.save_callback()
        except Exception as e:
            print(f"Save error: {e}")

    def cancel(self):
        """Cancel pending autosave."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._pending = False
