"""Unit tests for project search behavior."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton

from oeapp.models.chapter import Chapter
from oeapp.models.note import Note
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, db_session):
    """Create a MainWindow instance for testing."""
    win = MainWindow()
    win.app_context.session = db_session
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


@pytest.fixture
def search_project(db_session, window):
    """Create a multi-section project used by search tests."""
    session = window.app_context.session

    project = Project(name="Search Test Project")
    session.add(project)
    session.flush()

    chapter1 = Chapter(project_id=project.id, number=1)
    chapter2 = Chapter(project_id=project.id, number=2)
    session.add_all([chapter1, chapter2])
    session.flush()

    section1 = Section(chapter_id=chapter1.id, number=1)
    section2 = Section(chapter_id=chapter2.id, number=1)
    session.add_all([section1, section2])
    session.flush()

    paragraph1 = Paragraph(section_id=section1.id, order=1)
    paragraph2 = Paragraph(section_id=section2.id, order=1)
    session.add_all([paragraph1, paragraph2])
    session.flush()

    s1 = Sentence.create(
        project_id=project.id,
        paragraph_id=paragraph1.id,
        display_order=1,
        text_oe="Se cyning rad.",
        commit=False,
    )
    s1.text_modern = "The king rode."

    s2 = Sentence.create(
        project_id=project.id,
        paragraph_id=paragraph1.id,
        display_order=2,
        text_oe="Þæt scip seglode.",
        commit=False,
    )
    s2.text_modern = "The ship sailed."

    s3 = Sentence.create(
        project_id=project.id,
        paragraph_id=paragraph2.id,
        display_order=3,
        text_oe="Se helm wearð.",
        commit=False,
    )
    s3.text_modern = "Helm showed the way."

    session.add_all([s1, s2, s3])
    session.flush()

    for token in s1.tokens:
        if token.surface.lower().startswith("cyning") and token.annotation:
            token.annotation.root = "cyning"
    for token in s2.tokens:
        if token.surface.lower().startswith("scip") and token.annotation:
            token.annotation.root = "scip"

    Note.create(
        sentence_id=s2.id,
        note_text_md="Ship note with cynn references",
        note_type="sentence",
        commit=False,
    )
    Note.create(
        sentence_id=s3.id,
        note_text_md="Navigator note: helm marker",
        note_type="sentence",
        commit=False,
    )

    session.commit()

    db_project = session.get(Project, project.id)
    assert db_project is not None
    window.load_project(db_project)
    return db_project


def test_project_search_matches_respects_scope_and_order(search_project):
    """Project.search_matches should mirror UI search counts and ordering."""
    oe_matches = search_project.search_matches("CY-N", "OE Text")
    assert oe_matches.total_match_count >= 1
    assert oe_matches.results
    assert oe_matches.results[0].match_kind in {"oe_surface", "oe_root"}

    mode_matches = search_project.search_matches("cyning", "ModE text")
    assert mode_matches.total_match_count == 0
    assert mode_matches.results == []

    notes_matches = search_project.search_matches("cyn", "Notes")
    assert notes_matches.total_match_count >= 2

    all_matches = search_project.search_matches("helm", "All")
    assert all_matches.total_match_count >= 2


def test_search_ui_elements_exist(window):
    """Search toolbar widgets should be present."""
    assert isinstance(window.search_input, QLineEdit)
    assert isinstance(window.search_counter_label, QLabel)
    assert isinstance(window.search_clear_button, QPushButton)
    assert isinstance(window.search_scope_combo, QComboBox)


def test_search_oe_uses_normalized_token_and_root_matching(qtbot, window, search_project):
    """OE search should normalize the term and match token/root normalized fields."""
    window.search_scope_combo.setCurrentText("OE Text")
    window.search_input.setText("CY-N")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")

    assert "1 /" in window.search_counter_label.text()
    first_card = window.sentence_cards[0]
    assert len(first_card.oe_text_edit.extraSelections()) > 0


def test_mode_scope_only_searches_modern_english(qtbot, window, search_project):
    """ModE scope should not include normalized OE matches."""
    window.search_scope_combo.setCurrentText("ModE text")
    window.search_input.setText("cyning")
    qtbot.waitUntil(lambda: window.search_counter_label.text() == "0 / 0")

    assert window.search_counter_label.text() == "0 / 0"


def test_notes_scope_combines_notes_and_normalized_oe(qtbot, window, search_project):
    """Notes scope should include note text and normalized OE matches."""
    window.search_scope_combo.setCurrentText("Notes")
    window.search_input.setText("cyn")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")

    current, total = [int(part.strip()) for part in window.search_counter_label.text().split("/")]
    assert current == 1
    assert total >= 2


def test_all_scope_combines_oe_mode_and_notes(qtbot, window, search_project):
    """All scope should combine all matching channels."""
    window.search_scope_combo.setCurrentText("All")
    window.search_input.setText("helm")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")

    current, total = [int(part.strip()) for part in window.search_counter_label.text().split("/")]
    assert current == 1
    assert total >= 2


def test_search_navigation_loads_other_chapter_and_focuses_mode_field(
    qtbot, window, search_project
):
    """Navigating to remote ModE match should load chapter/section and focus ModE field."""
    window.search_scope_combo.setCurrentText("ModE text")
    window.search_input.setText("Helm showed")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")

    window.action_service.focus_first_match()
    qtbot.waitUntil(
        lambda: window.chapter_combo.currentData() == search_project.chapters[1].id
    )

    assert window.chapter_combo.currentData() == search_project.chapters[1].id
    assert window.section_combo.currentData() == search_project.chapters[1].sections[0].id
    target_card = window.sentence_cards[0]
    assert target_card.sentence.display_order == 3
    assert window.focusWidget() == target_card.translation_edit


def test_clear_restores_origin_mode_focus(qtbot, window, search_project):
    """Clear should exit search mode and return focus to origin ModE textbox."""
    origin_card = window.sentence_cards[0]
    origin_card.translation_edit.setFocus()
    qtbot.waitUntil(lambda: window.focusWidget() == origin_card.translation_edit)

    window.search_scope_combo.setCurrentText("ModE text")
    window.search_input.setText("Helm showed")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")
    window.action_service.focus_first_match()
    qtbot.waitUntil(
        lambda: window.chapter_combo.currentData() == search_project.chapters[1].id
    )

    qtbot.mouseClick(window.search_clear_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: window.chapter_combo.currentData() == search_project.chapters[0].id
    )

    assert window.chapter_combo.currentData() == search_project.chapters[0].id
    assert window.section_combo.currentData() == search_project.chapters[0].sections[0].id
    restored_card = window.sentence_cards[0]
    assert restored_card.sentence.display_order == 1
    assert window.focusWidget() == restored_card.translation_edit


def test_escape_clears_search_and_restores_origin_mode_focus(qtbot, window, search_project):
    """Escape in active search should restore focus to origin ModE textbox."""
    origin_card = window.sentence_cards[0]
    origin_card.translation_edit.setFocus()
    qtbot.waitUntil(lambda: window.focusWidget() == origin_card.translation_edit)

    window.search_scope_combo.setCurrentText("ModE text")
    window.search_input.setText("Helm showed")
    qtbot.waitUntil(lambda: window.search_counter_label.text() != "0 / 0")
    window.action_service.focus_first_match()
    qtbot.waitUntil(
        lambda: window.chapter_combo.currentData() == search_project.chapters[1].id
    )

    window.search_input.setFocus()
    qtbot.keyClick(window.search_input, Qt.Key.Key_Escape)
    qtbot.waitUntil(
        lambda: window.chapter_combo.currentData() == search_project.chapters[0].id
    )

    assert window.chapter_combo.currentData() == search_project.chapters[0].id
    assert window.section_combo.currentData() == search_project.chapters[0].sections[0].id
    restored_card = window.sentence_cards[0]
    assert restored_card.sentence.display_order == 1
    assert window.focusWidget() == restored_card.translation_edit
