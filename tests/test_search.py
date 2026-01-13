import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QComboBox, QPushButton, QLabel
from oeapp.ui.main_window import MainWindow
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.state import ApplicationState

@pytest.fixture
def window(qtbot, db_session):
    """Create a MainWindow instance for testing."""
    win = MainWindow()
    # OVERRIDE the session that MainWindow just created/reset
    win.application_state.session = db_session
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win

@pytest.fixture
def search_project(db_session, window):
    """Create a project with several sentences for testing search."""
    # Ensure we use the SAME session that window is using
    session = window.application_state.session
    
    project = Project(name="Search Test Project")
    session.add(project)
    session.commit()
    
    s1 = Sentence.create(project_id=project.id, text_oe="Se cyning rad.", display_order=1, commit=False)
    s1.text_modern = "The king rode."
    session.add(s1)
    
    s2 = Sentence.create(project_id=project.id, text_oe="Þæt scip seglode.", display_order=2, commit=False)
    s2.text_modern = "The ship sailed."
    session.add(s2)
    
    s3 = Sentence.create(project_id=project.id, text_oe="Se guma sang.", display_order=3, commit=False)
    s3.text_modern = "The man sang."
    session.add(s3)
    
    session.commit()
    
    # Reload project to ensure all relationships are fresh
    db_project = session.get(Project, project.id)
    window.load_project(db_project)
    return db_project

def test_search_ui_elements_exist(window):
    """Test that all search UI elements are present in MainWindow."""
    assert hasattr(window, "search_input")
    assert isinstance(window.search_input, QLineEdit)
    assert hasattr(window, "search_counter_label")
    assert isinstance(window.search_counter_label, QLabel)
    assert hasattr(window, "search_clear_button")
    assert isinstance(window.search_clear_button, QPushButton)
    assert hasattr(window, "search_scope_combo")
    assert isinstance(window.search_scope_combo, QComboBox)

def test_search_highlighting_oe(qtbot, window, search_project):
    """Test that typing in the search box highlights matches in OE text."""
    window.search_input.setText("Se ")
    qtbot.wait(200)
    
    assert window.search_counter_label.text() == "1 / 2"
    assert len(window.sentence_cards[0].oe_text_edit.extraSelections()) > 0
    assert len(window.sentence_cards[1].oe_text_edit.extraSelections()) == 0
    assert len(window.sentence_cards[2].oe_text_edit.extraSelections()) > 0

def test_search_scope_switching(qtbot, window, search_project):
    """Test that switching scope updates search results."""
    window.search_input.setText("The ")
    qtbot.wait(200)
    assert "0 / 0" in window.search_counter_label.text()
    
    window.search_scope_combo.setCurrentText("ModE text")
    qtbot.wait(200)
    assert "1 / 3" in window.search_counter_label.text()
    
    assert len(window.sentence_cards[0].translation_edit.extraSelections()) > 0
    assert len(window.sentence_cards[1].translation_edit.extraSelections()) > 0
    assert len(window.sentence_cards[2].translation_edit.extraSelections()) > 0

def test_search_navigation(qtbot, window, search_project):
    """Test navigation with Enter, N, and Shift+N."""
    window.search_input.setText("Se ")
    qtbot.wait(200)
    assert "1 / 2" in window.search_counter_label.text()
    assert window.action_service.current_match_index == 0
    
    # Focus search input and press Enter/Return
    window.search_input.setFocus()
    qtbot.keyClick(window.search_input, Qt.Key.Key_Return)
    qtbot.wait(200)
    
    # Check if first match is focused (logic verification)
    assert window.action_service.current_match_index == 0
    
    # Press N
    window.action_service.next_match()
    qtbot.wait(200)
    assert window.action_service.current_match_index == 1
    assert "2 / 2" in window.search_counter_label.text()
    
    # Press N again (wrap around)
    window.action_service.next_match()
    qtbot.wait(200)
    assert window.action_service.current_match_index == 0
    assert "1 / 2" in window.search_counter_label.text()
    
    # Press Shift+N (previous)
    window.action_service.prev_match()
    qtbot.wait(200)
    assert window.action_service.current_match_index == 1
    assert "2 / 2" in window.search_counter_label.text()

def test_search_no_matches_feedback(qtbot, window, search_project):
    """Test visual feedback when no matches are found."""
    window.search_input.setText("NonExistentWord")
    qtbot.wait(200)
    assert "0 / 0" in window.search_counter_label.text()
    assert "background-color: #ffcccc;" in window.search_input.styleSheet()
    
    window.search_input.clear()
    qtbot.wait(200)
    assert window.search_input.styleSheet() == ""

def test_search_disabling_during_edit(qtbot, window, search_project):
    """Test that search UI is disabled when a card is in edit mode."""
    card = window.sentence_cards[0]
    qtbot.mouseClick(card.edit_oe_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)
    
    assert not window.search_input.isEnabled()
    assert not window.search_clear_button.isEnabled()
    assert not window.search_scope_combo.isEnabled()
    
    qtbot.mouseClick(card.cancel_edit_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)
    
    assert window.search_input.isEnabled()
    assert window.search_clear_button.isEnabled()
    assert window.search_scope_combo.isEnabled()

def test_search_clearing(qtbot, window, search_project):
    """Test clearing search with button and Esc."""
    window.search_input.setText("Se ")
    qtbot.wait(200)
    assert window.search_input.text() == "Se "
    
    qtbot.mouseClick(window.search_clear_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)
    assert window.search_input.text() == ""
    
    window.search_input.setText("Se ")
    qtbot.wait(200)
    window.search_input.setFocus()
    qtbot.keyClick(window.search_input, Qt.Key.Key_Escape)
    qtbot.wait(200)
    assert window.search_input.text() == ""

def test_translation_readonly_during_search(qtbot, window, search_project):
    """Test that translation boxes are read-only during active search."""
    card = window.sentence_cards[0]
    assert not card.translation_edit.isReadOnly()
    
    window.search_input.setText("Se ")
    qtbot.wait(200)
    assert card.translation_edit.isReadOnly()
    
    window.search_input.clear()
    qtbot.wait(200)
    assert not card.translation_edit.isReadOnly()
