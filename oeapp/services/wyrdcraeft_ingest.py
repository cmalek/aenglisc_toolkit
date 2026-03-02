"""Map wyrdcraeft canonical models into Ænglisc Toolkit project models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

from sqlalchemy import func, select
from wyrdcraeft import DocumentIngestor
from wyrdcraeft.models import Line as WyrdLine
from wyrdcraeft.models import OldEnglishText, TextMetadata
from wyrdcraeft.models import Paragraph as WyrdParagraph
from wyrdcraeft.models import Section as WyrdSection
from wyrdcraeft.models import Sentence as WyrdSentence

from oeapp.exc import AlreadyExists
from oeapp.models.chapter import Chapter
from oeapp.models.mixins import SessionMixin
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence


@dataclass(slots=True)
class CanonicalRun:
    """Contiguous canonical prose or verse run."""

    #: The kind of run: verse or prose.
    kind: Literal["prose", "verse"]
    #: The paragraphs in the run.
    paragraphs: list[list[WyrdSentence]] = field(default_factory=list)
    #: The lines in the run.
    lines: list[WyrdLine] = field(default_factory=list)
    #: The title of the run.
    title: str | None = None
    #: Whether the title is official, or auto-generated.
    title_official: bool = False


@dataclass(slots=True)
class VerseStanza:
    """Five-line stanza with durable line span."""

    #: The text of the verse stanza.
    text: str
    #: The start line number of the stanza.
    line_start: int | None = None
    #: The end line number of the stanza.
    line_end: int | None = None


class WyrdcraeftIngestService(SessionMixin):
    """
    Import/append Old English text via wyrdcraeft typed canonical models.
    """

    #: The number of lines in a verse stanza.
    STANZA_LINES = 5
    #: The number of stanzas per section.
    STANZAS_PER_SECTION = 20
    #: The number of words in the auto-generated title suffix.
    AUTO_TITLE_WORDS = 5
    #: The auto-generated title suffix.
    AUTO_TITLE_SUFFIX = " ...."

    def __init__(self) -> None:
        """
        Initialize the ingest service.
        """
        self.session = self._get_session()
        self._ingestor = DocumentIngestor()

    def create_project(  # noqa: PLR0913
        self,
        *,
        name: str,
        source: str | None = None,
        translator: str | None = None,
        notes: str | None = None,
        text: str | None = None,
        source_path: Path | None = None,
    ) -> Project:
        """
        Create a project and populate hierarchy using wyrdcraeft ingestion.

        Args:
            name: Project name.

        Keyword Args:
            source: Bibliographic/source metadata.
            translator: Translator/editor metadata.
            notes: Project notes.
            text: Raw pasted input text.
            source_path: Path to source file for ingestion.

        Raises:
            AlreadyExists: If a project with ``name`` already exists.
            ValueError: If no source text/path is provided.

        Returns:
            The created project.

        """
        if Project.exists(name):
            raise AlreadyExists("Project", name)  # noqa: EM101

        project = Project(name=name, source=source, translator=translator, notes=notes)
        self.session.add(project)
        self.session.flush()

        canonical = self._ingest(
            text=text,
            source_path=source_path,
            metadata=self._build_metadata(
                title=name,
                source=source,
                editor=translator,
            ),
        )
        self._map_canonical_to_project(
            project=project,
            canonical=canonical,
            chapter_start=1,
            sentence_start=1,
        )
        self.session.commit()
        self.session.refresh(project)
        return project

    def append_to_project(
        self,
        *,
        project: Project,
        text: str | None = None,
        source_path: Path | None = None,
    ) -> None:
        """
        Append ingested content into an existing project.

        Args:
            project: Existing project to append to.

        Keyword Args:
            text: Raw pasted input text.
            source_path: Path to source file for ingestion.

        Raises:
            ValueError: If no source text/path is provided.

        Returns:
            ``None``.

        """
        canonical = self._ingest(
            text=text,
            source_path=source_path,
            metadata=self._build_metadata(
                title=project.name,
                source=project.source,
                editor=project.translator,
            ),
        )
        chapter_start = (project.last_chapter_number() or 0) + 1
        sentence_start = (
            self.session.scalar(
                select(func.max(Sentence.display_order)).where(
                    Sentence.project_id == project.id
                )
            )
            or 0
        ) + 1

        self._map_canonical_to_project(
            project=project,
            canonical=canonical,
            chapter_start=chapter_start,
            sentence_start=sentence_start,
        )
        self.session.commit()

    def _build_metadata(
        self,
        *,
        title: str,
        source: str | None,
        editor: str | None,
    ) -> TextMetadata:
        """
        Build lightweight ingestion metadata.

        Args:
            title: Text title.
            source: Source label.
            editor: Translator/editor.

        Returns:
            Metadata for ``DocumentIngestor``.

        """
        return TextMetadata(
            title=title,
            author="",
            source=source or "",
            year="",
            language="Old English",
            editor=editor or "",
            license="",
        )

    def _ingest(
        self,
        *,
        text: str | None,
        source_path: Path | None,
        metadata: TextMetadata | None,
    ) -> OldEnglishText:
        """
        Ingest text into wyrdcraeft canonical models.

        Args:
            text: Raw pasted text.
            source_path: File path for ingestion.
            metadata: Canonical metadata.

        Raises:
            ValueError: If neither ``text`` nor ``source_path`` is provided.

        Returns:
            Typed canonical :class:`wyrdcraeft.models.OldEnglishText`.

        """
        if source_path is not None:
            return self._ingestor.ingest(source_path=source_path, metadata=metadata)

        if text is None or not text.strip():
            msg = "Please enter or import Old English text."
            raise ValueError(msg)

        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".txt",
                delete=False,
            ) as handle:
                handle.write(text)
                temp_path = Path(handle.name)
            return self._ingestor.ingest(source_path=temp_path, metadata=metadata)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _map_canonical_to_project(
        self,
        *,
        project: Project,
        canonical: OldEnglishText,
        chapter_start: int,
        sentence_start: int,
    ) -> None:
        """
        Map canonical content into app hierarchy models.

        Args:
            project: Target project.
            canonical: Canonical text from wyrdcraeft ingestion.
            chapter_start: Initial chapter number for this ingest batch.
            sentence_start: Initial sentence display order for this ingest batch.

        Returns:
            ``None``.

        """
        runs = self._flatten_runs(canonical.content)
        if not runs:
            return

        chapter_number = chapter_start
        display_order = sentence_start
        for run in runs:
            if run.kind == "verse":
                chapter = Chapter.create(
                    project_id=project.id,
                    number=chapter_number,
                    title=self._chapter_title_for_verse(run),
                    title_auto=not run.title_official,
                    commit=False,
                )
                display_order = self._create_verse_hierarchy(
                    run=run,
                    chapter=chapter,
                    display_order_start=display_order,
                    project_id=project.id,
                )
            else:
                chapter_title, title_auto = self._chapter_title_for_prose(run)
                chapter = Chapter.create(
                    project_id=project.id,
                    number=chapter_number,
                    title=chapter_title,
                    title_auto=title_auto,
                    commit=False,
                )
                display_order = self._create_prose_hierarchy(
                    run=run,
                    chapter=chapter,
                    display_order_start=display_order,
                    project_id=project.id,
                )
            chapter_number += 1

    def _flatten_runs(self, content: WyrdSection) -> list[CanonicalRun]:
        """
        Flatten canonical section tree into contiguous prose/verse runs.

        Args:
            content: Root canonical section.

        Returns:
            Ordered prose/verse runs.

        """
        runs: list[CanonicalRun] = []
        self._collect_runs(
            section=content,
            runs=runs,
            force_boundary=False,
            inherited_title=None,
        )
        return runs

    def _collect_runs(
        self,
        *,
        section: WyrdSection,
        runs: list[CanonicalRun],
        force_boundary: bool,
        inherited_title: str | None,
    ) -> None:
        """
        Recursively collect canonical prose/verse runs.

        Args:
            section: Current section node.
            runs: Mutable run accumulator.
            force_boundary: Whether this section starts a new run.
            inherited_title: Parent-provided official title.

        Returns:
            ``None``.

        """
        section_has_boundary = bool(section.title or section.number is not None)
        next_boundary = force_boundary or section_has_boundary
        effective_title = section.title or inherited_title
        effective_official = bool(section.title or inherited_title)

        if section.paragraphs:
            paragraphs = self._normalize_paragraphs(section.paragraphs)
            if paragraphs:
                self._append_run(
                    runs=runs,
                    run=CanonicalRun(
                        kind="prose",
                        paragraphs=paragraphs,
                        title=effective_title,
                        title_official=effective_official,
                    ),
                    force_boundary=next_boundary,
                )

        if section.lines:
            lines = [line for line in section.lines if line.text and line.text.strip()]
            if lines:
                self._append_run(
                    runs=runs,
                    run=CanonicalRun(
                        kind="verse",
                        lines=lines,
                        title=effective_title,
                        title_official=effective_official,
                    ),
                    force_boundary=next_boundary,
                )

        if section.sections:
            child_inherited_title = section.title or inherited_title
            for child in section.sections:
                self._collect_runs(
                    section=child,
                    runs=runs,
                    force_boundary=next_boundary,
                    inherited_title=child_inherited_title,
                )
                child_inherited_title = None

    def _append_run(
        self,
        *,
        runs: list[CanonicalRun],
        run: CanonicalRun,
        force_boundary: bool,
    ) -> None:
        """
        Append run or merge into previous compatible run.

        Args:
            runs: Mutable run accumulator.
            run: Run to append.
            force_boundary: Whether this run must begin a new segment.

        Returns:
            ``None``.

        """
        if (
            runs
            and not force_boundary
            and runs[-1].kind == run.kind
            and not run.title_official
        ):
            current = runs[-1]
            if run.kind == "prose":
                current.paragraphs.extend(run.paragraphs)
            else:
                current.lines.extend(run.lines)
            if current.title is None and run.title:
                current.title = run.title
                current.title_official = run.title_official
            return

        runs.append(run)

    def _normalize_paragraphs(
        self, paragraphs: list[WyrdParagraph]
    ) -> list[list[WyrdSentence]]:
        """
        Filter canonical paragraph list down to non-empty sentence groups.

        Args:
            paragraphs: Canonical paragraph list.

        Returns:
            Normalized paragraph sentence groups.

        """
        normalized: list[list[WyrdSentence]] = []
        for paragraph in paragraphs:
            sentences = [s for s in paragraph.sentences if s.text and s.text.strip()]
            if sentences:
                normalized.append(sentences)
        return normalized

    def _chapter_title_for_prose(self, run: CanonicalRun) -> tuple[str, bool]:
        """
        Resolve prose chapter title and auto-title flag.

        Args:
            run: Prose canonical run.

        Returns:
            Tuple of ``(title, title_auto)``.

        """
        if run.title and run.title_official:
            return run.title, False
        return self._auto_title_from_run(run), True

    def _chapter_title_for_verse(self, run: CanonicalRun) -> str | None:
        """
        Resolve verse chapter title.

        Args:
            run: Verse canonical run.

        Returns:
            Official title when present, otherwise ``None``.

        """
        return run.title if run.title_official else None

    def _auto_title_from_run(self, run: CanonicalRun) -> str:
        """
        Build auto-generated prose chapter title from first 5 words.

        Args:
            run: Prose canonical run.

        Returns:
            Auto title suffixed with `` ....``.

        """
        if not run.paragraphs or not run.paragraphs[0]:
            return f"Untitled{self.AUTO_TITLE_SUFFIX}"
        first_text = run.paragraphs[0][0].text
        words = re.findall(r"\S+", first_text)
        snippet = " ".join(words[: self.AUTO_TITLE_WORDS]).strip()
        if not snippet:
            snippet = "Untitled"
        return f"{snippet}{self.AUTO_TITLE_SUFFIX}"

    def _create_prose_hierarchy(
        self,
        *,
        run: CanonicalRun,
        chapter: Chapter,
        display_order_start: int,
        project_id: int,
    ) -> int:
        """
        Create chapter/section/paragraph/sentence rows for a prose run.

        Args:
            run: Prose canonical run.
            chapter: Target chapter row.
            display_order_start: Starting global sentence order.
            project_id: Project ID.

        Returns:
            Next display order after insertion.

        """
        section = Section.create(
            chapter_id=chapter.id,
            number=1,
            title=None,
            title_auto=False,
            commit=False,
        )
        display_order = display_order_start
        paragraph_order = 1
        for paragraph_sentences in run.paragraphs:
            paragraph = Paragraph(section_id=section.id, order=paragraph_order)
            self.session.add(paragraph)
            self.session.flush()
            paragraph_order += 1

            for canonical_sentence in paragraph_sentences:
                Sentence.create(
                    project_id=project_id,
                    display_order=display_order,
                    text_oe=canonical_sentence.text.strip(),
                    paragraph_id=paragraph.id,
                    verse_line_start=None,
                    verse_line_end=None,
                    commit=False,
                )
                display_order += 1
        return display_order

    def _create_verse_hierarchy(
        self,
        *,
        run: CanonicalRun,
        chapter: Chapter,
        display_order_start: int,
        project_id: int,
    ) -> int:
        """
        Create chapter/section/paragraph/sentence rows for a verse run.

        Args:
            run: Verse canonical run.
            chapter: Target chapter row.
            display_order_start: Starting global sentence order.
            project_id: Project ID.

        Returns:
            Next display order after insertion.

        """
        stanzas = self._build_stanzas(run.lines)
        if not stanzas:
            return display_order_start

        display_order = display_order_start
        section_number = 1
        for offset in range(0, len(stanzas), self.STANZAS_PER_SECTION):
            section_stanzas = stanzas[offset : offset + self.STANZAS_PER_SECTION]
            section_title = (
                f"Lines {section_stanzas[0].line_start}-{section_stanzas[-1].line_end}"
            )
            section = Section.create(
                chapter_id=chapter.id,
                number=section_number,
                title=section_title,
                title_auto=True,
                commit=False,
            )
            section_number += 1

            for paragraph_order, stanza in enumerate(section_stanzas, 1):
                paragraph = Paragraph(section_id=section.id, order=paragraph_order)
                self.session.add(paragraph)
                self.session.flush()

                Sentence.create(
                    project_id=project_id,
                    display_order=display_order,
                    text_oe=stanza.text,
                    paragraph_id=paragraph.id,
                    verse_line_start=stanza.line_start,
                    verse_line_end=stanza.line_end,
                    commit=False,
                )
                display_order += 1
        return display_order

    def _build_stanzas(self, lines: list[WyrdLine]) -> list[VerseStanza]:
        """
        Group verse lines into fixed 5-line stanzas.

        Args:
            lines: Ordered canonical verse lines.

        Returns:
            Stanza list with line spans.

        """
        stanzas: list[VerseStanza] = []
        for offset in range(0, len(lines), self.STANZA_LINES):
            stanza_lines = lines[offset : offset + self.STANZA_LINES]
            if not stanza_lines:
                continue
            start_num = self._line_number(stanza_lines[0], fallback_index=offset)
            end_num = self._line_number(
                stanza_lines[-1],
                fallback_index=offset + len(stanza_lines) - 1,
            )
            stanza_text = "\n".join(line.text.rstrip("\n") for line in stanza_lines)
            stanzas.append(
                VerseStanza(
                    text=stanza_text,
                    line_start=start_num,
                    line_end=end_num,
                )
            )
        return stanzas

    def _line_number(self, line: WyrdLine, *, fallback_index: int) -> int:
        """
        Resolve canonical line number with deterministic fallback.

        Args:
            line: Canonical line model.
            fallback_index: Zero-based index fallback when number is missing.

        Returns:
            Resolved 1-based line number.

        """
        if line.number is not None:
            try:
                value = int(line.number)
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass
        return fallback_index + 1
