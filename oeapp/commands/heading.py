"""Commands that mark and clear heading sentences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from oeapp.models.headings import (
    HeadingRole,
    allowed_role,
    apply_generated_title,
    apply_heading_title,
    is_verse_section,
    section_index,
)
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence

from .abstract import Command, CommandLocators

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

#: Chapter title, chapter ``title_auto``, section title, section ``title_auto``.
_Titles = tuple[str | None, bool, str | None, bool]

#: The 1-based slot in the opening section that may hold a section heading.
_SECTION_HEADING_INDEX = 2


def _snapshot_titles(sentence: Sentence) -> _Titles | None:
    """
    Record the titles a heading change may rewrite.

    Args:
        sentence: A sentence in the chapter and section to record

    Returns:
        The chapter and section titles with their ``title_auto`` flags, or
        ``None`` when the sentence has no paragraph

    """
    if sentence.paragraph is None:
        return None
    section = sentence.paragraph.section
    chapter = section.chapter
    return (chapter.title, chapter.title_auto, section.title, section.title_auto)


def _restore_titles(sentence: Sentence, titles: _Titles | None) -> None:
    """
    Put back titles recorded by :func:`_snapshot_titles`.

    Args:
        sentence: A sentence in the chapter and section to restore
        titles: The recorded titles, or ``None`` to do nothing

    Side Effects:
        Sets ``title`` and ``title_auto`` on the sentence's chapter and section.

    """
    if titles is None or sentence.paragraph is None:
        return
    section = sentence.paragraph.section
    chapter = section.chapter
    chapter.title, chapter.title_auto, section.title, section.title_auto = titles


def _clear_role(sentence: Sentence) -> None:
    """
    Clear a sentence's heading role, restoring the generated name first.

    A ``chapter`` or ``section`` heading gets its ``Chapter {n}`` or
    ``Section {n}`` title back while it still holds the role. A ``subsection``
    heading only loses the role.

    Args:
        sentence: The heading sentence

    Side Effects:
        Sets ``heading_role`` to ``None`` and may rewrite a title.

    """
    if sentence.heading_role in (HeadingRole.CHAPTER, HeadingRole.SECTION):
        apply_generated_title(sentence)
    sentence.heading_role = None


def _section_heading_below(sentence: Sentence) -> Sentence | None:
    """
    Find the section heading that rides on a chapter heading.

    Args:
        sentence: The chapter heading sentence

    Returns:
        The index-2 sentence of the same section when it has the ``section``
        role and the section is not verse, otherwise ``None``

    """
    if sentence.paragraph is None:
        return None
    section = sentence.paragraph.section
    if is_verse_section(section):
        return None
    for paragraph in section.paragraphs:
        for other in paragraph.sentences:
            if (
                section_index(other) == _SECTION_HEADING_INDEX
                and other.heading_role == HeadingRole.SECTION
            ):
                return other
    return None


@dataclass
class SetHeadingCommand(SessionMixin, Command):
    """
    Mark a sentence as the heading its slot allows.

    The stored role is :func:`~oeapp.models.headings.allowed_role` of the
    sentence, so :attr:`role` is the role the menu offered and is not
    re-checked against the slot.

    Args:
        sentence_id: The sentence to mark.
        role: The role the menu offered.

    """

    #: The sentence ID.
    sentence_id: int
    #: The role the menu offered.
    role: str
    #: The role before the command ran.
    previous_role: str | None = None
    #: The chapter and section titles before the command ran.
    previous_titles: _Titles | None = None

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the project structure must be reloaded after the command.

        Returns:
            ``True``, because the role changes which headings neighbors allow

        """
        return True

    def execute(self) -> bool:
        """
        Mark the sentence and copy its Old English text into the title.

        Side Effects:
            Sets ``heading_role`` and, for a ``chapter`` or ``section``
            heading, the division's title. Commits.

        Returns:
            ``True`` on success, ``False`` when the sentence is missing or its
            slot allows no heading

        """
        session: Session = self._get_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False
        role = allowed_role(sentence)
        if role is None:
            return False
        self.previous_role = sentence.heading_role
        self.previous_titles = _snapshot_titles(sentence)
        sentence.heading_role = role.value
        apply_heading_title(sentence)
        session.commit()
        return True

    def undo(self) -> bool:
        """
        Restore the previous role and titles.

        Side Effects:
            Sets ``heading_role``, titles, and ``title_auto``. Commits.

        Returns:
            ``True`` on success, ``False`` when the sentence is missing

        """
        session: Session = self._get_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False
        sentence.heading_role = self.previous_role
        _restore_titles(sentence, self.previous_titles)
        session.commit()
        return True

    def locators(self) -> CommandLocators:
        """
        Get the sentence this command marks.

        Returns:
            Locators naming :attr:`sentence_id`.

        """
        return CommandLocators(sentence_ids={self.sentence_id})

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Mark heading"


@dataclass
class ClearHeadingCommand(SessionMixin, Command):
    """
    Clear a sentence's heading role and restore the generated name.

    Clearing a chapter heading also clears the section heading on index 2 of
    the same section, unless the section is verse.

    Args:
        sentence_id: The heading sentence to clear.

    """

    #: The sentence ID.
    sentence_id: int
    #: The id of the section-heading sentence this clear also cleared.
    cleared_section_heading_id: int | None = None
    #: The Old English text of that sentence, captured before its role cleared.
    cleared_section_text_oe: str | None = None
    #: The number of the section that sentence heads.
    cleared_section_number: int | None = None
    #: The role the sentence had before the command ran.
    previous_role: str | None = None
    #: The chapter and section titles before the command ran.
    previous_titles: _Titles | None = None

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the project structure must be reloaded after the command.

        Returns:
            ``True``, because the role changes which headings neighbors allow

        """
        return True

    def execute(self) -> bool:
        """
        Clear the heading, and the section heading below a chapter heading.

        Side Effects:
            Sets ``heading_role`` to ``None``, rewrites the chapter and
            section titles to their generated names, and sets
            :attr:`cleared_section_heading_id`. Commits.

        Returns:
            ``True`` on success, ``False`` when the sentence is missing or has
            no heading role

        """
        session: Session = self._get_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None or sentence.heading_role is None:
            return False
        self.previous_role = sentence.heading_role
        self.previous_titles = _snapshot_titles(sentence)
        self.cleared_section_heading_id = None
        self.cleared_section_text_oe = None
        self.cleared_section_number = None
        below = (
            _section_heading_below(sentence)
            if sentence.heading_role == HeadingRole.CHAPTER
            else None
        )
        if below is not None:
            self.cleared_section_heading_id = below.id
            self.cleared_section_text_oe = below.text_oe
            self.cleared_section_number = below.paragraph.section.number
            _clear_role(below)
        _clear_role(sentence)
        session.commit()
        return True

    def undo(self) -> bool:
        """
        Restore both roles and the previous titles.

        Side Effects:
            Sets ``heading_role``, titles, and ``title_auto``. Commits.

        Returns:
            ``True`` on success, ``False`` when the sentence is missing

        """
        session: Session = self._get_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False
        sentence.heading_role = self.previous_role
        if self.cleared_section_heading_id is not None:
            below = Sentence.get(self.cleared_section_heading_id, session=session)
            if below is not None:
                below.heading_role = HeadingRole.SECTION.value
        _restore_titles(sentence, self.previous_titles)
        session.commit()
        return True

    def locators(self) -> CommandLocators:
        """
        Get the sentences this command clears.

        Returns:
            Locators naming :attr:`sentence_id` and, once known, the section
            heading it also cleared.

        """
        ids = {self.sentence_id}
        if self.cleared_section_heading_id is not None:
            ids.add(self.cleared_section_heading_id)
        return CommandLocators(sentence_ids=ids)

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Clear heading"
