"""A translation undo returns to the sentence it changed."""

from unittest.mock import MagicMock, patch

import pytest
from oeapp.models.chapter import Chapter
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.state import AppContext
from oeapp.ui.main_window import MainWindow

BLINK = "oeapp.ui.undo_presenter.blink_translation"


@pytest.fixture
def mock_services():
    """Mock MigrationService and BackupService."""
    with (
        patch("oeapp.ui.main_window.MigrationService") as mock_mig,
        patch("oeapp.ui.main_window.BackupService") as mock_back,
    ):
        mock_mig.return_value.migrate.return_value = MagicMock(
            migration_version="abc", app_version="1.0.0"
        )
        yield mock_mig, mock_back


def _add_section(project: Project, chapter: Chapter, number: int, text: str):
    section = Section.create(chapter_id=chapter.id, number=number)
    paragraph = Paragraph.create(section_id=section.id, order=1)
    Sentence.create(
        project_id=project.id,
        display_order=number * 10,
        text_oe=text,
        paragraph_id=paragraph.id,
    )
    return section


@pytest.fixture
def main_window(qapp, db_session, mock_services):
    """
    Show a project with two sections in chapter one and one in chapter two.
    """
    project = Project.create(text="Se cyning cōm.", name=f"Nav {id(db_session)}")
    chapter_one = project.chapters[0]
    _add_section(project, chapter_one, 2, "Hē wæs gōd.")
    chapter_two = Chapter.create(project_id=project.id, number=2)
    _add_section(project, chapter_two, 1, "Þā fōr hē.")
    db_session.refresh(project)
    window = MainWindow(app_context=AppContext(session=db_session))
    window.app_context.current_project_id = project.id
    window.load_project(project)
    window.show()
    window.activateWindow()
    qapp.processEvents()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def _type(card, text: str, qtbot) -> None:
    card.translation_edit.setFocus()
    card.translation_edit.moveCursor(
        card.translation_edit.textCursor().MoveOperation.End
    )
    qtbot.keyClicks(card.translation_edit, text)


def _two_steps(main_window, qtbot) -> tuple[int, int]:
    """Type ``a`` then ``ab`` as two steps on the first card of section A."""
    card = main_window.sentence_cards[0]
    _type(card, "a", qtbot)
    main_window.app_context.typed_run.end()
    _type(card, "b", qtbot)
    main_window.app_context.typed_run.end()
    assert main_window.app_context.undo_stack.count() == 2  # noqa: PLR2004
    return card.sentence.id, main_window.app_context.current_section_id


def _card(main_window, sentence_id):
    return main_window.project_ui.find_sentence_card(sentence_id)


def _in_view(main_window, card, qapp) -> bool:
    qapp.processEvents()
    viewport = main_window.main_column.viewport()
    top_left = card.mapTo(viewport, card.rect().topLeft())
    return viewport.rect().intersects(card.rect().translated(top_left))


def test_undo_after_section_change_returns_to_sentence(main_window, qtbot, qapp):
    sentence_id, section_a = _two_steps(main_window, qtbot)
    main_window.section_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert _card(main_window, sentence_id) is None
    with (
        patch(BLINK) as blink,
        patch.object(main_window, "focus_section_start") as focus_start,
    ):
        main_window.app_context.undo()
        qapp.processEvents()
    assert main_window.section_combo.currentData() == section_a
    assert main_window.app_context.current_section_id == section_a
    card = _card(main_window, sentence_id)
    assert card is not None
    assert card.translation_edit.toPlainText() == "a"
    assert _in_view(main_window, card, qapp)
    blink.assert_called_once_with(card.translation_edit)
    assert main_window.focusWidget() is card.oe_text_edit
    focus_start.assert_not_called()
    assert main_window.app_context.typed_run.open_command is None
    assert main_window.app_context.undo_stack.count() == 2  # noqa: PLR2004


def test_undo_with_card_shown_does_not_load_or_blink(main_window, qtbot, qapp):
    sentence_id, _ = _two_steps(main_window, qtbot)
    main_window.section_combo.setCurrentIndex(1)
    qapp.processEvents()
    with patch(BLINK):
        main_window.app_context.undo()
    qapp.processEvents()
    with (
        patch(BLINK) as blink,
        patch.object(
            main_window.project_ui,
            "load_section",
            wraps=main_window.project_ui.load_section,
        ) as load_section,
    ):
        main_window.app_context.undo()
        qapp.processEvents()
    blink.assert_not_called()
    load_section.assert_not_called()
    assert _card(main_window, sentence_id).translation_edit.toPlainText() == ""


def test_redo_after_chapter_change_returns_to_sentence(main_window, qtbot, qapp):
    sentence_id, section_a = _two_steps(main_window, qtbot)
    chapter_one = main_window.chapter_combo.currentData()
    main_window.app_context.undo()
    main_window.chapter_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert _card(main_window, sentence_id) is None
    with patch(BLINK) as blink:
        main_window.app_context.redo()
        qapp.processEvents()
    assert main_window.chapter_combo.currentData() == chapter_one
    assert main_window.app_context.current_chapter_id == chapter_one
    assert main_window.section_combo.currentData() == section_a
    assert main_window.section_combo.count() == 2  # noqa: PLR2004
    card = _card(main_window, sentence_id)
    assert card.translation_edit.toPlainText() == "ab"
    blink.assert_called_once_with(card.translation_edit)


def test_chapter_change_focuses_first_old_english_editor(main_window, qtbot, qapp):
    _type(main_window.sentence_cards[0], "a", qtbot)
    main_window.chapter_combo.setCurrentIndex(1)
    qapp.processEvents()
    first = main_window.sentence_cards[0]
    assert main_window.focusWidget() is first.oe_text_edit
    assert main_window.focusWidget() is not first.translation_edit


def test_section_change_focuses_first_old_english_editor(main_window, qtbot, qapp):
    _type(main_window.sentence_cards[0], "a", qtbot)
    main_window.section_next_button.click()
    qapp.processEvents()
    assert main_window.focusWidget() is main_window.sentence_cards[0].oe_text_edit


def test_search_navigation_to_other_chapter_keeps_focus_choice(main_window, qapp):
    chapter_two = main_window.chapter_combo.itemData(1)
    target = Chapter.get(chapter_two).sections[0]
    sentence_id = target.paragraphs[0].sentences[0].id
    with patch.object(main_window, "focus_section_start") as focus_start:
        card = main_window.project_ui.navigate_to_sentence(
            chapter_two, target.id, sentence_id
        )
        qapp.processEvents()
    focus_start.assert_not_called()
    assert card is not None
    assert card.sentence.id == sentence_id
    assert main_window.chapter_combo.currentData() == chapter_two
    assert main_window.section_combo.currentData() == target.id
    assert main_window.app_context.current_chapter_id == chapter_two


def test_blink_translation_restores_style_without_push(main_window, qtbot):
    from oeapp.ui.undo_presenter import blink_translation  # noqa: PLC0415

    edit = main_window.sentence_cards[0].translation_edit
    before = edit.styleSheet()
    count = main_window.app_context.undo_stack.count()
    blink_translation(edit)
    assert edit.styleSheet() != before
    qtbot.waitUntil(lambda: edit.styleSheet() == before, timeout=2000)
    assert main_window.app_context.undo_stack.count() == count
