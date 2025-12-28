"""Shared pytest fixtures and test helpers for Ænglisc Toolkit tests."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from oeapp.models import *

# Set a temporary database path for tests before any other imports
# This prevents oeapp.db from trying to create a directory in the user's home
if "OE_ANNOTATOR_DB_PATH" not in os.environ:
    _temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _temp_db.close()
    os.environ["OE_ANNOTATOR_DB_PATH"] = _temp_db.name

from oeapp.commands import CommandManager

from PySide6.QtWidgets import QMenuBar, QWidget
import pytest

from oeapp.state import CURRENT_PROJECT_ID, ApplicationState

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

@pytest.fixture
def db_session():
    """Create a temporary database and session for testing."""
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()
    db_path = Path(temp_db.name)

    engine = create_engine_with_path(db_path)
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    state = ApplicationState()
    state.reset()
    state.session = SessionFactory()
    state.session.info["db_path"] = db_path

    yield state.session

    state.session.close()
    engine.dispose()
    os.unlink(temp_db.name)
    state._instance = None


@pytest.fixture
def sample_project(db_session):
    """Create a sample project with default text."""
    project = Project.create(
        session=db_session,
        text="Se cyning",
        name=f"Sample Project {id(db_session)}",
    )
    db_session.commit()
    return project


@pytest.fixture
def sample_sentence(db_session, sample_project):
    """Create a sample sentence with tokens."""
    sentence = Sentence.create(
        session=db_session,
        project_id=sample_project.id,
        display_order=1,
        text_oe="Se cyning",
    )
    db_session.commit()
    return sentence

@pytest.fixture
def mock_main_window():
    """Create a mock main window with session."""

    temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_db.close()
    db_path = Path(temp_db.name)

    engine = create_engine_with_path(db_path)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    session.info["db_path"] = db_path

    main_window = MockMainWindow(session)

    yield main_window

    del main_window
    session.close()
    engine.dispose()
    os.unlink(temp_db.name)

@pytest.fixture
def command_setup(db_session):
    """Set up test database and base objects."""
    state = ApplicationState()
    state.reset()
    state.session = db_session
    # db_session already sets state.session and calls state.reset()

    # Create test project and sentence
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()
    project_id = project.id

    sentence = Sentence.create(
        project_id=project_id, display_order=1, text_oe="Se cyning"
    )
    sentence.text_modern = "The king"
    db_session.commit()

    tokens = Token.list(sentence.id)
    token_id = tokens[0].id

    # Use a command manager with small limit for tests
    command_manager = CommandManager(db_session, max_commands=10)
    state.command_manager = command_manager

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
        self.application_state = ApplicationState()
        self.application_state.reset()
        self.application_state.set_main_window(self)
        self.application_state.session = session
        self.application_state[CURRENT_PROJECT_ID] = None

        self.menuBar = MagicMock()
        self.menuBar.return_value = QMenuBar()

        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.show_information = MagicMock()

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



# Test helper functions (not fixtures, but available for import)


def create_test_project(session, name=None, text=""):
    """
    Helper to create a project with defaults.

    Args:
        session: SQLAlchemy session
        name: Project name (if None, generates unique name)
        text: Old English text (defaults to empty to avoid creating sentences)

    Returns:
        Created Project instance
    """
    if name is None:
        name = f"Test Project {id(session)}"
    project = Project.create(text=text, name=name)
    session.commit()
    return project


def create_test_sentence(
    session, project_id=None, text="Se cyning", display_order=1, is_paragraph_start=False
):
    """
    Helper to create a sentence with defaults.

    Args:
        session: SQLAlchemy session
        project_id: Project ID (if None, creates a new project)
        text: Old English text
        display_order: Display order (will be incremented if conflict exists)
        is_paragraph_start: Whether sentence starts a paragraph

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

    sentence = Sentence.create(
        project_id=project_id,
        display_order=display_order,
        text_oe=text,
        is_paragraph_start=is_paragraph_start,
    )
    session.commit()
    return sentence


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
    session.add(token)
    session.commit()
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

