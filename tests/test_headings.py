"""Tests for heading sentences."""

from __future__ import annotations

import pytest
from oeapp.commands import (
    AddSentenceCommand,
    ClearHeadingCommand,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
    SetHeadingCommand,
)
from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.models.chapter import Chapter
from oeapp.models.headings import (
    HeadingRole,
    allowed_role,
    apply_generated_title,
    apply_heading_title,
    HeadingMoveGuard,
    heading_is_legal,
    headings_illegal_after,
    is_opening_section,
    is_verse_section,
    section_index,
)
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.sentence_card_controller import REFUSED_MOVE_TEXT
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QMessageBox

from tests.conftest import create_test_sentence


def test_sentence_json_round_trips_heading_role(db_session) -> None:
    """A heading role is written to the sentence JSON."""
    sentence = create_test_sentence(db_session, text="Beowulf")
    sentence.heading_role = "chapter"
    sentence.save()
    assert sentence.to_json()["heading_role"] == "chapter"


def test_old_sentence_json_without_heading_role_imports(db_session) -> None:
    """Sentence JSON from files predating heading roles still imports."""
    sentence = create_test_sentence(db_session, text="Hwæt")
    payload = sentence.to_json()
    payload.pop("heading_role", None)
    lookup = {
        (
            sentence.paragraph.section.chapter.number,
            sentence.paragraph.section.number,
            sentence.paragraph.order,
        ): sentence.paragraph_id
    }
    project_id = sentence.project_id
    sentence.delete()
    imported = Sentence.from_json(project_id, payload, lookup, session=db_session)
    assert imported.heading_role is None


def _build(session, layout, chapter_number=1):
    """
    Build a chapter whose sections hold the sentences described by ``layout``.

    Args:
        session: SQLAlchemy session
        layout: One list per section; each item is ``True`` for a verse
            sentence and ``False`` for a prose sentence

    Keyword Args:
        chapter_number: The chapter number

    Returns:
        The chapter and a list of sentence lists, one per section

    """
    project = Project.create(text="", name=f"Headings {id(layout)}", session=session)
    chapter = Chapter(project_id=project.id, number=chapter_number)
    session.add(chapter)
    session.flush()
    order = 0
    result = []
    for number, flags in enumerate(layout, 1):
        section = Section(chapter_id=chapter.id, number=number)
        session.add(section)
        session.flush()
        paragraph = Paragraph(section_id=section.id, order=1)
        session.add(paragraph)
        session.flush()
        sentences = []
        for is_verse in flags:
            order += 1
            sentence = Sentence(
                project_id=project.id,
                paragraph_id=paragraph.id,
                display_order=order,
                text_oe=f"Sentence {order}",
                verse_line_start=order if is_verse else None,
                verse_line_end=order if is_verse else None,
            )
            session.add(sentence)
            sentences.append(sentence)
        session.flush()
        result.append(sentences)
    session.refresh(chapter)
    return chapter, result


class TestSlotRules:
    """Which heading a sentence slot allows."""

    def test_section_index_is_one_based_display_order(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        assert [section_index(s) for s in sections[0]] == [1, 2, 3]

    def test_opening_section_is_lowest_number(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        assert is_opening_section(sections[0][0]) is True
        assert is_opening_section(sections[1][0]) is False

    def test_is_verse_section(self, db_session):
        _, sections = _build(db_session, [[True, True], [True, False], []])
        assert is_verse_section(sections[0][0].paragraph.section) is True
        assert is_verse_section(sections[1][0].paragraph.section) is False
        empty = sections[0][0].paragraph.section.chapter.sections[2]
        assert is_verse_section(empty) is False

    def test_opening_allowed_index_one_is_chapter(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        assert allowed_role(sections[0][0]) == HeadingRole.CHAPTER

    def test_opening_allowed_index_two_needs_chapter_heading(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, _third = sections[0]
        assert allowed_role(second) is None
        first.heading_role = "chapter"
        assert allowed_role(second) == HeadingRole.SECTION

    def test_opening_index_two_ignores_own_role(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        first.heading_role = "chapter"
        second.heading_role = "section"
        assert allowed_role(second) == HeadingRole.SECTION
        first.heading_role = None
        assert allowed_role(second) is None

    def test_opening_index_two_blocked_by_section_heading_on_first(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        sections[0][0].heading_role = "section"
        assert allowed_role(sections[0][1]) is None

    def test_opening_allowed_index_three_is_subsection(self, db_session):
        _, sections = _build(db_session, [[False, False, False, False]])
        assert allowed_role(sections[0][2]) == HeadingRole.SUBSECTION
        assert allowed_role(sections[0][3]) == HeadingRole.SUBSECTION

    def test_verse_opening_section(self, db_session):
        _, sections = _build(db_session, [[True, True, True]])
        first, second, third = sections[0]
        assert allowed_role(first) == HeadingRole.CHAPTER
        assert allowed_role(second) is None
        first.heading_role = "chapter"
        assert allowed_role(second) is None
        assert allowed_role(third) == HeadingRole.SUBSECTION

    def test_verse_non_opening_section(self, db_session):
        _, sections = _build(db_session, [[False], [True, True, True]])
        first, second, third = sections[1]
        assert allowed_role(first) is None
        assert allowed_role(second) == HeadingRole.SUBSECTION
        assert allowed_role(third) == HeadingRole.SUBSECTION

    def test_later_prose_section(self, db_session):
        _, sections = _build(db_session, [[False], [False, False]])
        first, second = sections[1]
        assert allowed_role(first) == HeadingRole.SECTION
        assert allowed_role(second) == HeadingRole.SUBSECTION

    def test_heading_is_legal(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        assert heading_is_legal(first) is True
        first.heading_role = "chapter"
        assert heading_is_legal(first) is True
        first.heading_role = "section"
        assert heading_is_legal(first) is False
        second.heading_role = "subsection"
        assert heading_is_legal(second) is False


class TestTitleWrites:
    """Writing divisions' titles from headings."""

    def test_generated_chapter_title(self, db_session):
        chapter, sections = _build(db_session, [[False, False]], chapter_number=2)
        sections[0][0].heading_role = "chapter"
        apply_generated_title(sections[0][0])
        assert chapter.title == "Chapter 2"
        assert chapter.title_auto is True

    def test_generated_section_title(self, db_session):
        _, sections = _build(db_session, [[False], [False, False]])
        sections[1][0].heading_role = "section"
        apply_generated_title(sections[1][0])
        section = sections[1][0].paragraph.section
        assert section.title == "Section 2"
        assert section.title_auto is True

    @pytest.mark.parametrize("role", ["subsection", None])
    def test_generated_title_ignores_other_roles(self, db_session, role):
        chapter, sections = _build(db_session, [[False, False]])
        sentence = sections[0][1]
        sentence.heading_role = role
        apply_generated_title(sentence)
        assert chapter.title is None
        assert sentence.paragraph.section.title is None

    def test_heading_title_for_chapter(self, db_session):
        chapter, sections = _build(db_session, [[False]])
        sections[0][0].heading_role = "chapter"
        chapter.title_auto = True
        apply_heading_title(sections[0][0])
        assert chapter.title == sections[0][0].text_oe
        assert chapter.title_auto is False

    def test_heading_title_for_section(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        sentence = sections[1][0]
        sentence.heading_role = "section"
        sentence.paragraph.section.title_auto = True
        apply_heading_title(sentence)
        section = sentence.paragraph.section
        assert section.title == sentence.text_oe
        assert section.title_auto is False

    def test_chapter_heading_leaves_verse_section_title(self, db_session):
        _, sections = _build(db_session, [[True, True]])
        section = sections[0][0].paragraph.section
        section.title = "Lines 1-2"
        section.title_auto = True
        sections[0][0].heading_role = "chapter"
        apply_heading_title(sections[0][0])
        assert section.title == "Lines 1-2"
        assert section.title_auto is True

    @pytest.mark.parametrize("role", ["subsection", None])
    def test_heading_title_ignores_other_roles(self, db_session, role):
        chapter, sections = _build(db_session, [[False, False]])
        sentence = sections[0][1]
        sentence.heading_role = role
        apply_heading_title(sentence)
        assert chapter.title is None
        assert sentence.paragraph.section.title is None


def _hit(command, session):
    """Execute a command and expire the session so reads see its writes."""
    assert command.execute() is True
    session.expire_all()


def test_set_heading_copies_oe_and_clears_auto(db_session) -> None:
    """Marking a chapter heading names the chapter after its Old English text."""
    chapter, sections = _build(db_session, [[False, False]])
    chapter.title = "Chapter 1"
    chapter.title_auto = True
    first = sections[0][0]
    first.text_oe = "Be ðēodwitan"
    db_session.commit()
    command = SetHeadingCommand(sentence_id=first.id, role="chapter")
    _hit(command, db_session)
    assert first.heading_role == "chapter"
    assert chapter.title == "Be ðēodwitan"
    assert chapter.title_auto is False


def test_set_heading_writes_the_allowed_role(db_session) -> None:
    """The stored role is the slot's allowed role, not the declared one."""
    _, sections = _build(db_session, [[False], [False, False]])
    sentence = sections[1][0]
    _hit(SetHeadingCommand(sentence_id=sentence.id, role="chapter"), db_session)
    assert sentence.heading_role == "section"


def test_set_heading_refuses_when_slot_allows_nothing(db_session) -> None:
    """A slot that allows no heading is refused and nothing changes."""
    _, sections = _build(db_session, [[False, False]])
    second = sections[0][1]
    command = SetHeadingCommand(sentence_id=second.id, role="section")
    assert command.execute() is False
    assert second.heading_role is None


def test_set_heading_undo_restores_role_and_title(db_session) -> None:
    """Undo puts back the previous role, title, and title_auto."""
    chapter, sections = _build(db_session, [[False]])
    chapter.title = "Chapter 1"
    chapter.title_auto = True
    db_session.commit()
    command = SetHeadingCommand(sentence_id=sections[0][0].id, role="chapter")
    _hit(command, db_session)
    assert command.undo() is True
    db_session.expire_all()
    assert sections[0][0].heading_role is None
    assert chapter.title == "Chapter 1"
    assert chapter.title_auto is True


def test_clear_chapter_heading_also_clears_section_heading(db_session) -> None:
    """Clearing a chapter heading drops the section heading on index 2."""
    chapter, sections = _build(db_session, [[False, False, False]])
    first, second, _third = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = first.text_oe
    chapter.title_auto = False
    section.title = second.text_oe
    section.title_auto = False
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert first.heading_role is None
    assert second.heading_role is None
    assert chapter.title == "Chapter 1"
    assert chapter.title_auto is True
    assert section.title == "Section 1"
    assert section.title_auto is True
    assert command.cleared_section_heading_id == second.id
    assert command.cleared_section_text_oe == "Sentence 2"
    assert command.cleared_section_number == 1


def test_clear_chapter_heading_undo_restores_both_roles(db_session) -> None:
    """Undo restores both roles and both titles."""
    chapter, sections = _build(db_session, [[False, False]])
    first, second = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = "Sentence 1"
    section.title = "Sentence 2"
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert command.undo() is True
    db_session.expire_all()
    assert first.heading_role == "chapter"
    assert second.heading_role == "section"
    assert chapter.title == "Sentence 1"
    assert chapter.title_auto is False
    assert section.title == "Sentence 2"


def test_clear_chapter_heading_in_verse_section_keeps_lines_title(db_session) -> None:
    """A verse opening section keeps its Lines title and no cascade runs."""
    chapter, sections = _build(db_session, [[True, True, True]])
    first, second, _third = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = "Sentence 1"
    section.title = "Lines 1-3"
    section.title_auto = True
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert command.cleared_section_heading_id is None
    assert second.heading_role == "section"
    assert chapter.title == "Chapter 1"
    assert section.title == "Lines 1-3"
    assert section.title_auto is True


def test_clear_section_heading_restores_section_n(db_session) -> None:
    """A section heading cleared alone restores ``Section {number}``."""
    chapter, sections = _build(db_session, [[False], [False, False]])
    sentence = sections[1][0]
    section = sentence.paragraph.section
    sentence.heading_role = "section"
    section.title = sentence.text_oe
    section.title_auto = False
    chapter.title = "Kept"
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=sentence.id)
    _hit(command, db_session)
    assert sentence.heading_role is None
    assert section.title == "Section 2"
    assert section.title_auto is True
    assert chapter.title == "Kept"
    assert command.cleared_section_heading_id is None


def test_clear_subsection_heading_writes_no_title(db_session) -> None:
    """A subsection clear only clears the role."""
    chapter, sections = _build(db_session, [[False, False, False]])
    sentence = sections[0][2]
    sentence.heading_role = "subsection"
    chapter.title = "Kept"
    db_session.commit()
    _hit(ClearHeadingCommand(sentence_id=sentence.id), db_session)
    assert sentence.heading_role is None
    assert chapter.title == "Kept"
    assert sentence.paragraph.section.title is None


def test_clear_heading_refuses_a_plain_sentence(db_session) -> None:
    """A sentence with no heading role cannot be cleared."""
    _, sections = _build(db_session, [[False]])
    assert ClearHeadingCommand(sentence_id=sections[0][0].id).execute() is False


def test_edit_oe_updates_chapter_title(db_session) -> None:
    """Editing a chapter heading's Old English text renames the chapter."""
    chapter, sections = _build(db_session, [[False]])
    first = sections[0][0]
    first.heading_role = "chapter"
    chapter.title = first.text_oe
    chapter.title_auto = False
    db_session.commit()
    command = EditSentenceCommand(
        sentence_id=first.id,
        field="text_oe",
        before=first.text_oe,
        after="Beowulf",
    )
    _hit(command, db_session)
    assert chapter.title == "Beowulf"
    assert chapter.title_auto is False
    assert command.undo() is True
    db_session.expire_all()
    assert chapter.title == "Sentence 1"


def test_edit_oe_leaves_titles_of_a_plain_sentence(db_session) -> None:
    """Editing a non-heading sentence does not touch titles."""
    chapter, sections = _build(db_session, [[False, False]])
    chapter.title = "Kept"
    db_session.commit()
    second = sections[0][1]
    command = EditSentenceCommand(
        sentence_id=second.id, field="text_oe", before="Sentence 2", after="Other"
    )
    _hit(command, db_session)
    assert chapter.title == "Kept"


def _add_chapter(session, chapter, texts):
    """
    Add a chapter with one section and one paragraph after ``chapter``.

    Args:
        session: SQLAlchemy session
        chapter: The chapter to follow
        texts: Old English text of each new sentence

    Returns:
        The new chapter, its section, and its sentences

    """
    new_chapter = Chapter(project_id=chapter.project_id, number=chapter.number + 1)
    session.add(new_chapter)
    session.flush()
    section = Section(chapter_id=new_chapter.id, number=1)
    session.add(section)
    session.flush()
    paragraph = Paragraph(section_id=section.id, order=1)
    session.add(paragraph)
    session.flush()
    last = max(
        s.display_order
        for sec in chapter.sections
        for p in sec.paragraphs
        for s in p.sentences
    )
    sentences = []
    for offset, text in enumerate(texts, 1):
        sentence = Sentence(
            project_id=chapter.project_id,
            paragraph_id=paragraph.id,
            display_order=last + offset,
            text_oe=text,
        )
        session.add(sentence)
        sentences.append(sentence)
    session.flush()
    session.refresh(new_chapter)
    return new_chapter, section, sentences


def _mark(session, sentence, role, *, title=True):
    """Give a sentence a role and, for a division heading, its title."""
    sentence.heading_role = role
    section = sentence.paragraph.section
    if title and role == "chapter":
        section.chapter.title = sentence.text_oe
        section.chapter.title_auto = False
    if title and role == "section":
        section.title = sentence.text_oe
        section.title_auto = False
    session.commit()


class TestHeadingsIllegalAfter:
    """The section-bounded recheck."""

    def test_returns_misplaced_headings_in_display_order(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        second.heading_role = "section"
        third.heading_role = "subsection"
        db_session.commit()
        assert headings_illegal_after(first.paragraph.section) == [second]

    def test_legal_headings_are_not_returned(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        first.heading_role = "chapter"
        second.heading_role = "section"
        third.heading_role = "subsection"
        db_session.commit()
        assert headings_illegal_after(first.paragraph.section) == []

    def test_other_sections_are_not_walked(self, db_session):
        _, sections = _build(db_session, [[False, False], [False, False]])
        sections[1][0].heading_role = "chapter"
        db_session.commit()
        assert headings_illegal_after(sections[0][0].paragraph.section) == []


class TestDeleteRecheck:
    """Deleting a sentence reverts titles and clears stranded headings."""

    def _delete_first(self, db_session):
        chapter, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        _mark(db_session, third, "subsection")
        chapter2, section2, later = _add_chapter(db_session, chapter, ["Later one"])
        _mark(db_session, later[0], "chapter")
        command = DeleteSentenceCommand(sentence_id=first.id)
        _hit(command, db_session)
        return command, chapter, chapter2, (second, third), later[0]

    def test_delete_chapter_heading_clears_shifted_section_and_subsection(
        self, db_session
    ):
        _, chapter, chapter2, (second, third), later = self._delete_first(db_session)
        assert second.heading_role is None
        assert third.heading_role is None
        assert chapter.title == "Chapter 1"
        assert chapter.title_auto is True
        assert second.paragraph.section.title == "Section 1"
        assert later.heading_role == "chapter"
        assert chapter2.title == "Later one"

    def test_delete_records_cleared_headings_in_display_order(self, db_session):
        command, _, _, (second, third), _ = self._delete_first(db_session)
        assert command.cleared_headings == [
            (second.id, "section", "Sentence 2"),
            (third.id, "subsection", "Sentence 3"),
        ]

    def test_delete_undo_restores_sentence_titles_and_roles(self, db_session):
        command, chapter, _, (second, third), _ = self._delete_first(db_session)
        assert command.undo() is True
        db_session.expire_all()
        assert second.heading_role == "section"
        assert third.heading_role == "subsection"
        assert chapter.title == "Sentence 1"
        assert chapter.title_auto is False
        assert second.paragraph.section.title == "Sentence 2"
        restored = Sentence.get(command.sentence_id, session=db_session)
        assert restored.heading_role == "chapter"
        assert restored.text_oe == "Sentence 1"
        assert restored.display_order == 1

    def test_delete_plain_sentence_clears_nothing(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        command = DeleteSentenceCommand(sentence_id=sections[0][1].id)
        _hit(command, db_session)
        assert command.cleared_headings == []

    def test_delete_does_not_walk_into_the_next_section(self, db_session):
        _, sections = _build(db_session, [[False, False], [False, False]])
        _mark(db_session, sections[1][0], "section")
        _hit(DeleteSentenceCommand(sentence_id=sections[0][1].id), db_session)
        assert sections[1][0].heading_role == "section"

    @pytest.mark.parametrize("removed", [0, 1, 2, 3, 4])
    def test_guard_agrees_with_the_real_recheck(self, db_session, removed):
        _, sections = _build(db_session, [[False] * 5])
        roles = ["chapter", "section", None, "subsection", None]
        for sentence, role in zip(sections[0], roles, strict=True):
            sentence.heading_role = role
        db_session.commit()
        target = sections[0][removed]
        predicted = HeadingMoveGuard.allows_removal(target)
        command = DeleteSentenceCommand(sentence_id=target.id)
        _hit(command, db_session)
        assert predicted is (command.cleared_headings == [])


class TestRefusedMoves:
    """Moves that would strand a heading are refused before any write."""

    def test_add_sentence_before_heading_is_refused(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first = sections[0][0]
        _mark(db_session, first, "chapter")
        command = AddSentenceCommand(
            project_id=first.project_id,
            reference_sentence_id=first.id,
            position="before",
        )
        assert command.execute() is False
        assert command.refused is True
        db_session.expire_all()
        assert first.display_order == 1
        assert first.heading_role == "chapter"

    def test_add_sentence_after_chapter_heading_refuses_when_it_shifts_a_section_heading(
        self, db_session
    ):
        chapter, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        section = first.paragraph.section
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        command = AddSentenceCommand(
            project_id=first.project_id,
            reference_sentence_id=first.id,
            position="after",
        )
        assert command.execute() is False
        db_session.expire_all()
        assert (first.heading_role, second.heading_role) == ("chapter", "section")
        assert chapter.title == "Sentence 1"
        assert section.title == "Sentence 2"
        assert second.display_order == 2

    def test_add_sentence_after_the_last_heading_is_allowed(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        command = AddSentenceCommand(
            project_id=first.project_id,
            reference_sentence_id=second.id,
            position="after",
        )
        assert command.execute() is True
        assert command.refused is False

    def _merge(self, current, following):
        return MergeSentenceCommand(
            current_sentence_id=current.id,
            next_sentence_id=following.id,
            before_text_oe=current.text_oe,
            before_text_modern=current.text_modern,
        )

    def test_merge_heading_with_neighbor_is_refused(self, db_session):
        chapter, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        _mark(db_session, first, "chapter")
        assert self._merge(first, second).execute() is False
        db_session.expire_all()
        assert chapter.title == first.text_oe
        assert first.text_oe == "Sentence 1"

    def test_merge_refuses_when_a_later_heading_would_shift(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        _mark(db_session, third, "subsection")
        command = self._merge(first, second)
        assert command.execute() is False
        assert command.refused is True
        db_session.expire_all()
        assert third.heading_role == "subsection"
        assert Sentence.get(second.id, session=db_session) is not None

    def test_merge_allows_a_later_heading_that_stays_legal(self, db_session):
        _, sections = _build(db_session, [[False] * 5])
        first, second, _third, _fourth, fifth = sections[0]
        _mark(db_session, fifth, "subsection")
        assert self._merge(first, second).execute() is True

    def test_not_chapter_start_refuses_when_the_chapter_heading_would_move(
        self, db_session
    ):
        chapter, sections = _build(db_session, [[False, False]])
        _, section2, later = _add_chapter(db_session, chapter, ["Next", "More"])
        _mark(db_session, later[0], "chapter")
        command = MergeChapterCommand(section_id=section2.id)
        assert command.execute() is False
        assert command.refused is True
        db_session.expire_all()
        assert later[0].heading_role == "chapter"
        assert Chapter.get(later[0].paragraph.section.chapter_id, session=db_session)

    def test_not_chapter_start_allows_a_plain_chapter(self, db_session):
        chapter, _ = _build(db_session, [[False, False]])
        _, section2, _later = _add_chapter(db_session, chapter, ["Next"])
        assert MergeChapterCommand(section_id=section2.id).execute() is True

    def test_merge_section_refuses_when_a_section_heading_would_leave_index_1(
        self, db_session
    ):
        _, sections = _build(db_session, [[False, False], [False, False]])
        head = sections[1][0]
        section = head.paragraph.section
        _mark(db_session, head, "section")
        command = MergeSectionCommand(paragraph_id=head.paragraph_id)
        assert command.execute() is False
        db_session.expire_all()
        assert head.heading_role == "section"
        assert section.title == head.text_oe

    def test_merge_section_allows_a_plain_section(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        command = MergeSectionCommand(paragraph_id=sections[1][0].paragraph_id)
        assert command.execute() is True

    def _two_paragraph_section(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        section = sections[0][0].paragraph.section
        second = Paragraph(section_id=section.id, order=2)
        db_session.add(second)
        db_session.flush()
        sections[0][2].paragraph_id = second.id
        db_session.commit()
        db_session.refresh(section)
        return sections[0], second

    def test_split_section_refuses_when_a_subsection_would_become_first(
        self, db_session
    ):
        sentences, second = self._two_paragraph_section(db_session)
        _mark(db_session, sentences[2], "subsection")
        command = SplitSectionCommand(paragraph_id=second.id)
        assert command.execute() is False
        db_session.expire_all()
        assert sentences[2].heading_role == "subsection"
        assert sentences[2].paragraph_id == second.id

    def test_split_section_allows_a_plain_paragraph(self, db_session):
        _, second = self._two_paragraph_section(db_session)
        assert SplitSectionCommand(paragraph_id=second.id).execute() is True

    def test_split_chapter_refuses_when_a_section_heading_would_become_chapter_slot(
        self, db_session
    ):
        _, sections = _build(db_session, [[False], [False, False]])
        head = sections[1][0]
        _mark(db_session, head, "section")
        command = SplitChapterCommand(section_id=head.paragraph.section_id)
        assert command.execute() is False
        db_session.expire_all()
        assert head.heading_role == "section"

    def test_split_chapter_allows_a_plain_section(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        command = SplitChapterCommand(section_id=sections[1][0].paragraph.section_id)
        assert command.execute() is True


class TestMovedHeadingTitles:
    """A legal move of a heading onto another division moves its title too."""

    def test_split_section_names_the_new_section_after_its_heading(self, db_session):
        chapter, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        section = first.paragraph.section
        later = Paragraph(section_id=section.id, order=2)
        db_session.add(later)
        db_session.flush()
        second.paragraph_id = later.id
        third.paragraph_id = later.id
        db_session.commit()
        db_session.refresh(section)
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        command = SplitSectionCommand(paragraph_id=later.id)
        _hit(command, db_session)
        new_section = Section.get(command.new_section_id, session=db_session)
        assert second.heading_role == "section"
        assert second.paragraph.section_id == new_section.id
        assert (new_section.title, new_section.title_auto) == ("Sentence 2", False)
        assert (section.title, section.title_auto) == ("Section 1", True)
        assert chapter.title == "Sentence 1"

    def test_split_section_undo_restores_the_original_title(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        section = first.paragraph.section
        later = Paragraph(section_id=section.id, order=2)
        db_session.add(later)
        db_session.flush()
        second.paragraph_id = later.id
        db_session.commit()
        db_session.refresh(section)
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        command = SplitSectionCommand(paragraph_id=later.id)
        _hit(command, db_session)
        assert command.undo() is True
        db_session.expire_all()
        assert (section.title, section.title_auto) == ("Sentence 2", False)
        assert second.paragraph.section_id == section.id

    def test_split_section_leaves_titles_alone_when_no_heading_moves(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        section = sections[0][0].paragraph.section
        later = Paragraph(section_id=section.id, order=2)
        db_session.add(later)
        db_session.flush()
        sections[0][2].paragraph_id = later.id
        section.title = "Kept"
        db_session.commit()
        db_session.refresh(section)
        command = SplitSectionCommand(paragraph_id=later.id)
        _hit(command, db_session)
        new_section = Section.get(command.new_section_id, session=db_session)
        assert section.title == "Kept"
        assert new_section.title is None

    def _merge_setup(self, db_session):
        chapter, sections = _build(db_session, [[False], [False, False]])
        first = sections[0][0]
        head = sections[1][0]
        opening = first.paragraph.section
        opening.title = "Section 1"
        opening.title_auto = True
        _mark(db_session, first, "chapter")
        _mark(db_session, head, "section")
        return chapter, opening, head

    def test_merge_section_names_the_receiving_section_after_the_heading(
        self, db_session
    ):
        chapter, opening, head = self._merge_setup(db_session)
        removed_id = head.paragraph.section_id
        _hit(MergeSectionCommand(paragraph_id=head.paragraph_id), db_session)
        assert head.heading_role == "section"
        assert head.paragraph.section_id == opening.id
        assert (opening.title, opening.title_auto) == ("Sentence 2", False)
        assert Section.get(removed_id, session=db_session) is None
        assert chapter.title == "Sentence 1"

    def test_merge_section_undo_restores_both_titles(self, db_session):
        _, opening, head = self._merge_setup(db_session)
        command = MergeSectionCommand(paragraph_id=head.paragraph_id)
        _hit(command, db_session)
        assert command.undo() is True
        db_session.expire_all()
        assert (opening.title, opening.title_auto) == ("Section 1", True)
        restored = head.paragraph.section
        assert restored.id != opening.id
        assert (restored.title, restored.title_auto) == ("Sentence 2", False)
        assert head.heading_role == "section"


class TestGuardMatchesSlotRules:
    """The predicted layout agrees with ``allowed_role`` on real data."""

    @pytest.mark.parametrize("position", ["before", "after"])
    @pytest.mark.parametrize("anchor", [0, 1, 2, 3])
    def test_insert_prediction_matches_a_real_insert(
        self, db_session, position, anchor
    ):
        _, sections = _build(db_session, [[False] * 4])
        for sentence, role in zip(
            sections[0], ["chapter", "section", None, "subsection"], strict=True
        ):
            sentence.heading_role = role
        db_session.commit()
        reference = sections[0][anchor]
        predicted = HeadingMoveGuard.allows_insert(reference, position)
        command = AddSentenceCommand(
            project_id=reference.project_id,
            reference_sentence_id=reference.id,
            position=position,
        )
        if command.execute():
            db_session.expire_all()
            section = reference.paragraph.section
            assert predicted is (headings_illegal_after(section) == [])
        else:
            assert predicted is False


@pytest.fixture
def _no_dialogs(monkeypatch):
    """Capture warning and information dialogs and answer ``Yes`` to questions."""
    shown = {"warning": [], "information": []}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a: shown["warning"].append(a[1:])
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *a: shown["information"].append(a[1:])
    )
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Yes
    )
    return shown


class TestCardDialogs:
    """The card shows the refused-move warning and the delete dialog."""

    def _card(self, qtbot, sentence, main_window):
        stack = QUndoStack()
        card = SentenceCard(sentence, undo_stack=stack, main_window=main_window)
        qtbot.addWidget(card)
        return card, stack

    def test_refused_add_shows_warning_and_pushes_nothing(
        self, qtbot, db_session, mock_main_window, _no_dialogs
    ):
        _, sections = _build(db_session, [[False, False]])
        _mark(db_session, sections[0][0], "chapter")
        card, stack = self._card(qtbot, sections[0][0], mock_main_window)
        card.controller.on_add_sentence_before_clicked()
        assert stack.count() == 0
        assert [d[-1] for d in _no_dialogs["warning"]] == [REFUSED_MOVE_TEXT]

    def test_refused_hierarchy_action_shows_only_the_refused_warning(
        self, qtbot, db_session, mock_main_window, _no_dialogs
    ):
        chapter, sections = _build(db_session, [[False], [False, False]])
        _mark(db_session, sections[1][0], "section")
        card, stack = self._card(qtbot, sections[1][0], mock_main_window)
        card._on_split_chapter_clicked()
        assert stack.count() == 0
        assert [d[-1] for d in _no_dialogs["warning"]] == [REFUSED_MOVE_TEXT]

    def test_refused_move_text_is_verbatim(self):
        assert REFUSED_MOVE_TEXT == (
            "Clear the heading with Not a heading before changing the structure "
            "around it."
        )

    def test_delete_shows_dialog_listing_cleared_headings(
        self, qtbot, db_session, mock_main_window, _no_dialogs
    ):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, third = sections[0]
        _mark(db_session, first, "chapter")
        _mark(db_session, second, "section")
        _mark(db_session, third, "subsection")
        card, stack = self._card(qtbot, first, mock_main_window)
        card.controller.on_delete_clicked()
        assert stack.count() == 1
        assert [d[-1] for d in _no_dialogs["information"]] == [
            "These headings no longer sit in a legal place, so they were cleared:\n"
            '- Section heading on "Sentence 2"\n'
            '- Subsection heading on "Sentence 3"'
        ]

    def test_delete_without_cleared_headings_shows_no_dialog(
        self, qtbot, db_session, mock_main_window, _no_dialogs
    ):
        _, sections = _build(db_session, [[False, False]])
        card, stack = self._card(qtbot, sections[0][1], mock_main_window)
        card.controller.on_delete_clicked()
        assert stack.count() == 1
        assert _no_dialogs["information"] == []
