"""Shared help topic metadata."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class HelpTopic:
    """Metadata for a single help topic."""

    #: Topic title
    title: str
    #: Markdown file
    markdown_file: str
    #: HTML file
    html_file: str


#: List of help topics. The tuple is ("Title", "Markdown file", "HTML file").
HELP_TOPICS: Final[tuple[HelpTopic, ...]] = (
    HelpTopic("Start Here", "start-here.md", "start-here.html"),
    HelpTopic("Settings", "settings.md", "settings.html"),
    HelpTopic("Keybindings", "keybindings.md", "keybindings.html"),
    HelpTopic("Annotation Guide", "annotation-guide.md", "annotation-guide.html"),
    HelpTopic("Idioms Guide", "idioms-guide.md", "idioms-guide.html"),
    HelpTopic(
        "Incremental Annotation",
        "incremental-annotation.md",
        "incremental-annotation.html",
    ),
    HelpTopic("Notes Guide", "notes-guide.md", "notes-guide.html"),
    HelpTopic("Search Guide", "search-guide.md", "search-guide.html"),
    HelpTopic(
        "Full Translation Window",
        "full-translation-window.md",
        "full-translation-window.html",
    ),
    HelpTopic("Export Formatting", "export-formatting.md", "export-formatting.html"),
    HelpTopic(
        "Project Export/Import",
        "project-export-import.md",
        "project-export-import.html",
    ),
    HelpTopic("Automatic Backups", "automatic-backups.md", "automatic-backups.html"),
    HelpTopic(
        "Morphological Reference",
        "morphological-reference.md",
        "morphological-reference.html",
    ),
    HelpTopic("Troubleshooting", "troubleshooting.md", "troubleshooting.html"),
)

#: Mapping of topic titles to HTML files.
TOPIC_TO_HTML: Final[dict[str, str]] = {
    topic.title: topic.html_file for topic in HELP_TOPICS
}

#: Default topic title when first opening the help center
DEFAULT_TOPIC_TITLE: Final[str] = "Start Here"
#: Default HTML page when first opening the help center
DEFAULT_HTML_PAGE: Final[str] = "start-here.html"
