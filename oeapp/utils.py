"""Utility functions for Ænglisc Toolkit."""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def get_resource_path(relative_path: str) -> Path:
    """
    Get resource path for bundled application or development.

    Args:
        relative_path: Relative path from project root

    Returns:
        Path to resource file

    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


def to_utc_iso(dt: datetime | None) -> str | None:
    """
    Convert datetime to UTC ISO format string.

    Args:
        dt: Datetime object to convert, or None

    Returns:
        ISO format string with UTC timezone, or None

    """
    if dt is None:
        return None
    # If datetime is naive, assume it's already UTC (database stores UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    # Convert to UTC if not already
    dt_utc = dt.astimezone(UTC)
    return dt_utc.isoformat()


def from_utc_iso(iso_str: str | None) -> datetime | None:
    """
    Parse UTC ISO format string to datetime.

    Args:
        iso_str: ISO format string, or None

    Returns:
        Naive datetime object (UTC), or None

    """
    if iso_str is None:
        return None
    dt = datetime.fromisoformat(iso_str)
    # Ensure it's in UTC
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    # Return naive datetime (SQLite doesn't handle timezone-aware datetimes well)
    return dt.replace(tzinfo=None)


def get_logo_pixmap(size: int = 75) -> QPixmap | None:
    """
    Get the application logo as a QPixmap at the specified size.

    Args:
        size: Size of the pixmap in pixels (default: 75)

    Returns:
        QPixmap of the logo at the specified size, or None if logo not found

    """
    logo_path = get_resource_path("assets/logo.png")
    if not logo_path.exists():
        return None
    pixmap = QPixmap(str(logo_path))
    if pixmap.isNull():
        return None
    # Scale to specified size while maintaining aspect ratio
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def render_svg(svg_data: str, size: int = 16) -> QIcon:
    """
    Render SVG data to a QPixmap at the specified size.

    Args:
        svg_data: SVG data to render
        size: Size of the pixmap in pixels (default: 16)

    Returns:
        QPixmap of the rendered SVG, or None if SVG data is invalid

    """
    renderer = QSvgRenderer()
    renderer.load(svg_data.encode("utf-8"))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def open_bosworth_toller(root_value: str) -> None:
    """
    Open the Bosworth-Toller dictionary search page for the given root value.

    Args:
        root_value: The root value to search for

    """
    # Remove hyphens, en-dashes, and em-dashes
    cleaned_root = re.sub(r"[-–—]", "", root_value)  # noqa: RUF001

    # URL-encode the cleaned root value
    encoded_root = quote(cleaned_root)

    # Construct URL
    url = QUrl(f"https://bosworthtoller.com/search?q={encoded_root}")

    # Open in default browser
    QDesktopServices.openUrl(url)
