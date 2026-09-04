import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QMenu
from oeapp.models.project import Project
from oeapp.models.chapter import Chapter
from oeapp.models.section import Section
from oeapp.models.paragraph import Paragraph
from oeapp.models.sentence import Sentence
from oeapp.ui.sentence_card import SentenceCard
from oeapp.commands import CommandManager
from oeapp.ui.sentence_card_controller import HierarchyPosition
from unittest.mock import MagicMock

@pytest.fixture
def mock_main_window():
    mock = MagicMock()
    mock.messages = MagicMock()
    return mock

@pytest.fixture
def hierarchy_project(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()

    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()

    section = Section(chapter_id=chapter.id, number=1)
    db_session.add(section)
    db_session.flush()

    p1 = Paragraph(section_id=section.id, order=1)
    db_session.add(p1)
    db_session.flush()

    s1 = Sentence(project_id=project.id, paragraph_id=p1.id, display_order=1, text_oe="Sentence 1")
    s2 = Sentence(project_id=project.id, paragraph_id=p1.id, display_order=2, text_oe="Sentence 2")
    s3 = Sentence(project_id=project.id, paragraph_id=p1.id, display_order=3, text_oe="Sentence 3")
    db_session.add_all([s1, s2, s3])
    db_session.flush()
    return project, s1, s2, s3

def test_sentence_card_dropdown_middle_of_paragraph(qtbot, db_session, hierarchy_project, mock_main_window):
    project, s1, s2, s3 = hierarchy_project
    # Ensure s2 is NOT the first sentence of the project
    s1.display_order = 1
    s2.display_order = 2
    s3.display_order = 3
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)
    card.show() # Ensure visibility logic works
    qtbot.addWidget(card)

    # s2 is in middle of paragraph
    assert card.toggle_paragraph_button.isVisible()
    menu = card.paragraph_menu
    actions = menu.actions()
    assert len(actions) == 1
    assert actions[0].text() == "Paragraph Start"

def test_sentence_card_dropdown_paragraph_start(qtbot, db_session, hierarchy_project, mock_main_window):
    project, s1, s2, s3 = hierarchy_project

    # Make s2 a paragraph start
    p2 = Paragraph(section_id=s1.paragraph.section_id, order=2)
    db_session.add(p2)
    db_session.flush()
    s2.paragraph_id = p2.id
    s3.paragraph_id = p2.id
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)
    qtbot.addWidget(card)

    # s2 is now paragraph start, but not section start
    actions = card.paragraph_menu.actions()
    assert any(a.text() == "Not Paragraph Start" for a in actions)
    assert any(a.text() == "Section Start" for a in actions)
    assert not any(a.text() == "Paragraph Start" for a in actions)

def test_sentence_card_dropdown_section_start(qtbot, db_session, hierarchy_project, mock_main_window):
    project, s1, s2, s3 = hierarchy_project

    # Make s2 a section start
    chapter = s1.paragraph.section.chapter
    sec2 = Section(chapter_id=chapter.id, number=2)
    db_session.add(sec2)
    db_session.flush()
    p2 = Paragraph(section_id=sec2.id, order=1)
    db_session.add(p2)
    db_session.flush()
    s2.paragraph_id = p2.id
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)
    qtbot.addWidget(card)

    # s2 is now section start, but not chapter start
    actions = card.paragraph_menu.actions()
    assert any(a.text() == "Not Paragraph Start" for a in actions)
    assert any(a.text() == "Not Section Start" for a in actions)
    assert any(a.text() == "Chapter Start" for a in actions)

def test_sentence_card_dropdown_chapter_start(qtbot, db_session, hierarchy_project, mock_main_window):
    project, s1, s2, s3 = hierarchy_project

    # Make s2 a chapter start
    ch2 = Chapter(project_id=project.id, number=2)
    db_session.add(ch2)
    db_session.flush()
    sec2 = Section(chapter_id=ch2.id, number=1)
    db_session.add(sec2)
    db_session.flush()
    p2 = Paragraph(section_id=sec2.id, order=1)
    db_session.add(p2)
    db_session.flush()
    s2.paragraph_id = p2.id
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)
    qtbot.addWidget(card)

    # s2 is now chapter start
    actions = card.paragraph_menu.actions()
    assert any(a.text() == "Not Paragraph Start" for a in actions)
    assert any(a.text() == "Not Section Start" for a in actions)
    assert any(a.text() == "Not Chapter Start" for a in actions)


def test_get_hierarchy_position_middle_of_paragraph(
    db_session, hierarchy_project, mock_main_window
):
    project, s1, s2, s3 = hierarchy_project
    s1.display_order = 1
    s2.display_order = 2
    s3.display_order = 3
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)

    position = card.controller.get_hierarchy_position(s2)

    assert position == HierarchyPosition(
        is_paragraph_start=False, is_section_start=False, is_chapter_start=False
    )


def test_get_hierarchy_position_chapter_start(
    db_session, hierarchy_project, mock_main_window
):
    project, s1, s2, s3 = hierarchy_project

    ch2 = Chapter(project_id=project.id, number=2)
    db_session.add(ch2)
    db_session.flush()
    sec2 = Section(chapter_id=ch2.id, number=1)
    db_session.add(sec2)
    db_session.flush()
    p2 = Paragraph(section_id=sec2.id, order=1)
    db_session.add(p2)
    db_session.flush()
    s2.paragraph_id = p2.id
    db_session.commit()

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)

    position = card.controller.get_hierarchy_position(s2)

    assert position == HierarchyPosition(
        is_paragraph_start=True, is_section_start=True, is_chapter_start=True
    )


def test_on_split_paragraph_clicked_executes_command_via_controller(
    db_session, hierarchy_project, mock_main_window
):
    project, s1, s2, s3 = hierarchy_project

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)

    assert card.controller.on_split_paragraph_clicked() is True
    db_session.refresh(s2)
    assert s2.paragraph_id != s1.paragraph_id


def test_on_merge_paragraph_clicked_returns_false_when_command_manager_missing(
    db_session, hierarchy_project, mock_main_window, monkeypatch
):
    project, s1, s2, s3 = hierarchy_project

    cmd_manager = CommandManager(db_session)
    card = SentenceCard(s2, command_manager=cmd_manager, main_window=mock_main_window)
    monkeypatch.setattr(card, "command_manager", None)

    assert card.controller.on_merge_paragraph_clicked() is False
