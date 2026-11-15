"""Heading slot rules and title writes for heading sentences."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

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
    label = "Chapter" if sentence.heading_role == HeadingRole.CHAPTER else "Section"
    division.title = f"{label} {division.number}"
    division.title_auto = True


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
