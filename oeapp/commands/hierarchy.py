"""Hierarchy related commands for Sections and Chapters."""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from oeapp.models.chapter import Chapter
from oeapp.models.headings import HeadingMoveGuard, HeadingTitleMove, RefusalMixin
from oeapp.models.mixins import SessionMixin
from oeapp.models.paragraph import Paragraph
from oeapp.models.section import Section

from .abstract import Command


@dataclass
class SplitSectionCommand(RefusalMixin, SessionMixin, Command):
    """Command for splitting a section at a specific paragraph."""

    #: The paragraph ID that will start the new section.
    paragraph_id: int
    #: The new section ID (stored for undo).
    new_section_id: int | None = None
    #: The original section ID (stored for undo).
    original_section_id: int | None = None
    #: List of paragraph IDs that were moved to the new section.
    moved_paragraph_ids: list[int] = field(default_factory=list)
    #: The original section's title and ``title_auto`` before the split.
    original_title: tuple[str | None, bool] | None = None

    @property
    def needs_full_reload(self) -> bool:
        """
        Needs full reload.

        Returns:
            Always True, as the section is split and the user needs to reload
            the page to see the changes.

        """
        return True

    def execute(self) -> bool:
        """
        Execute split section operation. This means:

        - Create a new section after the original section.
        - Move all paragraphs after the split paragraph to the new section.
        - Shift the section numbers of all subsequent sections in the chapter.

        Returns:
            bool: True if the operation was successful, False otherwise.

        """
        session = self._get_session()
        paragraph = Paragraph.get(self.paragraph_id, session=session)
        if not paragraph or not paragraph.section_id:
            return False

        original_section = Section.get(paragraph.section_id, session=session)
        if not original_section:
            return False

        self.original_section_id = original_section.id

        # Get all paragraphs in the original section, ordered by order
        paragraphs = Paragraph.list(section_id=original_section.id, session=session)
        paragraphs = sorted(paragraphs, key=lambda p: p.order)

        # Find index of paragraph to split at
        split_index = next(
            (i for i, p in enumerate(paragraphs) if p.id == self.paragraph_id), -1
        )
        if split_index <= 0:
            # Not found or already at start of section
            return False
        if self.refuse_unless(
            HeadingMoveGuard.allows_split_section(original_section, paragraph)
        ):
            return False

        # Paragraphs to move
        paragraphs_to_move = paragraphs[split_index:]
        self.moved_paragraph_ids = [p.id for p in paragraphs_to_move]
        self.original_title = (original_section.title, original_section.title_auto)
        title_moves = HeadingTitleMove([original_section])

        new_section = self._create_following_section(original_section, session)

        # Move paragraphs to new section and reset their order
        for i, p in enumerate(paragraphs_to_move, 1):
            p.section_id = new_section.id
            p.order = i
            p.save(commit=False)

        session.commit()
        session.expire_all()
        title_moves.apply(session)
        session.commit()
        return True

    def _create_following_section(self, original: Section, session: Session) -> Section:
        """
        Create the section after ``original`` and shift the later numbers.

        Args:
            original: The section being split.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`new_section_id`, adds the section, and increments the
            number of every later section in the chapter. Does not commit.

        Returns:
            The new section.

        """
        new_section = Section.create(
            chapter_id=original.chapter_id,
            number=original.number + 1,
            commit=False,
            session=session,
        )
        self.new_section_id = new_section.id
        subsequent_sections = Section.get_sections_after(
            chapter_id=original.chapter_id,
            number=original.number,
            exclude_section_id=self.new_section_id,
            session=session,
        )
        for s in subsequent_sections:
            s.number += 1
            s.save(commit=False)
        return new_section

    def undo(self) -> bool:
        """
        Undo split section operation. This means:

        - Move all paragraphs back to the original section.
        - Shift the section numbers of all subsequent sections in the chapter back.
        - Delete the new section.

        Returns:
            The computed value.

        """
        session = self._get_session()
        if not self.new_section_id or not self.original_section_id:
            return False

        # RE-FETCH EVERYTHING
        new_section = Section.get(self.new_section_id, session=session)
        original_section = Section.get(self.original_section_id, session=session)
        if not new_section or not original_section:
            return False

        # Find the last order in the original section
        last_order = original_section.last_paragraph_number()

        # Move paragraphs back to original section
        # CRITICAL: Use a query to get them, don't rely on the relationship yet
        paragraphs_to_move = Paragraph.list(
            section_id=self.new_section_id, session=session
        )

        for i, p in enumerate(sorted(paragraphs_to_move, key=lambda x: x.order), 1):
            p.section_id = self.original_section_id
            p.order = last_order + i
            p.save(commit=False)

        session.commit()
        session.refresh(new_section, attribute_names=["paragraphs"])

        chapter_id = new_section.chapter_id
        number_to_remove = new_section.number

        # Shift subsequent sections back
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id, number=number_to_remove, session=session
        )
        for s in subsequent_sections:
            s.number -= 1
            s.save(commit=False)

        # Delete the new section
        new_section.delete(commit=False)
        if self.original_title is not None:
            original_section.title, original_section.title_auto = self.original_title
        session.commit()
        session.expire_all()
        return True

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Split section"


@dataclass
class MergeSectionCommand(RefusalMixin, SessionMixin, Command):
    """Command for merging a section with the previous one."""

    #: The paragraph ID that is currently the start of a section.
    paragraph_id: int
    #: The section ID that was removed.
    removed_section_id: int | None = None
    #: The original section ID paragraphs were moved to.
    target_section_id: int | None = None
    #: List of paragraph IDs that were moved.
    moved_paragraph_ids: list[int] = field(default_factory=list)
    #: Original number of the removed section.
    original_number: int | None = None
    #: The removed section's title and ``title_auto`` before the merge.
    removed_title: tuple[str | None, bool] | None = None
    #: The receiving section's title and ``title_auto`` before the merge.
    target_title: tuple[str | None, bool] | None = None

    @property
    def needs_full_reload(self) -> bool:
        """
        Needs full reload.

        Returns:
            The computed value.

        """
        return True

    def execute(self) -> bool:
        """
        Execute merge section operation. This means:

        - Move all paragraphs from the current section to the previous section.
        - Shift the section numbers of all subsequent sections in the chapter.
        - Delete the current section.

        Returns:
            bool: True if the operation was successful, False otherwise.

        """
        session = self._get_session()
        paragraph = Paragraph.get(self.paragraph_id, session=session)
        if not paragraph or not paragraph.section_id:
            return False

        current_section = Section.get(paragraph.section_id, session=session)
        if not current_section or current_section.number == 1:
            # Cannot merge first section of chapter
            return False

        # Verify this paragraph is the first in its section
        first_paragraph = sorted(current_section.paragraphs, key=lambda p: p.order)[0]
        if first_paragraph.id != self.paragraph_id:
            return False

        self.removed_section_id = current_section.id
        self.original_number = current_section.number
        chapter_id = current_section.chapter_id

        # Find previous section in the same chapter
        prev_section = Section.previous_section(
            chapter_id, current_section.number, session=session
        )
        if not prev_section:
            return False
        if self.refuse_unless(
            HeadingMoveGuard.allows_merge_section(current_section, prev_section)
        ):
            return False

        self.target_section_id = prev_section.id
        self.removed_title = (current_section.title, current_section.title_auto)
        self.target_title = (prev_section.title, prev_section.title_auto)
        title_moves = HeadingTitleMove([current_section])
        self._move_paragraphs(current_section, prev_section, session)

        # Delete current section
        current_section.delete(commit=False)

        self._close_number_gap(chapter_id, self.original_number, session)

        session.commit()
        session.expire_all()
        title_moves.apply(session)
        session.commit()
        return True

    @staticmethod
    def _close_number_gap(
        chapter_id: int, removed_number: int, session: Session
    ) -> None:
        """
        Shift the sections after a removed one back by one number.

        Args:
            chapter_id: The chapter the section belonged to.
            removed_number: The number the removed section had.
            session: The session the command runs in.

        Side Effects:
            Decrements ``number`` of every later section. Does not commit.

        """
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id, number=removed_number, session=session
        )
        for s in subsequent_sections:
            s.number -= 1
            s.save(commit=False)

    def _move_paragraphs(
        self, current: Section, previous: Section, session: Session
    ) -> None:
        """
        Move every paragraph of ``current`` to the end of ``previous``.

        Args:
            current: The section being merged away.
            previous: The section that receives the paragraphs.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`moved_paragraph_ids` and each paragraph's
            ``section_id`` and ``order``. Flushes and refreshes ``current``.

        """
        last_order = previous.last_paragraph_number()
        paragraphs_to_move = list(current.paragraphs)
        self.moved_paragraph_ids = [p.id for p in paragraphs_to_move]
        for i, p in enumerate(sorted(paragraphs_to_move, key=lambda x: x.order), 1):
            p.section_id = previous.id
            p.order = last_order + i
            p.save(commit=False)

        session.flush()
        session.refresh(current, attribute_names=["paragraphs"])

    def undo(self) -> bool:
        """
        Undo.

        Returns:
            The computed value.

        """
        session = self._get_session()
        if (
            not self.removed_section_id
            or not self.target_section_id
            or self.original_number is None
        ):
            return False

        target_section = Section.get(self.target_section_id, session=session)
        if not target_section:
            return False

        chapter_id = target_section.chapter_id

        # Shift subsequent sections forward
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id, number=self.original_number, session=session
        )
        for s in subsequent_sections:
            s.number += 1
            s.save(commit=False)

        # Re-create the removed section
        new_s = Section.create(
            chapter_id=chapter_id,
            number=self.original_number,
            commit=False,
            session=session,
        )

        # Move paragraphs back
        # We need to find them in the target section
        paragraphs_to_move = session.scalars(
            select(Paragraph).where(Paragraph.id.in_(self.moved_paragraph_ids))
        ).all()
        for i, p in enumerate(
            sorted(
                paragraphs_to_move, key=lambda x: self.moved_paragraph_ids.index(x.id)
            ),
            1,
        ):
            p.section_id = new_s.id
            p.order = i
            p.save(commit=False)

        if self.removed_title is not None:
            new_s.title, new_s.title_auto = self.removed_title
        if self.target_title is not None:
            target_section.title, target_section.title_auto = self.target_title
        session.commit()
        session.expire_all()
        return True

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Merge sections"


@dataclass
class SplitChapterCommand(RefusalMixin, SessionMixin, Command):
    """Command for splitting a chapter at a specific section."""

    #: The section ID that will start the new chapter.
    section_id: int
    #: The new chapter ID (stored for undo).
    new_chapter_id: int | None = None
    #: The original chapter ID (stored for undo).
    original_chapter_id: int | None = None
    #: List of section IDs that were moved to the new chapter.
    moved_section_ids: list[int] = field(default_factory=list)

    @property
    def needs_full_reload(self) -> bool:
        """
        Needs full reload.

        Returns:
            The computed value.

        """
        return True

    def execute(self) -> bool:
        """
        Execute.

        Returns:
            The computed value.

        """
        session = self._get_session()
        section = Section.get(self.section_id, session=session)
        if not section or not section.chapter_id:
            return False

        original_chapter = Chapter.get(section.chapter_id, session=session)
        if not original_chapter:
            return False

        self.original_chapter_id = original_chapter.id

        # Get all sections in the original chapter, ordered by number
        sections = sorted(
            Section.list(chapter_id=original_chapter.id, session=session),
            key=lambda s: s.number,
        )

        # Find index of section to split at
        split_index = -1
        for i, s in enumerate(sections):
            if s.id == self.section_id:
                split_index = i
                break

        if split_index <= 0:
            # Not found or already at start of chapter
            return False

        # Sections to move
        sections_to_move = sections[split_index:]
        if self.refuse_unless(HeadingMoveGuard.allows_split_chapter(sections_to_move)):
            return False
        self.moved_section_ids = [s.id for s in sections_to_move]

        new_chapter = self._create_following_chapter(original_chapter, session)

        # Move sections to new chapter and reset their number
        for i, s in enumerate(sections_to_move, 1):
            s.chapter_id = new_chapter.id
            s.number = i
            s.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def _create_following_chapter(self, original: Chapter, session: Session) -> Chapter:
        """
        Create the chapter after ``original`` and shift the later numbers.

        Args:
            original: The chapter being split.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`new_chapter_id`, adds the chapter, and increments the
            number of every later chapter in the project. Does not commit.

        Returns:
            The new chapter.

        """
        new_chapter = Chapter.create(
            project_id=original.project_id,
            number=original.number + 1,
            commit=False,
            session=session,
        )
        self.new_chapter_id = new_chapter.id
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=original.project_id,
            number=original.number,
            exclude_chapter_id=self.new_chapter_id,
            session=session,
        )
        for c in subsequent_chapters:
            c.number += 1
            c.save(commit=False)
        return new_chapter

    def undo(self) -> bool:
        """
        Undo split chapter operation. This means:

        - Move all sections back to the original chapter.
        - Shift the chapter numbers of all subsequent chapters in the project back.
        - Delete the new chapter.

        Returns:
            The computed value.

        """
        session = self._get_session()
        if not self.new_chapter_id or not self.original_chapter_id:
            return False

        new_chapter = Chapter.get(self.new_chapter_id, session=session)
        original_chapter = session.get(Chapter, self.original_chapter_id)
        if not new_chapter or not original_chapter:
            return False

        # Find the last section number in the original chapter
        last_number = original_chapter.last_section_number()

        # Move sections back to original chapter
        sections_to_move = session.scalars(
            select(Section).where(Section.chapter_id == self.new_chapter_id)
        ).all()
        for i, s in enumerate(sorted(sections_to_move, key=lambda x: x.number), 1):
            s.chapter_id = self.original_chapter_id
            s.number = last_number + i
            session.add(s)

        session.flush()
        session.refresh(new_chapter, attribute_names=["sections"])

        project_id = new_chapter.project_id
        number_to_remove = new_chapter.number

        # Shift subsequent chapters back
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id, number=number_to_remove, session=session
        )
        for c in subsequent_chapters:
            c.number -= 1
            c.save(commit=False)

        # Delete the new chapter
        new_chapter.delete(commit=False)
        session.commit()
        session.expire_all()
        return True

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Split chapter"


@dataclass
class MergeChapterCommand(RefusalMixin, SessionMixin, Command):
    """Command for merging a chapter with the previous one."""

    #: The section ID that is currently the start of a chapter.
    section_id: int
    #: The chapter ID that was removed.
    removed_chapter_id: int | None = None
    #: The original chapter ID sections were moved to.
    target_chapter_id: int | None = None
    #: List of section IDs that were moved.
    moved_section_ids: list[int] = field(default_factory=list)
    #: Original number of the removed chapter.
    original_number: int | None = None

    @property
    def needs_full_reload(self) -> bool:
        """
        Needs full reload.

        Returns:
            The computed value.

        """
        return True

    def execute(self) -> bool:
        """
        Execute.

        Returns:
            The computed value.

        """
        session = self._get_session()
        section = Section.get(self.section_id, session=session)
        if not section or not section.chapter_id:
            return False

        current_chapter = Chapter.get(section.chapter_id, session=session)
        if not current_chapter or current_chapter.number == 1:
            # Cannot merge first chapter of project
            return False

        # Verify this section is the first in its chapter
        first_section = sorted(current_chapter.sections, key=lambda s: s.number)[0]
        if first_section.id != self.section_id:
            return False

        self.removed_chapter_id = current_chapter.id
        self.original_number = current_chapter.number
        project_id = current_chapter.project_id

        # Find previous chapter in the same project
        prev_chapter = Chapter.previous_chapter(
            project_id, current_chapter.number, session=session
        )
        if not prev_chapter:
            return False
        if self.refuse_unless(
            HeadingMoveGuard.allows_merge_chapter(current_chapter.sections)
        ):
            return False

        self.target_chapter_id = prev_chapter.id
        self._move_sections(current_chapter, prev_chapter, session)

        # Delete current chapter
        current_chapter.delete(commit=False)

        # Shift subsequent chapters back
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id, number=self.original_number, session=session
        )
        for c in subsequent_chapters:
            c.number -= 1
            c.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def _move_sections(
        self, current: Chapter, previous: Chapter, session: Session
    ) -> None:
        """
        Move every section of ``current`` to the end of ``previous``.

        Args:
            current: The chapter being merged away.
            previous: The chapter that receives the sections.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`moved_section_ids` and each section's ``chapter_id``
            and ``number``. Flushes and refreshes ``current``.

        """
        last_number = previous.last_section_number()
        sections_to_move = list(current.sections)
        self.moved_section_ids = [s.id for s in sections_to_move]
        for i, s in enumerate(sorted(sections_to_move, key=lambda x: x.number), 1):
            s.chapter_id = previous.id
            s.number = last_number + i
            s.save(commit=False)

        session.flush()
        session.refresh(current, attribute_names=["sections"])

    def undo(self) -> bool:
        """
        Undo.

        Returns:
            The computed value.

        """
        session = self._get_session()
        if (
            not self.removed_chapter_id
            or not self.target_chapter_id
            or self.original_number is None
        ):
            return False

        target_chapter = Chapter.get(self.target_chapter_id, session=session)
        if not target_chapter:
            return False

        project_id = target_chapter.project_id

        # Shift subsequent chapters forward
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id, number=self.original_number, session=session
        )
        for c in subsequent_chapters:
            c.number += 1
            session.add(c)

        # Re-create the removed chapter
        new_c = Chapter.create(
            project_id=project_id,
            number=self.original_number,
            commit=False,
            session=session,
        )

        # Move sections back
        sections_to_move = session.scalars(
            select(Section).where(Section.id.in_(self.moved_section_ids))
        ).all()
        for i, s in enumerate(
            sorted(sections_to_move, key=lambda x: self.moved_section_ids.index(x.id)),
            1,
        ):
            s.chapter_id = new_c.id
            s.number = i
            s.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Merge chapters"
