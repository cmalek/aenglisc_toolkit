"""Heading slot rules and title writes for heading sentences."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import func, select

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from sqlalchemy.orm import Session

    from oeapp.models.chapter import Chapter
    from oeapp.models.paragraph import Paragraph
    from oeapp.models.section import Section
    from oeapp.models.sentence import Sentence

#: The 1-based slot in the opening section that may hold a section heading.
_SECTION_HEADING_INDEX = 2


class HeadingRole(StrEnum):
    """
    The role a heading sentence plays, as stored in ``Sentence.heading_role``.
    """

    #: A chapter heading.
    CHAPTER = "chapter"
    #: A section heading.
    SECTION = "section"
    #: A subsection heading.
    SUBSECTION = "subsection"


def _section_sentences(section: Section) -> list[Sentence]:
    """
    Return a section's sentences in display order.

    Args:
        section: The section to read

    Returns:
        Every sentence in the section's paragraphs, sorted by ``display_order``

    """
    return sorted(
        (s for paragraph in section.paragraphs for s in paragraph.sentences),
        key=lambda s: s.display_order,
    )


def section_index(sentence: Sentence) -> int:
    """
    Return the 1-based display position of a sentence within its section.

    Args:
        sentence: The sentence to locate

    Returns:
        The position, or ``1`` when the sentence has no paragraph

    """
    if sentence.paragraph is None:
        return 1
    for index, other in enumerate(_section_sentences(sentence.paragraph.section), 1):
        if other is sentence or (other.id is not None and other.id == sentence.id):
            return index
    return 1


def is_opening_section(sentence: Sentence) -> bool:
    """
    Return whether the sentence sits in its chapter's opening section.

    The opening section is the one with the lowest ``Section.number``.

    Args:
        sentence: The sentence to check

    Returns:
        ``True`` when the sentence's section is the chapter's opening section

    """
    if sentence.paragraph is None:
        return False
    section = sentence.paragraph.section
    opening = min(section.chapter.sections, key=lambda s: s.number)
    return opening is section or opening.id == section.id


def is_verse_section(section: Section) -> bool:
    """
    Return whether a section is verse.

    A section is verse when it has at least one sentence and every sentence
    is verse.

    Args:
        section: The section to check

    Returns:
        ``True`` when the section is verse

    """
    sentences = _section_sentences(section)
    return bool(sentences) and all(s.is_verse for s in sentences)


def _opening_slot_role(section: Section, index: int) -> HeadingRole | None:
    """
    Return the role an opening-section slot allows.

    Args:
        section: The sentence's section
        index: The sentence's 1-based position in the section

    Returns:
        The allowed role, or ``None``

    """
    if index == 1:
        return HeadingRole.CHAPTER
    if index > _SECTION_HEADING_INDEX:
        return HeadingRole.SUBSECTION
    first = _section_sentences(section)[0]
    if is_verse_section(section) or first.heading_role != HeadingRole.CHAPTER:
        return None
    return HeadingRole.SECTION


def allowed_role(sentence: Sentence) -> HeadingRole | None:
    """
    Return the heading role this sentence's slot allows.

    The sentence's own current ``heading_role`` is ignored.

    Args:
        sentence: The sentence to check

    Returns:
        The allowed role, or ``None`` when the slot allows no heading

    """
    if sentence.paragraph is None:
        return None
    section = sentence.paragraph.section
    index = section_index(sentence)
    if is_opening_section(sentence):
        return _opening_slot_role(section, index)
    if index == 1:
        return None if is_verse_section(section) else HeadingRole.SECTION
    return HeadingRole.SUBSECTION


def apply_heading_title(sentence: Sentence) -> None:
    """
    Write the sentence's Old English text as its division's title.

    A ``chapter`` heading names the chapter and a ``section`` heading names the
    section, both with ``title_auto`` false. Other roles do nothing.

    Args:
        sentence: The heading sentence

    Side Effects:
        Sets ``title`` and ``title_auto`` on the sentence's chapter or section.

    """
    division = _division_for(sentence)
    if division is None:
        return
    division.title = sentence.text_oe
    division.title_auto = False


def apply_generated_title(sentence: Sentence) -> None:
    """
    Write a generated ``Chapter {n}`` or ``Section {n}`` title.

    Applies to a ``chapter`` or ``section`` heading sentence, using the
    division it currently belongs to. Other roles do nothing.

    Args:
        sentence: The heading sentence

    Side Effects:
        Sets ``title`` and ``title_auto`` (true) on the sentence's chapter or
        section.

    """
    division = _division_for(sentence)
    if division is None:
        return
    _write_generated_title(division, sentence.heading_role)


def _write_generated_title(division: Chapter | Section, role: str | None) -> None:
    """
    Write a generated ``Chapter {n}`` or ``Section {n}`` title.

    Args:
        division: The chapter or section to name
        role: The ``heading_role`` that titled it; ``chapter`` gives a chapter
            name and anything else a section name

    Side Effects:
        Sets ``title`` and ``title_auto`` (true) on ``division``.

    """
    label = "Chapter" if role == HeadingRole.CHAPTER else "Section"
    division.title = f"{label} {division.number}"
    division.title_auto = True


def _needs_official_title(chapter: Chapter) -> bool:
    """
    Return whether a chapter has an official title with no heading sentence.

    Args:
        chapter: The chapter to check

    Returns:
        ``True`` when the title is official and non-blank and no sentence in
        the chapter has a ``heading_role``

    """
    if chapter.title_auto or not chapter.title or not chapter.title.strip():
        return False
    return not any(
        sentence.heading_role is not None
        for section in chapter.sections
        for sentence in _section_sentences(section)
    )


def _insert_title_sentence(
    chapter: Chapter,
    paragraph: Paragraph,
    display_order: int,
    *,
    session: Session,
) -> Sentence:
    """
    Create the chapter's title as a sentence.

    Args:
        chapter: The chapter whose title becomes the sentence
        paragraph: The paragraph that receives the sentence
        display_order: The new sentence's project display order

    Keyword Args:
        session: The session to write through

    Side Effects:
        Adds a sentence and its tokens to the session. Does not commit.

    Returns:
        The new sentence, with no heading role yet

    """
    from oeapp.models.sentence import Sentence  # noqa: PLC0415

    sentence = Sentence.create(
        project_id=chapter.project_id,
        display_order=display_order,
        text_oe=cast("str", chapter.title),
        paragraph_id=paragraph.id,
        commit=False,
        session=session,
    )
    session.expire(paragraph, ["sentences"])
    return sentence


def _next_project_order(chapter: Chapter, *, session: Session) -> int:
    """
    Return the next free display order in the chapter's project.

    Args:
        chapter: A chapter of the project

    Keyword Args:
        session: The session to read through

    Returns:
        One more than the project's highest sentence display order

    """
    from oeapp.models.sentence import Sentence  # noqa: PLC0415

    highest = session.scalar(
        select(func.max(Sentence.display_order)).where(
            Sentence.project_id == chapter.project_id
        )
    )
    return (highest or 0) + 1


def _shift_from(first: Sentence, *, session: Session) -> None:
    """
    Move a sentence and every later project sentence up by one display order.

    Args:
        first: The first sentence to move

    Keyword Args:
        session: The session to write through

    Side Effects:
        Renumbers sentences with ``Sentence.renumber_sentences``, which commits
        the session's current transaction.

    """
    from oeapp.models.sentence import Sentence  # noqa: PLC0415

    moving = Sentence.subsequent_sentences(
        first.project_id, first.display_order - 1, session=session
    )
    Sentence.renumber_sentences(
        list(moving),
        order_function=lambda s: s.display_order + 1,
        session=session,
    )


def promote_official_chapter_title(chapter: Chapter, *, session: Session) -> None:
    """
    Turn a chapter's official title into its chapter heading sentence.

    Does nothing when any sentence in the chapter already has a
    ``heading_role``, when the title is generated, or when it is missing or
    blank. Otherwise it looks at the opening section. An empty section gets the
    title as a new first sentence at the end of the project's display order. A
    first sentence whose ``text_oe`` equals the title exactly (no case folding,
    no stripping) becomes the chapter heading. Any other first sentence is
    pushed down one display order and the title is inserted before it.

    Args:
        chapter: The chapter to promote

    Keyword Args:
        session: The session to read and write through

    Side Effects:
        May add a sentence and renumber later project sentences. Sets
        ``heading_role`` on the heading sentence and rewrites the chapter's
        title with ``title_auto`` false. Does not commit, except that
        ``Sentence.renumber_sentences`` commits when it shifts display orders.

    """
    session.flush()
    session.expire(chapter, ["sections"])
    if not _needs_official_title(chapter):
        return
    opening = min(chapter.sections, key=lambda s: s.number)
    session.expire(opening, ["paragraphs"])
    paragraphs = sorted(opening.paragraphs, key=lambda p: p.order)
    if not paragraphs:
        return
    sentences = _section_sentences(opening)
    if not sentences:
        order = _next_project_order(chapter, session=session)
        heading = _insert_title_sentence(chapter, paragraphs[0], order, session=session)
    elif sentences[0].text_oe == chapter.title:
        heading = sentences[0]
    else:
        first = sentences[0]
        order, paragraph = first.display_order, first.paragraph
        _shift_from(first, session=session)
        heading = _insert_title_sentence(chapter, paragraph, order, session=session)
    heading.heading_role = HeadingRole.CHAPTER.value
    session.flush()
    session.refresh(heading)
    apply_heading_title(heading)
    session.flush()


def heading_is_legal(sentence: Sentence) -> bool:
    """
    Return whether the sentence's heading sits in a legal slot.

    Args:
        sentence: The sentence to check

    Returns:
        ``True`` when ``heading_role`` is ``None`` or matches ``allowed_role``

    """
    return sentence.heading_role is None or sentence.heading_role == allowed_role(
        sentence
    )


def _division_for(sentence: Sentence) -> Chapter | Section | None:
    """
    Return the chapter or section that a heading sentence titles.

    Args:
        sentence: The heading sentence

    Returns:
        The chapter for a ``chapter`` role, the section for a ``section`` role,
        otherwise ``None``

    """
    if sentence.paragraph is None:
        return None
    section = sentence.paragraph.section
    if sentence.heading_role == HeadingRole.CHAPTER:
        return section.chapter
    if sentence.heading_role == HeadingRole.SECTION:
        return section
    return None


def headings_illegal_after(section: Section) -> list[Sentence]:
    """
    Find the heading sentences in a section that no longer sit in a legal slot.

    Args:
        section: The section to check

    Returns:
        Sentences whose ``heading_role`` is set and not :func:`heading_is_legal`,
        in display order

    """
    return [
        sentence
        for sentence in _section_sentences(section)
        if sentence.heading_role is not None and not heading_is_legal(sentence)
    ]


@dataclass(frozen=True)
class _Slot:
    """What a slot rule needs to know about one sentence in a predicted layout."""

    #: The sentence's ``heading_role``, or ``None``.
    role: str | None
    #: Whether the sentence is verse.
    is_verse: bool


#: The slot of a sentence that does not exist yet: no heading, not verse.
_NEW_SLOT = _Slot(role=None, is_verse=False)


def _slots_of(sentences: Iterable[Sentence]) -> list[_Slot]:
    """
    Snapshot the slot-rule inputs of sentences.

    Args:
        sentences: Sentences in display order

    Returns:
        One slot per sentence, in the same order

    """
    return [_Slot(s.heading_role, s.is_verse) for s in sentences]


def _section_is_opening(section: Section) -> bool:
    """
    Return whether a section is its chapter's opening section.

    Args:
        section: The section to check

    Returns:
        ``True`` when it has the lowest ``Section.number`` in its chapter

    """
    opening = min(section.chapter.sections, key=lambda s: s.number)
    return opening is section or opening.id == section.id


def _predicted_role(
    slots: Sequence[_Slot], position: int, *, opening: bool, verse: bool
) -> HeadingRole | None:
    """
    Return the role a slot allows in a predicted layout.

    Mirrors :func:`allowed_role`, but reads a predicted layout instead of the
    database.

    Args:
        slots: The section's predicted layout, in display order
        position: The 0-based position to check

    Keyword Args:
        opening: Whether the section is its chapter's opening section
        verse: Whether every slot in the layout is verse

    Returns:
        The allowed role, or ``None``

    """
    index = position + 1
    if not opening:
        if index == 1:
            return None if verse else HeadingRole.SECTION
        return HeadingRole.SUBSECTION
    if index == 1:
        return HeadingRole.CHAPTER
    if index > _SECTION_HEADING_INDEX:
        return HeadingRole.SUBSECTION
    if verse or slots[0].role != HeadingRole.CHAPTER:
        return None
    return HeadingRole.SECTION


def _layout_is_legal(slots: Sequence[_Slot], *, opening: bool) -> bool:
    """
    Return whether every heading in a predicted layout sits in a legal slot.

    Args:
        slots: The section's predicted layout, in display order

    Keyword Args:
        opening: Whether the section is its chapter's opening section

    Returns:
        ``True`` when each set role equals the role its slot allows

    """
    verse = bool(slots) and all(slot.is_verse for slot in slots)
    return all(
        slot.role is None
        or slot.role == _predicted_role(slots, i, opening=opening, verse=verse)
        for i, slot in enumerate(slots)
    )


class RefusalMixin:
    """
    Let a command record that it refused a move to protect a heading.

    A command that mixes this in calls :meth:`refuse_unless` before it writes.
    """

    #: Whether the last ``execute`` refused because a heading would leave its
    #: legal slot.
    refused: bool = False

    def refuse_unless(self, legal: bool) -> bool:
        """
        Record whether the move is refused.

        Args:
            legal: Whether the move keeps every heading in a legal slot

        Side Effects:
            Sets :attr:`refused`.

        Returns:
            ``True`` when the move must be refused

        """
        self.refused = not legal
        return self.refused


class HeadingTitleMove:
    """
    Keep division titles in step when a move puts a heading on another division.

    Build it before the move, from the sections whose sentences may change
    division, then call :meth:`apply` once the move is written and committed.
    A ``chapter`` or ``section`` heading that now belongs to a different
    division names that division with its Old English text. A division that
    lost the heading and still exists gets its generated name back.

    Args:
        sections: The sections whose sentences may move to another division

    """

    def __init__(self, sections: Iterable[Section]) -> None:
        """
        Record which division each division-titling heading belongs to.

        Args:
            sections: The sections whose sentences may move to another division

        """
        #: Each titling heading with the type and id of its division before the move.
        self._before: list[tuple[Sentence, type[Chapter | Section], int]] = []
        for section in sections:
            for sentence in _section_sentences(section):
                division = _division_for(sentence)
                if division is not None:
                    self._before.append((sentence, type(division), division.id))

    def apply(self, session: Session) -> None:
        """
        Retitle the divisions whose heading moved.

        Args:
            session: The session the move ran in. Its objects must be expired
                or refreshed so each sentence reads its new division.

        Side Effects:
            Sets ``title`` and ``title_auto`` on the receiving and the losing
            division. Does not commit.

        """
        for sentence, kind, old_id in self._before:
            division = _division_for(sentence)
            if division is None or division.id == old_id:
                continue
            apply_heading_title(sentence)
            lost = cast("Chapter | Section | None", session.get(kind, old_id))
            if lost is not None:
                _write_generated_title(lost, sentence.heading_role)


class HeadingMoveGuard:
    """
    Predict whether a structural move keeps every heading in a legal slot.

    Every method reads the current layout and predicts the new one without
    writing. A move is allowed when each heading in each affected section
    would equal the role :func:`allowed_role` gives its new slot.
    """

    @staticmethod
    def allows_insert(
        reference: Sentence, position: Literal["before", "after"]
    ) -> bool:
        """
        Predict an insert next to a sentence.

        Args:
            reference: The sentence the new one goes next to
            position: ``"before"`` or ``"after"`` the reference

        Returns:
            ``True`` when every later heading in the section keeps a legal slot

        """
        if reference.paragraph is None:
            return True
        section = reference.paragraph.section
        sentences = _section_sentences(section)
        at = next(
            (i for i, s in enumerate(sentences) if s.id == reference.id), len(sentences)
        )
        slots = _slots_of(sentences)
        slots.insert(at if position == "before" else at + 1, _NEW_SLOT)
        return _layout_is_legal(slots, opening=_section_is_opening(section))

    @staticmethod
    def allows_removal(sentence: Sentence) -> bool:
        """
        Predict taking a sentence out of its section.

        Args:
            sentence: The sentence that goes away

        Returns:
            ``True`` when every later heading in the section keeps a legal slot

        """
        if sentence.paragraph is None:
            return True
        section = sentence.paragraph.section
        remaining = [s for s in _section_sentences(section) if s.id != sentence.id]
        return _layout_is_legal(
            _slots_of(remaining), opening=_section_is_opening(section)
        )

    @staticmethod
    def allows_split_section(section: Section, paragraph: Paragraph) -> bool:
        """
        Predict splitting a section so a paragraph starts a new one.

        Args:
            section: The section being split
            paragraph: The paragraph that starts the new section

        Returns:
            ``True`` when both halves keep every heading in a legal slot

        """
        paragraphs = sorted(section.paragraphs, key=lambda p: p.order)
        split_at = next(i for i, p in enumerate(paragraphs) if p.id == paragraph.id)
        kept = _slots_of(_paragraph_sentences(paragraphs[:split_at]))
        moved = _slots_of(_paragraph_sentences(paragraphs[split_at:]))
        return _layout_is_legal(
            kept, opening=_section_is_opening(section)
        ) and _layout_is_legal(moved, opening=False)

    @staticmethod
    def allows_merge_section(section: Section, previous: Section) -> bool:
        """
        Predict folding a section into the one before it.

        Args:
            section: The section that goes away
            previous: The section that receives its paragraphs

        Returns:
            ``True`` when the joined section keeps every heading legal

        """
        joined = _slots_of(_section_sentences(previous)) + _slots_of(
            _section_sentences(section)
        )
        return _layout_is_legal(joined, opening=_section_is_opening(previous))

    @staticmethod
    def allows_split_chapter(moved_sections: Sequence[Section]) -> bool:
        """
        Predict moving sections into a new chapter.

        Args:
            moved_sections: The sections that move, in section order

        Returns:
            ``True`` when every moved section keeps its headings legal, the
            first one now being the opening section

        """
        return all(
            _layout_is_legal(_slots_of(_section_sentences(section)), opening=i == 0)
            for i, section in enumerate(moved_sections)
        )

    @staticmethod
    def allows_merge_chapter(sections: Iterable[Section]) -> bool:
        """
        Predict moving a chapter's sections to the end of the chapter before.

        Args:
            sections: The sections that move

        Returns:
            ``True`` when no moved section keeps a heading that needs the
            opening slot

        """
        return all(
            _layout_is_legal(_slots_of(_section_sentences(section)), opening=False)
            for section in sections
        )


def _paragraph_sentences(paragraphs: Iterable[Paragraph]) -> list[Sentence]:
    """
    Return the sentences of paragraphs in display order.

    Args:
        paragraphs: The paragraphs to read

    Returns:
        Their sentences sorted by ``display_order``

    """
    return sorted(
        (s for paragraph in paragraphs for s in paragraph.sentences),
        key=lambda s: s.display_order,
    )
