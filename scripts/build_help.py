#!/usr/bin/env python3
"""Build QtHelp artifacts from markdown topic sources."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

import markdown
from oeapp.help.topics import HELP_TOPICS

#: Path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
#: Path to the topics directory
TOPICS_DIR = PROJECT_ROOT / "oeapp" / "help" / "topics"
#: Path to the assets directory
ASSETS_DIR = PROJECT_ROOT / "oeapp" / "help" / "assets"
#: Path to the qhp file
QHP_PATH = ASSETS_DIR / "aenglisc_toolkit_help.qhp"
#: Path to the qhcp file
QHCP_PATH = ASSETS_DIR / "aenglisc_toolkit_help.qhcp"
#: Path to the qch file
QCH_PATH = ASSETS_DIR / "aenglisc_toolkit_help.qch"
#: Path to the qhc file
QHC_PATH = ASSETS_DIR / "aenglisc_toolkit_help.qhc"
#: Namespace for the help system
HELP_NAMESPACE = "org.placodermi.aenglisc_toolkit"
#: Virtual folder for the help system
HELP_VIRTUAL_FOLDER = "doc"
#: Filter name for the help system
HELP_FILTER_NAME = "Aenglisc Toolkit"
#: Filter attribute for the help system
HELP_FILTER_ATTRIBUTE = "aenglisc"
#: HTML page used as the authored help entrypoint.
DEFAULT_HOME_PAGE = "start-here.html"


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.

    Returns:
        argparse.Namespace: The parsed arguments.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    #: Skip the qhelpgenerator step
    parser.add_argument(
        "--skip-generator",
        action="store_true",
        help="Only render HTML and project files (.qhp/.qhcp), skip qhelpgenerator.",
    )
    parser.add_argument(
        "--qhelpgenerator",
        type=Path,
        default=None,
        help="Explicit path to qhelpgenerator.",
    )
    return parser.parse_args()


def main() -> None:
    """Build HTML pages, QtHelp project files, and binary artifacts."""
    args = parse_args()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    #: List of topic titles
    topic_titles: list[str] = []
    #: List of topic HTML files
    topic_html_files: list[str] = []

    for topic in HELP_TOPICS:
        markdown_path = TOPICS_DIR / topic.markdown_file
        if not markdown_path.exists():
            msg = f"Missing help topic: {markdown_path}"
            raise FileNotFoundError(msg)

        source = markdown_path.read_text(encoding="utf-8")
        title = first_heading(source) or topic.title
        body_html = markdown.markdown(
            source,
            extensions=["tables", "fenced_code", "codehilite"],
        )
        rendered_page = render_html_page(title=title, body_html=body_html)

        output_path = ASSETS_DIR / topic.html_file
        output_path.write_text(rendered_page, encoding="utf-8")
        topic_titles.append(topic.title)
        topic_html_files.append(topic.html_file)

    if DEFAULT_HOME_PAGE not in topic_html_files:
        msg = (
            "Default home page is missing from help topics: "
            f"{DEFAULT_HOME_PAGE}"
        )
        raise ValueError(msg)

    index_html = render_index_page(home_page=DEFAULT_HOME_PAGE)
    (ASSETS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    QHP_PATH.write_text(build_qhp(topic_titles, topic_html_files), encoding="utf-8")
    QHCP_PATH.write_text(build_qhcp(), encoding="utf-8")

    if args.skip_generator:
        print("Rendered HTML and QtHelp project files (generator skipped).")
        return

    qhelpgenerator = resolve_qhelpgenerator(args.qhelpgenerator)
    run_generator(qhelpgenerator)
    print(f"QtHelp build complete: {QCH_PATH} and {QHC_PATH}")


def first_heading(markdown_text: str) -> str | None:
    """Extract the first markdown H1 heading."""
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def render_html_page(*, title: str, body_html: str) -> str:
    """Render a help topic page with shared CSS."""
    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{escape(title)}</title>
          <style>
            body {{
              margin: 0 auto;
              max-width: 960px;
              padding: 1.2rem 1.4rem 2.2rem;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              line-height: 1.6;
            }}
            h1 {{
              border-bottom: 1px solid;
              padding-bottom: 0.3rem;
            }}
            table {{
              border-collapse: collapse;
              width: 100%;
              margin: 1rem 0;
            }}
            th, td {{
              border: 1px solid;
              padding-top: 8px;
              padding-right: 8px;
              padding-bottom: 8px;
              padding-left: 8px;
              text-align: left;
              vertical-align: top;
            }}
            th {{
              font-weight: 600;
            }}
            code {{
              border-radius: 4px;
              padding: 0.1rem 0.3rem;
            }}
            pre {{
              border-radius: 6px;
              overflow-x: auto;
              padding: 0.75rem;
            }}
          </style>
        </head>
        <body>
          {body_html}
        </body>
        </html>
        """
    )


def render_index_page(home_page: str) -> str:
    """Render top-level index page as redirect to the authored home page."""
    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta http-equiv="refresh" content="0; url={escape(home_page)}">
          <title>Aenglisc Toolkit Help</title>
        </head>
        <body>
          <p>Redirecting to <a href="{escape(home_page)}">{escape(home_page)}</a>...</p>
        </body>
        </html>
        """
    )


def build_qhp(topic_titles: list[str], topic_html_files: list[str]) -> str:
    """Build the QtHelp project file content."""
    topic_sections = "\n".join(
        f'            <section title="{escape(title)}" ref="{escape(html_file)}" />'
        for title, html_file in zip(topic_titles, topic_html_files, strict=True)
    )
    topic_keywords = "\n".join(
        f'        <keyword name="{escape(title)}" '
        f'id="{escape(keyword_id(title))}" '
        f'ref="{escape(html_file)}" />'
        for title, html_file in zip(topic_titles, topic_html_files, strict=True)
    )
    topic_files = "\n".join(
        f"        <file>{escape(html_file)}</file>" for html_file in topic_html_files
    )
    return textwrap.dedent(
        f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <QtHelpProject version="1.0">
              <namespace>{HELP_NAMESPACE}</namespace>
              <virtualFolder>{HELP_VIRTUAL_FOLDER}</virtualFolder>
              <customFilter name="{HELP_FILTER_NAME}">
                <filterAttribute>{HELP_FILTER_ATTRIBUTE}</filterAttribute>
              </customFilter>
              <filterSection>
                <filterAttribute>{HELP_FILTER_ATTRIBUTE}</filterAttribute>
                <toc>
                  <section title="Aenglisc Toolkit Help" ref="{DEFAULT_HOME_PAGE}">
            {topic_sections}
                  </section>
                </toc>
                <keywords>
                  <keyword name="Aenglisc Toolkit Help" id="home" ref="{DEFAULT_HOME_PAGE}" />
            {topic_keywords}
                </keywords>
                <files>
                  <file>index.html</file>
            {topic_files}
                </files>
              </filterSection>
            </QtHelpProject>
            """
    ).lstrip()


def build_qhcp() -> str:
    """Build the QtHelp collection project file content."""
    homepage = f"qthelp://{HELP_NAMESPACE}/{HELP_VIRTUAL_FOLDER}/{DEFAULT_HOME_PAGE}"
    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <QHelpCollectionProject version="1.0">
          <assistant>
            <title>Aenglisc Toolkit Help</title>
            <homePage>{homepage}</homePage>
            <startPage>{homepage}</startPage>
            <currentFilter>{HELP_FILTER_NAME}</currentFilter>
          </assistant>
          <docFiles>
            <generate>
              <file>
                <input>{QHP_PATH.name}</input>
                <output>{QCH_PATH.name}</output>
              </file>
            </generate>
            <register>
              <file>{QCH_PATH.name}</file>
            </register>
          </docFiles>
        </QHelpCollectionProject>
        """
    )


def keyword_id(title: str) -> str:
    """Create a stable QtHelp keyword id from title text."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "topic"


def resolve_qhelpgenerator(explicit_path: Path | None) -> Path:
    """Resolve qhelpgenerator binary path."""
    if explicit_path is not None:
        if explicit_path.exists():
            return explicit_path
        msg = f"qhelpgenerator not found at: {explicit_path}"
        raise FileNotFoundError(msg)

    command_path = shutil.which("qhelpgenerator")
    if command_path:
        return Path(command_path)

    known_locations = (
        Path("/opt/homebrew/Cellar/qt/6.10.2/share/qt/libexec/qhelpgenerator"),
        Path("/opt/homebrew/opt/qt/libexec/qhelpgenerator"),
        Path("/usr/local/opt/qt/libexec/qhelpgenerator"),
    )
    for location in known_locations:
        if location.exists():
            return location

    msg = (
        "qhelpgenerator not found. Install Qt tools or pass --qhelpgenerator "
        "with an explicit binary path."
    )
    raise FileNotFoundError(msg)


def run_generator(qhelpgenerator: Path) -> None:
    """Generate .qch and .qhc files via qhelpgenerator."""
    subprocess.run(
        [str(qhelpgenerator), str(QHP_PATH), "-o", str(QCH_PATH)],
        check=True,
        cwd=ASSETS_DIR,
    )
    subprocess.run(
        [str(qhelpgenerator), str(QHCP_PATH), "-o", str(QHC_PATH)],
        check=True,
        cwd=ASSETS_DIR,
    )


if __name__ == "__main__":
    main()
