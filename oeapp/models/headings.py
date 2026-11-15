"""Heading slot rules and title writes for heading sentences."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oeapp.models.chapter import Chapter
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
