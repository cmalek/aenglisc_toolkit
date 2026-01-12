"""Project model."""

import builtins
import re
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, event, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.exc import AlreadyExists
from oeapp.utils import from_utc_iso, to_utc_iso

from .mixins import SaveDeleteMixin
from .sentence import Sentence
from .token import Token


class Project(SaveDeleteMixin, Base):
    """
    Represents a project.
    """

    __tablename__ = "projects"

    #: The project ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The project name.
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    #: The bibliographic source of the OE text.
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The name of the translator.
    translator: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Free form notes field about the text.
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the project was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the project was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    sentences: Mapped[builtins.list[Sentence]] = relationship(
        "Sentence",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Sentence.display_order",
    )

    @classmethod
    def exists(cls, name: str) -> bool:
        """
        Get all projects.
        """
        session = cls._get_session()
        return session.scalar(select(cls).where(cls.name == name)) is not None

    @classmethod
    def get(cls, project_id: int) -> Project | None:
        """
        Get a project by name.

        Args:
            project_id: Project ID

        Returns:
            Project or None if not found

        """
        session = cls._get_session()
        return session.get(cls, project_id)

    @classmethod
    def first(cls) -> Project | None:
        """
        Get the first project.

        Returns:
            The first project or None if there are no projects

        """
        session = cls._get_session()
        return session.scalar(select(cls).order_by(cls.id).limit(1))

    @classmethod
    def list(cls) -> builtins.list[Project]:
        """
        Get all projects.

        Returns:
            List of projects

        """
        session = cls._get_session()
        return builtins.list(session.scalars(select(cls)).all())

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        text: str,
        name: str = "Untitled Project",
        source: str | None = None,
        translator: str | None = None,
        notes: str | None = None,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Project:
        """
        Create a new project.

        Args:
            text: Old English text to process and add to the project

        Keyword Args:
            name: Project name
            source: Bibliographic source
            translator: Translator name
            notes: Project notes
            commit: Whether to commit the changes

        Returns:
            The new :class:`~oeapp.models.project.Project` object

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(cls.__name__)

        session = cls._get_session()
        # Check if project with this name already exists
        if cls.exists(name):
            raise AlreadyExists("Project", name)  # noqa: EM101

        # Create project
        project = cls(name=name, source=source, translator=translator, notes=notes)
        session.add(project)
        session.flush()  # Get the ID

        sentences_data = cls.split_sentences(text)
        paragraph_number = 1
        sentence_number_in_paragraph = 0

        for order, (sentence_text, is_paragraph_start) in enumerate(sentences_data, 1):
            if is_paragraph_start and order > 1:
                # Starting a new paragraph (but first sentence is always paragraph 1)
                paragraph_number += 1
                sentence_number_in_paragraph = 1
            else:
                # Continuing current paragraph
                sentence_number_in_paragraph += 1
                if order == 1:
                    # First sentence always starts paragraph 1
                    paragraph_number = 1

            Sentence.create(
                project_id=project.id,
                display_order=order,
                text_oe=sentence_text,
                is_paragraph_start=is_paragraph_start,
                paragraph_number=paragraph_number,
                sentence_number_in_paragraph=sentence_number_in_paragraph,
                commit=False,
            )

        if commit:
            session.commit()
            logger.info(
                "project.created",
                project_id=project.id,
                name=name,
                source=source,
                translator=translator,
                notes=notes,
            )

        return project

    def append_oe_text(self, text: str) -> None:
        """
        Append Old English text to the end of this project.

        The Old English text is split into sentences and appended after the last
        sentence in the project.  If the project has no sentences, the new
        sentences start from display_order 1.

        Args:
            text: Old English text to process and append to the project

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        session = self._get_session()
        # Find the maximum display_order for existing sentences
        max_order = (
            session.scalar(
                select(func.max(Sentence.display_order)).where(
                    Sentence.project_id == self.id
                )
            )
            or 0
        )

        # Split text into sentences
        sentences_data = self.split_sentences(text)

        # Get the last sentence to determine current paragraph state
        last_sentence = (
            session.scalar(
                select(Sentence)
                .where(Sentence.project_id == self.id)
                .order_by(Sentence.display_order.desc())
                .limit(1)
            )
            if max_order > 0
            else None
        )

        # Determine starting paragraph and sentence numbers
        if last_sentence:
            start_paragraph = last_sentence.paragraph_number
            current_paragraph = start_paragraph
            current_sentence_in_para = last_sentence.sentence_number_in_paragraph
        else:
            start_paragraph = 0
            current_paragraph = 0
            current_sentence_in_para = 0

        paragraph_number = current_paragraph
        sentence_number_in_paragraph = current_sentence_in_para

        # Create new sentences starting from max_order + 1
        for order_offset, (sentence_text, is_paragraph_start) in enumerate(
            sentences_data, 1
        ):
            if is_paragraph_start:
                paragraph_number += 1
                sentence_number_in_paragraph = 1
            else:
                sentence_number_in_paragraph += 1

            Sentence.create(
                project_id=self.id,
                display_order=max_order + order_offset,
                text_oe=sentence_text,
                is_paragraph_start=is_paragraph_start,
                paragraph_number=paragraph_number,
                sentence_number_in_paragraph=sentence_number_in_paragraph,
            )

        session.commit()
        logger.info(
            "project.append_oe_text",
            project_id=self.id,
            sentences_added=len(sentences_data),
            paragraphs_added=paragraph_number - start_paragraph,
        )

    def to_json(self) -> dict:
        """
        Serialize project to JSON-compatible dictionary (without PKs).

        Returns:
            Dictionary containing project data

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)
        logger.info(
            "project.to_json",
            project_id=self.id,
            project_name=self.name,
            sentences_count=len(self.sentences),
        )
        return {
            "name": self.name,
            "source": self.source,
            "translator": self.translator,
            "notes": self.notes,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

    @classmethod
    def from_json(
        cls,
        project_data: dict,
        resolved_name: str,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Project:
        """
        Create a project from JSON import data.

        Args:
            session: SQLAlchemy session
            project_data: Project data dictionary from JSON
            resolved_name: Resolved project name (after collision handling)

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Created Project entity

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(cls.__name__)

        project = cls(
            name=resolved_name,
            source=project_data.get("source"),
            translator=project_data.get("translator"),
            notes=project_data.get("notes"),
        )
        created_at = from_utc_iso(project_data.get("created_at"))
        if created_at:
            project.created_at = created_at
        updated_at = from_utc_iso(project_data.get("updated_at"))
        if updated_at:
            project.updated_at = updated_at
        project.save(commit=commit)
        logger.info(
            "project.from_json",
            name=project.name,
            source=project.source,
            translator=project.translator,
            notes=project.notes,
        )
        return project

    def save(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Save the project.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        super().save(commit=commit)
        if commit:
            logger.info(
                "project.saved",
                project_id=self.id,
                project_name=self.name,
                sentences_count=len(self.sentences),
            )

    def delete(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Delete the project.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)
        super().delete(commit=commit)
        if commit:
            logger.info(
                "project.deleted",
                project_id=self.id,
                project_name=self.name,
            )

    @classmethod
    def split_sentences(  # noqa: PLR0912, PLR0915
        cls, text: str
    ) -> builtins.list[tuple[str, bool]]:
        """
        Split text into sentences and detect paragraph breaks.

        Args:
            text: Input Old English text

        Returns:
            List of tuples (sentence_text, is_paragraph_start) where is_paragraph_start
            indicates if the sentence starts a new paragraph (detected by blank lines)

        """
        if not text.strip():
            return []

        sentences: list[tuple[str, bool]] = []
        current_sentence = ""
        i = 0
        inside_quotes = False
        quote_char = None
        last_sentence_end_pos = -1  # Track where last sentence ended

        while i < len(text):
            char = text[i]

            # Track quote state
            if char in ('"', "'"):
                if not inside_quotes:
                    # Opening quote
                    inside_quotes = True
                    quote_char = char
                    current_sentence += char
                elif char == quote_char:
                    # Closing quote
                    inside_quotes = False
                    quote_char = None
                    current_sentence += char
                    # Check if we should split after closing quote
                    # Split if the quote contains sentence-ending punctuation (.!?)
                    # before the closing quote
                    # Check if the character immediately before the closing quote is
                    # sentence-ending punctuation
                    min_length_for_preceding_char = 2
                    char_before_closing_quote = None
                    if len(current_sentence) >= min_length_for_preceding_char:
                        # Look at the character before the closing quote
                        char_before_closing_quote = current_sentence[-2]

                    j = i + 1
                    # Skip whitespace
                    while j < len(text) and text[j].isspace():
                        j += 1

                    # Split if:
                    # 1. Quote contains sentence-ending punctuation (.!?) before
                    #    closing quote AND followed by uppercase letter
                    # 2. Or followed by [number] marker (always split on these)
                    should_split_after_quote = False
                    if j < len(text):
                        if (
                            text[j] == "["
                            and j + 1 < len(text)
                            and text[j + 1].isdigit()
                        ) or (
                            char_before_closing_quote in (".", "!", "?")
                            and text[j].isupper()
                        ):
                            should_split_after_quote = True

                    if should_split_after_quote:
                        # End of sentence - save it
                        sentence = current_sentence.strip()
                        if sentence:
                            # Check for paragraph break (blank lines before this
                            # sentence)
                            is_paragraph_start = cls._has_paragraph_break(
                                text, last_sentence_end_pos, i + 1
                            )
                            sentences.append((sentence, is_paragraph_start))
                            last_sentence_end_pos = i + 1
                        current_sentence = ""
                        # Skip the whitespace we looked ahead
                        i = j - 1
                else:
                    # Different quote type inside quotes - treat as regular char
                    current_sentence += char
            elif char in (".", "!", "?"):
                current_sentence += char
                # Only split if we're not inside quotes
                if not inside_quotes:
                    # Check if this is followed by whitespace or end of text
                    # Look ahead to see if there's content after optional whitespace
                    j = i + 1
                    # Skip whitespace
                    while j < len(text) and text[j].isspace():
                        j += 1
                    # Split if: end of text, uppercase (new sentence),
                    # quote (new quoted sentence), or [ followed by digit (like [1])
                    # Don't split if lowercase (likely abbreviation)
                    should_split = (
                        j >= len(text)
                        or text[j].isupper()
                        or text[j] in ('"', "'")
                        or (
                            text[j] == "["
                            and j + 1 < len(text)
                            and text[j + 1].isdigit()
                        )
                    )

                    if should_split:
                        # End of sentence - save it
                        sentence = current_sentence.strip()
                        if sentence:
                            # Check for paragraph break (blank lines before this
                            # sentence)
                            is_paragraph_start = cls._has_paragraph_break(
                                text, last_sentence_end_pos, i + 1
                            )
                            sentences.append((sentence, is_paragraph_start))
                            last_sentence_end_pos = i + 1
                        current_sentence = ""
                        # Skip the whitespace we looked ahead
                        i = j - 1
            elif char == "[" and i + 1 < len(text) and text[i + 1].isdigit():
                # Handle [number] markers - skip the entire marker
                # Find the closing ]
                j = i + 1
                while j < len(text) and text[j].isdigit():
                    j += 1
                if j < len(text) and text[j] == "]":
                    # Skip the entire [number] marker
                    i = j  # Will be incremented at end of loop
                else:
                    # Not a valid [number] marker, treat as regular char
                    current_sentence += char
            else:
                current_sentence += char

            i += 1

        # Add the last sentence if there's any content
        if current_sentence.strip():
            # Check for paragraph break before last sentence
            is_paragraph_start = cls._has_paragraph_break(
                text, last_sentence_end_pos, len(text)
            )
            sentences.append((current_sentence.strip(), is_paragraph_start))

        # Process sentences: remove [numbers] markers and filter empty strings
        result: list[tuple[str, bool]] = []
        for sentence_text, is_para_start in sentences:
            # Remove any [numbers] from the sentence
            cleaned = re.sub(r"\[\d+\]", "", sentence_text)
            # Also remove any remaining number] patterns
            cleaned = re.sub(r"^\d+\]\s*", "", cleaned)
            # Skip if sentence is just a number in [brackets] or empty
            if cleaned.strip() and not re.match(r"^\[\d+\]\s*$", cleaned.strip()):
                result.append((cleaned.strip(), is_para_start))

        # First sentence always starts a paragraph
        if result:
            result[0] = (result[0][0], True)

        return result

    @classmethod
    def _has_paragraph_break(cls, text: str, start_pos: int, end_pos: int) -> bool:
        """
        Check if there are blank lines (two or more consecutive newlines)
        between positions.

        Args:
            text: Full text
            start_pos: Start position to check from
            end_pos: End position to check to

        Returns:
            True if there are blank lines (paragraph break), False otherwise

        """
        if start_pos < 0 or start_pos >= len(text):
            # This is the first sentence
            return True

        # Extract the whitespace between sentences
        whitespace = text[start_pos:end_pos]
        # Check for two or more consecutive newlines
        newline_count = 0
        for char in whitespace:
            if char == "\n":
                newline_count += 1
                if newline_count >= 2:  # noqa: PLR2004
                    return True
            elif char not in (" ", "\t", "\r"):
                # Non-whitespace character resets the count
                newline_count = 0

        return False

    def total_token_count(self) -> int:
        """
        Get the total number of tokens in the project.

        Args:
            text: Old English text to process and add to the project

        Returns:
            Total number of tokens in the project

        """
        session = self._get_session()
        return (
            session.scalar(
                select(func.count(Token.id))
                .select_from(Token)
                .join(Sentence)
                .where(Sentence.project_id == self.id)
            )
            or 0
        )


@event.listens_for(Session, "before_flush")
def touch_project_on_change(session, flush_context, instances):  # noqa: ARG001, PLR0912
    """
    Update Project.updated_at whenever a related entity is changed.
    """
    projects_to_touch = set()

    # Check new, dirty (modified), and deleted objects
    for obj in session.new | session.dirty | session.deleted:
        if isinstance(obj, Project):
            continue

        classname = obj.__class__.__name__
        if classname not in ("Sentence", "Token", "Annotation", "Note"):
            continue

        project = None
        try:
            if classname == "Sentence":
                project = obj.project
                if not project and obj.project_id:
                    project = session.get(Project, obj.project_id)
            elif classname == "Token" or classname == "Note":
                sentence = obj.sentence
                if not sentence and obj.sentence_id:
                    from .sentence import Sentence  # noqa: PLC0415

                    sentence = session.get(Sentence, obj.sentence_id)
                if sentence:
                    project = sentence.project
            elif classname == "Annotation":
                token = obj.token
                if not token and obj.token_id:
                    from .token import Token  # noqa: PLC0415

                    token = session.get(Token, obj.token_id)
                if token:
                    sentence = token.sentence
                    if not sentence and token.sentence_id:
                        from .sentence import Sentence  # noqa: PLC0415

                        sentence = session.get(Sentence, token.sentence_id)
                    if sentence:
                        project = sentence.project
        except Exception:  # noqa: BLE001
            # If relationship is not accessible, skip
            continue

        if project and project not in session.deleted:
            projects_to_touch.add(project)

    for project in projects_to_touch:
        project.updated_at = datetime.now(UTC).replace(tzinfo=None)
