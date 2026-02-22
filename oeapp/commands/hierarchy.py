"""Hierarchy related commands for Sections and Chapters."""

from dataclasses import dataclass, field

from sqlalchemy import select

from oeapp.models.chapter import Chapter
from oeapp.models.mixins import SessionMixin
from oeapp.models.paragraph import Paragraph
from oeapp.models.section import Section

from .abstract import Command


@dataclass
class SplitSectionCommand(SessionMixin, Command):
    """Command for splitting a section at a specific paragraph."""

    #: The paragraph ID that will start the new section.
    paragraph_id: int
    #: The new section ID (stored for undo).
    new_section_id: int | None = None
    #: The original section ID (stored for undo).
    original_section_id: int | None = None
    #: List of paragraph IDs that were moved to the new section.
    moved_paragraph_ids: list[int] = field(default_factory=list)

    @property
    def needs_full_reload(self) -> bool:
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
        paragraph = Paragraph.get(self.paragraph_id)
        if not paragraph or not paragraph.section_id:
            return False

        original_section = Section.get(paragraph.section_id)
        if not original_section:
            return False

        self.original_section_id = original_section.id
        chapter_id = original_section.chapter_id

        # Get all paragraphs in the original section, ordered by order
        paragraphs = Paragraph.list(section_id=original_section.id)
        paragraphs = sorted(paragraphs, key=lambda p: p.order)

        # Find index of paragraph to split at
        split_index = -1
        for i, p in enumerate(paragraphs):
            if p.id == self.paragraph_id:
                split_index = i
                break

        if split_index <= 0:
            # Not found or already at start of section
            return False

        # Paragraphs to move
        paragraphs_to_move = paragraphs[split_index:]
        self.moved_paragraph_ids = [p.id for p in paragraphs_to_move]

        # Create new section
        new_section = Section.create(
            chapter_id=chapter_id,
            number=original_section.number + 1,
            commit=False,
        )
        self.new_section_id = new_section.id

        # Shift subsequent sections in the same chapter
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id,
            number=original_section.number,
            exclude_section_id=self.new_section_id,
        )
        for s in subsequent_sections:
            s.number += 1
            s.save(commit=False)

        # Move paragraphs to new section and reset their order
        for i, p in enumerate(paragraphs_to_move, 1):
            p.section_id = new_section.id
            p.order = i
            p.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def undo(self) -> bool:
        """
        Undo split section operation. This means:

        - Move all paragraphs back to the original section.
        - Shift the section numbers of all subsequent sections in the chapter back.
        - Delete the new section.
        """
        session = self._get_session()
        if not self.new_section_id or not self.original_section_id:
            return False

        # RE-FETCH EVERYTHING
        new_section = Section.get(self.new_section_id)
        original_section = Section.get(self.original_section_id)
        if not new_section or not original_section:
            return False

        # Find the last order in the original section
        last_order = original_section.last_paragraph_number()

        # Move paragraphs back to original section
        # CRITICAL: Use a query to get them, don't rely on the relationship yet
        paragraphs_to_move = Paragraph.list(section_id=self.new_section_id)

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
            chapter_id=chapter_id,
            number=number_to_remove,
        )
        for s in subsequent_sections:
            s.number -= 1
            s.save(commit=False)

        # Delete the new section
        new_section.delete(commit=False)
        session.commit()
        session.expire_all()
        return True

    def get_description(self) -> str:
        return f"Split section at paragraph {self.paragraph_id}"


@dataclass
class MergeSectionCommand(SessionMixin, Command):
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

    @property
    def needs_full_reload(self) -> bool:
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
        paragraph = Paragraph.get(self.paragraph_id)
        if not paragraph or not paragraph.section_id:
            return False

        current_section = Section.get(paragraph.section_id)
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
        prev_section = Section.previous_section(chapter_id, current_section.number)
        if not prev_section:
            return False

        self.target_section_id = prev_section.id
        last_order = prev_section.last_paragraph_number()

        # Move all paragraphs from current to previous section
        paragraphs_to_move = list(current_section.paragraphs)
        self.moved_paragraph_ids = [p.id for p in paragraphs_to_move]
        for i, p in enumerate(sorted(paragraphs_to_move, key=lambda x: x.order), 1):
            p.section_id = prev_section.id
            p.order = last_order + i
            p.save(commit=False)

        session.flush()
        session.refresh(current_section, attribute_names=["paragraphs"])

        # Delete current section
        current_section.delete(commit=False)

        # Shift subsequent sections back
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id,
            number=self.original_number,
        )
        for s in subsequent_sections:
            s.number -= 1
            s.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def undo(self) -> bool:
        session = self._get_session()
        if (
            not self.removed_section_id
            or not self.target_section_id
            or self.original_number is None
        ):
            return False

        target_section = Section.get(self.target_section_id)
        if not target_section:
            return False

        chapter_id = target_section.chapter_id

        # Shift subsequent sections forward
        subsequent_sections = Section.get_sections_after(
            chapter_id=chapter_id,
            number=self.original_number,
        )
        for s in subsequent_sections:
            s.number += 1
            s.save(commit=False)

        # Re-create the removed section
        new_s = Section.create(
            chapter_id=chapter_id,
            number=self.original_number,
            commit=False,
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

        session.commit()
        session.expire_all()
        return True

    def get_description(self) -> str:
        return f"Merge section at paragraph {self.paragraph_id} with previous"


@dataclass
class SplitChapterCommand(SessionMixin, Command):
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
        return True

    def execute(self) -> bool:
        session = self._get_session()
        section = Section.get(self.section_id)
        if not section or not section.chapter_id:
            return False

        original_chapter = Chapter.get(section.chapter_id)
        if not original_chapter:
            return False

        self.original_chapter_id = original_chapter.id
        project_id = original_chapter.project_id

        # Get all sections in the original chapter, ordered by number
        sections = sorted(
            Section.list(chapter_id=original_chapter.id),
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
        self.moved_section_ids = [s.id for s in sections_to_move]

        # Create new chapter
        new_chapter = Chapter.create(
            project_id=project_id,
            number=original_chapter.number + 1,
            commit=False,
        )
        self.new_chapter_id = new_chapter.id

        # Shift subsequent chapters in the same project
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id,
            number=original_chapter.number,
            exclude_chapter_id=self.new_chapter_id,
        )
        for c in subsequent_chapters:
            c.number += 1
            c.save(commit=False)

        # Move sections to new chapter and reset their number
        for i, s in enumerate(sections_to_move, 1):
            s.chapter_id = new_chapter.id
            s.number = i
            s.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def undo(self) -> bool:
        """
        Undo split chapter operation. This means:

        - Move all sections back to the original chapter.
        - Shift the chapter numbers of all subsequent chapters in the project back.
        - Delete the new chapter.
        """
        session = self._get_session()
        if not self.new_chapter_id or not self.original_chapter_id:
            return False

        new_chapter = Chapter.get(self.new_chapter_id)
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
            project_id=project_id,
            number=number_to_remove,
        )
        for c in subsequent_chapters:
            c.number -= 1
            c.save(commit=False)

        # Delete the new chapter
        new_chapter.delete(commit=False)
        session.commit()
        session.expire_all()
        return True

    def get_description(self) -> str:
        return f"Split chapter at section {self.section_id}"


@dataclass
class MergeChapterCommand(SessionMixin, Command):
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
        return True

    def execute(self) -> bool:
        session = self._get_session()
        section = Section.get(self.section_id)
        if not section or not section.chapter_id:
            return False

        current_chapter = Chapter.get(section.chapter_id)
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
        prev_chapter = Chapter.previous_chapter(project_id, current_chapter.number)
        if not prev_chapter:
            return False

        self.target_chapter_id = prev_chapter.id
        last_number = prev_chapter.last_section_number()

        # Move all sections from current to previous chapter
        sections_to_move = list(current_chapter.sections)
        self.moved_section_ids = [s.id for s in sections_to_move]
        for i, s in enumerate(sorted(sections_to_move, key=lambda x: x.number), 1):
            s.chapter_id = prev_chapter.id
            s.number = last_number + i
            s.save(commit=False)

        session.flush()
        session.refresh(current_chapter, attribute_names=["sections"])

        # Delete current chapter
        current_chapter.delete(commit=False)

        # Shift subsequent chapters back
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id,
            number=self.original_number,
        )
        for c in subsequent_chapters:
            c.number -= 1
            c.save(commit=False)

        session.commit()
        session.expire_all()
        return True

    def undo(self) -> bool:
        session = self._get_session()
        if (
            not self.removed_chapter_id
            or not self.target_chapter_id
            or self.original_number is None
        ):
            return False

        target_chapter = Chapter.get(self.target_chapter_id)
        if not target_chapter:
            return False

        project_id = target_chapter.project_id

        # Shift subsequent chapters forward
        subsequent_chapters = Chapter.get_chapters_after(
            project_id=project_id,
            number=self.original_number,
        )
        for c in subsequent_chapters:
            c.number += 1
            session.add(c)

        # Re-create the removed chapter
        new_c = Chapter.create(
            project_id=project_id,
            number=self.original_number,
            commit=False,
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

    def get_description(self) -> str:
        return f"Merge chapter at section {self.section_id} with previous"
