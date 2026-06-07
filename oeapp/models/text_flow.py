"""Shared domain rules for full-text rendering flow across UI and export."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class SentenceSeparatorKind(Enum):
    """
    Semantic separator between adjacent rendered sentences.

    Format layers map each kind to plain text or LaTeX output.
    """

    #: No separator (first sentence or titles already inserted).
    NONE = "none"
    #: Consecutive verse lines within one stanza block.
    VERSE_LINE = "verse_line"
    #: Verse line after prose or after a structural break.
    VERSE_BLOCK = "verse_block"
    #: Prose sentence immediately after verse.
    PROSE_AFTER_VERSE = "prose_after_verse"
    #: Prose sentence that starts a new paragraph.
    PARAGRAPH_BREAK = "paragraph_break"
    #: Prose sentence within the same paragraph.
    SENTENCE_SPACE = "sentence_space"


#: Plain-text gaps keyed by :class:`SentenceSeparatorKind`.
_PLAIN_TEXT_SEPARATORS: Final[dict[SentenceSeparatorKind, str]] = {
    SentenceSeparatorKind.NONE: "",
    SentenceSeparatorKind.VERSE_LINE: "\n",
    SentenceSeparatorKind.VERSE_BLOCK: "\n\n",
    SentenceSeparatorKind.PROSE_AFTER_VERSE: "\n\n",
    SentenceSeparatorKind.PARAGRAPH_BREAK: "\n\n",
    SentenceSeparatorKind.SENTENCE_SPACE: " ",
}

#: LaTeX gaps keyed by :class:`SentenceSeparatorKind`.
_LATEX_SEPARATORS: Final[dict[SentenceSeparatorKind, str]] = {
    SentenceSeparatorKind.NONE: "",
    SentenceSeparatorKind.VERSE_LINE: r"\newline ",
    SentenceSeparatorKind.VERSE_BLOCK: r"\par ",
    SentenceSeparatorKind.PROSE_AFTER_VERSE: r"\par ",
    SentenceSeparatorKind.PARAGRAPH_BREAK: r"\par ",
    SentenceSeparatorKind.SENTENCE_SPACE: " ",
}


def is_paragraph_start(sentence: Sentence) -> bool:
    """
    Return ``True`` when ``sentence`` is first in its paragraph by display order.

    Args:
        sentence: Sentence to inspect.

    Returns:
        ``True`` if sentence starts its paragraph.

    """
    if not sentence.paragraph:
        return False
    ordered = sorted(sentence.paragraph.sentences, key=lambda s: s.display_order)
    return bool(ordered and ordered[0].id == sentence.id)


def visible_titles(previous: Sentence | None, current: Sentence) -> list[str]:
    """
    Resolve official chapter/section titles visible at a sentence boundary.

    Auto-generated titles are suppressed. Chapter title precedes section title
    when both change at the same boundary.

    Args:
        previous: Previous rendered sentence, if any.
        current: Current sentence in render order.

    Returns:
        Titles to render before ``current``.

    """
    titles: list[str] = []
    current_section = current.paragraph.section if current.paragraph else None
    current_chapter = current_section.chapter if current_section else None
    previous_section = (
        previous.paragraph.section if previous and previous.paragraph else None
    )
    previous_chapter = previous_section.chapter if previous_section else None

    chapter_changed = current_chapter is not None and (
        previous_chapter is None or current_chapter.id != previous_chapter.id
    )
    if (
        current_chapter is not None
        and chapter_changed
        and current_chapter.title
        and not current_chapter.title_auto
    ):
        titles.append(current_chapter.title)

    section_changed = current_section is not None and (
        previous_section is None or current_section.id != previous_section.id
    )
    if (
        current_section is not None
        and section_changed
        and current_section.title
        and not current_section.title_auto
    ):
        titles.append(current_section.title)
    return titles


def sentence_separator_kind(
    previous: Sentence | None,
    current: Sentence,
    has_titles: bool,
) -> SentenceSeparatorKind:
    """
    Decide semantic separator between ``previous`` and ``current``.

    Args:
        previous: Previous rendered sentence.
        current: Current sentence.
        has_titles: Whether title lines were inserted before ``current``.

    Returns:
        Separator kind for format adapters.

    """
    if previous is None or has_titles:
        return SentenceSeparatorKind.NONE
    if current.is_verse:
        return (
            SentenceSeparatorKind.VERSE_LINE
            if previous.is_verse
            else SentenceSeparatorKind.VERSE_BLOCK
        )
    if previous.is_verse:
        return SentenceSeparatorKind.PROSE_AFTER_VERSE
    if is_paragraph_start(current):
        return SentenceSeparatorKind.PARAGRAPH_BREAK
    return SentenceSeparatorKind.SENTENCE_SPACE


def plain_text_separator(kind: SentenceSeparatorKind) -> str:
    """
    Map separator kind to plain-text gap for UI rendering.

    Args:
        kind: Semantic separator from :func:`sentence_separator_kind`.

    Returns:
        Separator string for ``QTextCursor`` insertion.

    """
    return _PLAIN_TEXT_SEPARATORS[kind]


def latex_separator(kind: SentenceSeparatorKind) -> str:
    """
    Map separator kind to LaTeX gap for PDF export.

    Args:
        kind: Semantic separator from :func:`sentence_separator_kind`.

    Returns:
        LaTeX separator string.

    """
    return _LATEX_SEPARATORS[kind]
