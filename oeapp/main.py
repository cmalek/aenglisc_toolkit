"""Main entry point for Ænglisc Toolkit application."""

# Set process name early on macOS (before any Qt imports)
# This ensures the menu bar shows the correct app name in development mode
import platform
import sys

if platform.system() == "Darwin":
    # Try to set process name before any other imports
    try:
        import setproctitle

        setproctitle.setproctitle("Ænglisc Toolkit")
    except ImportError:
        # Fallback: manipulate sys.argv[0] which sometimes helps
        # This doesn't always work, but it's worth trying
        if sys.argv and len(sys.argv) > 0:
            sys.argv[0] = "Ænglisc Toolkit"

from oeapp.ui.application import create_application


def main():
    """
    Run the Ænglisc Toolkit application.
    """
    app = create_application()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
