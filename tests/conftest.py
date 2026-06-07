"""Shared pytest fixtures and test helpers for Ænglisc Toolkit tests."""

import os
import sys

# Set QT_QPA_PLATFORM to offscreen for headless environments (like tests)
# This must be done BEFORE any PySide6 modules are imported
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Set a temporary database path for tests before any other imports
# This prevents oeapp.db from trying to create a directory in the user's home
if "OE_ANNOTATOR_DB_PATH" not in os.environ:
    _temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _temp_db.close()
    os.environ["OE_ANNOTATOR_DB_PATH"] = _temp_db.name

# Set a temporary app data path for tests
if "OE_ANNOTATOR_DATA_PATH" not in os.environ:
    import tempfile
    os.environ["OE_ANNOTATOR_DATA_PATH"] = tempfile.mkdtemp()

from oeapp.services.logs import configure_logging
configure_logging()

from oeapp.models import *

from oeapp.commands import CommandManager

from PySide6.QtWidgets import QMenuBar, QWidget
import pytest

from oeapp.db import clear_runtime_session, set_runtime_session
from oeapp.state import AppContext

# CRITICAL: Create QApplication BEFORE any Qt imports to prevent segmentation faults
# This must happen at module import time, before any test modules are imported
# Qt requires QApplication to exist before any Qt widgets can be used
try:
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists before any test imports
    # This prevents segfaults when test modules import Qt widgets during collection
    if QApplication.instance() is None:
        # Create QApplication with minimal args to avoid requiring display
        # Use sys.argv if available, otherwise empty list
        import sys
        app_args = sys.argv if hasattr(sys, 'argv') else []
        _ = QApplication(app_args)
except (ImportError, RuntimeError):
    # If Qt is not available or can't be initialized, that's okay
    # Some tests mock Qt, so we can't require it here
    pass

from sqlalchemy.orm import sessionmaker

from sqlalchemy import select

from oeapp.db import Base, create_engine_with_path
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token
from oeapp.services.migration import MigrationService


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing PySide6 widgets."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def disable_autosave_by_default(request, monkeypatch):
    """
    Disable autosave triggers unless a test explicitly opts in.

    Opt-in tests should use ``@pytest.mark.enable_autosave``.
    """
    if request.node.get_closest_marker("enable_autosave"):
        return

    from oeapp.services.autosave import AutosaveService

    def _disabled_trigger(self):
        self.cancel()

    monkeypatch.setattr(AutosaveService, "trigger", _disabled_trigger)


@pytest.fixture
def db_session():
    """Create a temporary database and session for testing."""
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()
    db_path = Path(temp_db.name)

    engine = create_engine_with_path(db_path)
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionFactory()
    set_runtime_session(session)
    session.info["db_path"] = db_path

    yield session

    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            for widget in app.topLevelWidgets():
                try:
                    widget.close()
                    widget.deleteLater()
                except RuntimeError:
                    continue
            app.processEvents()
    except RuntimeError:
        pass

    session.close()
    engine.dispose()
    os.unlink(temp_db.name)
    clear_runtime_session(close=False)


@pytest.fixture
def sample_project(db_session):
    """Create a sample project with default text."""
    return Project.create(
        text="Se cyning",
        name=f"Sample Project {id(db_session)}",
    )


@pytest.fixture
def sample_sentence(db_session, sample_project):
    """Get the first sentence of the sample project."""
    if sample_project.sentences:
        return sample_project.sentences[0]
    return Sentence.create(
        project_id=sample_project.id,
        display_order=1,
        text_oe="Se cyning",
    )

@pytest.fixture
def mock_main_window(db_session):
    """Create a mock main window with session."""
    main_window = MockMainWindow(db_session)
    return main_window

@pytest.fixture
def command_setup(db_session):
    """Set up test database and base objects."""
    # Create test project and sentence
    project = Project(name="Test Project")
    project.save()
    project_id = project.id

    sentence = Sentence.create(
        project_id=project_id, display_order=1, text_oe="Se cyning"
    )
    sentence.text_modern = "The king"
    sentence.save()

    tokens = Token.list(sentence.id)
    token_id = tokens[0].id

    # Use a command manager with small limit for tests
    command_manager = CommandManager(db_session, max_commands=10)
    return {
        "session": db_session,
        "project_id": project_id,
        "sentence_id": sentence.id,
        "token_id": token_id,
        "command_manager": command_manager,
    }


@pytest.fixture
def project_and_sentence(db_session):
    """Create a test project and sentence."""
    # Create project
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()

    # Create sentence
    sentence = Sentence.create(
        project_id=project.id,
        display_order=1,
        text_oe="Se cyning"
    )

    return project.id, sentence.id

# Test helper classes

class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self, session):
        super().__init__()
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.app_context = AppContext(session=session)
        self.app_context.set_main_window(self)
        self.app_context.current_project_id = None

        self.menuBar = MagicMock()
        self.menuBar.return_value = QMenuBar()

        self.token_details_sidebar = MagicMock()
        self.sentence_cards = []
        self.clear_selected_tokens = MagicMock()
        self.project_ui = _MockProjectUI()

        self.messages = MagicMock()
        self.messages.show_information = MagicMock()
        self.messages.show_warning = MagicMock()
        self.messages.show_error = MagicMock()
        self.messages.show_information = MagicMock()

        self.backup_service = MagicMock()
        self.action_service = MagicMock()
        self.backup_service = MagicMock()
        self.save_project = MagicMock()
        self.export_project_docx = MagicMock()
        self.new_project = MagicMock()
        self.open_project = MagicMock()
        self.delete_project = MagicMock()
        self.append_text = MagicMock()
        self.backup_now = MagicMock()
        self.restore_backup = MagicMock()
        self.view_backups = MagicMock()
        self.show_settings = MagicMock()
        self.show_help = MagicMock()
        self.show_restore_dialog = MagicMock()
        self.show_backups_dialog = MagicMock()
        self.import_project_json = MagicMock()
        self.export_project_json = MagicMock()
        self.show_settings_dialog = MagicMock()
        self.load_project = MagicMock()
        self.reload_project = MagicMock()
        self.refresh_project = MagicMock()
        self.setWindowTitle = MagicMock()


class _MockProjectUI:
    """Minimal workspace selection holder for tests."""

    def __init__(self) -> None:
        self._selected_sentence_card = None

    def get_selected_sentence_card(self):
        """Return selected sentence card for action tests."""
        return self._selected_sentence_card

    def set_selected_sentence_card(self, card) -> None:
        """Store selected sentence card for action tests."""
        self._selected_sentence_card = card

    def clear_selected_sentence_card(self) -> None:
        """Clear the selected sentence card."""
        self._selected_sentence_card = None



# Test helper functions (not fixtures, but available for import)


def create_test_project(
    session, name=None, text="", source=None, translator=None, notes=None
):
    """
    Helper to create a project with defaults.

    Args:
        session: SQLAlchemy session
        name: Project name (if None, generates unique name)
        text: Old English text (defaults to empty to avoid creating sentences)
        source: Bibliographic source
        translator: Translator name
        notes: Project notes

    Returns:
        Created Project instance
    """
    if name is None:
        name = f"Test Project {id(session)}"
    
    # If text is empty, Project.create won't create any chapters/sections/paragraphs
    # We need to ensure they exist even for empty projects
    project = Project.create(
        text=text, name=name, source=source, translator=translator, notes=notes
    )
    
    if not text:
        from oeapp.models.chapter import Chapter
        from oeapp.models.section import Section
        from oeapp.models.paragraph import Paragraph
        
        chapter = Chapter(project_id=project.id, number=1)
        session.add(chapter)
        session.flush()
        section = Section(chapter_id=chapter.id, number=1)
        session.add(section)
        session.flush()
        paragraph = Paragraph(section_id=section.id, order=1)
        session.add(paragraph)
        session.flush()
        
    return project


def create_test_sentence(
    session, project_id=None, text="Se cyning", display_order=1, paragraph_id=None
):
    """
    Helper to create a sentence with defaults.

    Args:
        session: SQLAlchemy session
        project_id: Project ID (if None, creates a new project)
        text: Old English text
        display_order: Display order (will be incremented if conflict exists)
        paragraph_id: Paragraph ID

    Returns:
        Created Sentence instance
    """
    # If project_id not specified, create a new project
    if project_id is None:
        project = create_test_project(session, name=f"Test Project {id(session)}")
        project_id = project.id

    # Check if a sentence with this display_order already exists
    existing = session.scalar(
        select(Sentence).where(
            Sentence.project_id == project_id,
            Sentence.display_order == display_order
        )
    )
    if existing is not None:
        # Find the next available display_order
        all_sentences = Sentence.list(project_id)
        if all_sentences:
            display_order = max(s.display_order for s in all_sentences) + 1
        else:
            display_order = 1

    # Ensure we have a paragraph if not provided
    if paragraph_id is None:
        from oeapp.models.chapter import Chapter
        from oeapp.models.section import Section
        from oeapp.models.paragraph import Paragraph
        
        project = session.get(Project, project_id)
        if not project.chapters:
            chapter = Chapter(project_id=project_id, number=1)
            session.add(chapter)
            session.flush()
            section = Section(chapter_id=chapter.id, number=1)
            session.add(section)
            session.flush()
            paragraph = Paragraph(section_id=section.id, order=1)
            session.add(paragraph)
            session.flush()
            paragraph_id = paragraph.id
        else:
            paragraph_id = project.chapters[0].sections[0].paragraphs[0].id

    return Sentence.create(
        project_id=project_id,
        display_order=display_order,
        text_oe=text,
        paragraph_id=paragraph_id,
    )


def create_test_token(session, sentence_id, surface="cyning", order_index=0, lemma=None):
    """
    Helper to create a token with defaults.

    Args:
        session: SQLAlchemy session
        sentence_id: Sentence ID
        surface: Token surface form
        order_index: Order index in sentence
        lemma: Optional lemma

    Returns:
        Created Token instance
    """
    token = Token(
        sentence_id=sentence_id,
        order_index=order_index,
        surface=surface,
        lemma=lemma,
    )
    token.save()
    return token


@pytest.fixture
def mock_migration_services():
    """Create mocked migration services for tests that need ProjectImporter."""
    mock_backup = MagicMock()
    mock_engine = MagicMock()
    mock_metadata = MagicMock()

    migration_service = MigrationService(
        backup_service=mock_backup,
        engine=mock_engine,
        migration_metadata_service=mock_metadata
    )

    return migration_service, mock_metadata
