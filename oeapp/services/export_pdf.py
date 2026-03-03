"""PDF export service for Full Translation window."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

from oeapp.mixins import AnnotationTextualMixin
from oeapp.models.project import Project
from oeapp.services.logs import get_logger
from oeapp.services.pdf_engine import PDFEngineError, compile_latex_with_tectonic
from oeapp.utils import normalize_old_english

if TYPE_CHECKING:
    import subprocess

    from oeapp.models.annotation import Annotation
    from oeapp.models.note import Note
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


@dataclass
class GlossaryEntry:
    """Aggregated glossary entry for a unique ``(root, pos)`` key."""

    #: The root word of the glossary entry.
    root: str
    #: The normalized root used for deduping forms.
    normalized_root: str
    #: The part of speech of the glossary entry.
    pos: str
    #: The classification of the glossary entry.
    classification: str
    #: The prep case of the glossary entry.
    prep_case: str | None = None
    #: The sort key of the glossary entry.
    sort_key: tuple[int, ...] = field(default_factory=tuple)
    #: The genders used in the glossary entry.
    used_genders: set[str] = field(default_factory=set)
    #: The cases used in the glossary entry.  Used to ensure that all the
    #: we only list a single instance of each case.
    used_cases: set[str] = field(default_factory=set)
    #: The modern English meanings of the glossary entry.
    meanings: list[str] = field(default_factory=list)
    #: The attested forms of the glossary entry from the text.
    examples: list[tuple[str, str, str | None]] = field(default_factory=list)
    #: Other root spellings that normalize to the same root.
    root_variants: list[str] = field(default_factory=list)
    #: Verb class label for verb entries.
    verb_class_label: str | None = None
    #: Verb direct object case for verb entries.
    verb_direct_object_case: str | None = None
    #: Whether any entry requires an infinitive complement.
    verb_requires_infinitive: bool = False
    #: Whether any entry is impersonal.
    verb_impersonal: bool = False
    #: Whether any entry is intransitive.
    verb_intransitive: bool = False


class FullTranslationPDFExporter(AnnotationTextualMixin):
    """Exports the full translation view as a LaTeX-driven PDF document."""

    #: A lookup map for part of speech codes to their long form, for
    #: the glossary legend.
    POS_LEGEND_MAP: Final[dict[str, str]] = {
        "N": "noun",
        "V": "verb",
        "A": "adjective",
        "R": "pronoun",
        "D": "determiner",
        "B": "adverb",
        "C": "conjunction",
        "E": "preposition",
        "I": "interjection",
        "L": "numeral",
    }
    #: A lookup map for gender codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    GENDER_LEGEND_MAP: Final[dict[str, str]] = {
        "m": "masculine",
        "f": "feminine",
        "n": "neuter",
    }
    #: A lookup map for case codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    CASE_LEGEND_MAP: Final[dict[str, str]] = {
        "n": "nominative",
        "a": "accusative",
        "g": "genitive",
        "d": "dative",
        "i": "instrumental",
    }
    #: A lookup map for case codes to their short form, for
    #: the glossary legend.  This is yet another mapping, I know.
    CASE_CODE_TO_SHORT_MAP: Final[dict[str, str]] = {
        "n": "nom",
        "a": "acc",
        "g": "gen",
        "d": "dat",
        "i": "inst",
    }
    #: A lookup map for verb tense codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    VERB_TENSE_LEGEND_MAP: Final[dict[str, str]] = {
        "pa": "past",
        "pr": "present",
    }
    #: A lookup map for verb mood codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    VERB_MOOD_LEGEND_MAP: Final[dict[str, str]] = {
        "i": "indicative",
        "s": "subjunctive",
        "imp": "imperative",
    }
    #: A lookup map for number codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    NUMBER_LEGEND_MAP: Final[dict[str, str]] = {
        "s": "singular",
        "pl": "plural",
    }
    #: A lookup map for verb person codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    VERB_PERSON_LEGEND_MAP: Final[dict[str, str]] = {
        "1": "1st person",
        "2": "2nd person",
        "3": "3rd person",
    }
    #: A lookup map for verb form codes to their long form, for
    #: the glossary legend.  This is yet another mapping, I know.
    VERB_FORM_LEGEND_MAP: Final[dict[str, str]] = {
        "f": "finite",
        "i": "infinitive",
        "p": "participle",
        "ii": "inflected infinitive",
    }
    #: The order of OE alphabet characters, for sorting glossary entries.
    #: Sorting by normal alphabetical order is not sufficient because
    #: æ, þ, ð, ġ and ċ are not handled correctly by the default sorting.
    _OE_ALPHA_ORDER: Final[dict[str, int]] = {
        "a": 0,
        "æ": 1,
        "b": 2,
        "c": 3,
        "d": 4,
        "e": 5,
        "f": 6,
        "g": 7,
        "h": 8,
        "i": 9,
        "j": 10,
        "k": 11,
        "l": 12,
        "m": 13,
        "n": 14,
        "o": 15,
        "p": 16,
        "r": 17,
        "s": 18,
        "t": 19,
        "þ": 20,
        "u": 21,
        "v": 22,
        "w": 23,
        "x": 24,
        "y": 25,
        "z": 26,
    }
    #: The order of parts of speech, for rendering the glossary legend.
    _POS_ORDER: Final[list[str]] = ["N", "V", "A", "R", "D", "B", "C", "E", "I", "L"]
    #: Fixed four-space verse indent expressed in em width.
    _VERSE_INDENT_EM: Final[float] = 2.40

    def __init__(self) -> None:
        #: The logger instance.
        self.logger = get_logger(__name__)
        #: The last error message.
        self.last_error: str | None = None

    def export_side_by_side_pdf(self, project_id: int, output_path: Path) -> bool:  # noqa: PLR0911
        """
        Export project text as PDF using bundled Tectonic.

        Args:
            project_id: The ID of the project to export.
            output_path: The path to the output PDF file.

        Returns:
            ``True`` on success, ``False`` on failure.

        """
        self.last_error = None
        project = Project.get(project_id)
        if project is None:
            self.last_error = f"Project not found: {project_id}"
            self.logger.error(
                "pdf_export.failed",
                project_id=project_id,
                reason=self.last_error,
            )
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.last_error = f"Cannot create output directory: {exc!s}"
            self.logger.exception(
                "pdf_export.failed",
                project_id=project_id,
                output_path=str(output_path),
                reason=self.last_error,
            )
            return False

        try:
            with TemporaryDirectory(prefix="aenglisc-pdf-") as tmp_dir:
                work_dir = Path(tmp_dir)
                tex_path = work_dir / "full_translation.tex"
                pdf_path = work_dir / "full_translation.pdf"

                tex_path.write_text(self._build_document_tex(project), encoding="utf-8")

                try:
                    result = compile_latex_with_tectonic(tex_path, work_dir)
                except PDFEngineError as exc:
                    artifacts = self._copy_debug_artifacts(
                        work_dir=work_dir,
                        output_path=output_path,
                        compile_result=None,
                    )
                    self.last_error = f"Failed to run PDF engine: {exc!s}"
                    self.logger.exception(
                        "pdf_export.failed",
                        project_id=project_id,
                        output_path=str(output_path),
                        reason=self.last_error,
                        artifacts=[str(path) for path in artifacts],
                    )
                    return False
                except Exception as exc:  # pragma: no cover - safety net
                    artifacts = self._copy_debug_artifacts(
                        work_dir=work_dir,
                        output_path=output_path,
                        compile_result=None,
                    )
                    self.last_error = f"Failed to run PDF engine: {exc!s}"
                    self.logger.exception(
                        "pdf_export.failed",
                        project_id=project_id,
                        output_path=str(output_path),
                        reason=self.last_error,
                        artifacts=[str(path) for path in artifacts],
                    )
                    return False

                if result.returncode != 0 or not pdf_path.exists():
                    artifacts = self._copy_debug_artifacts(
                        work_dir=work_dir,
                        output_path=output_path,
                        compile_result=result,
                    )
                    stderr = (result.stderr or "").strip()
                    stdout = (result.stdout or "").strip()
                    output_preview = stderr or stdout or "Unknown compile error"
                    first_line = output_preview.splitlines()[0]
                    self.last_error = (
                        f"LaTeX compilation failed (exit {result.returncode}): "
                        f"{first_line}"
                    )
                    self.logger.error(
                        "pdf_export.failed",
                        project_id=project_id,
                        output_path=str(output_path),
                        returncode=result.returncode,
                        stderr=stderr,
                        stdout=stdout,
                        reason=self.last_error,
                        artifacts=[str(path) for path in artifacts],
                    )
                    return False

                try:
                    shutil.copy2(pdf_path, output_path)
                except OSError as exc:
                    self.last_error = f"Unable to write PDF file: {exc!s}"
                    self.logger.exception(
                        "pdf_export.failed",
                        project_id=project_id,
                        output_path=str(output_path),
                        reason=self.last_error,
                    )
                    return False
        except Exception as exc:  # pragma: no cover - safety net
            self.last_error = f"Unexpected PDF export error: {exc!s}"
            self.logger.exception(
                "pdf_export.failed",
                project_id=project_id,
                output_path=str(output_path),
                reason=self.last_error,
            )
            return False

        self.logger.info(
            "pdf_export.success",
            project_id=project_id,
            output_path=str(output_path),
        )
        return True

    def _copy_debug_artifacts(
        self,
        work_dir: Path,
        output_path: Path,
        compile_result: subprocess.CompletedProcess[str] | None,
    ) -> list[Path]:
        """
        Copy ``.tex``/``.log`` artifacts near the destination for debugging.

        Args:
            work_dir: The directory containing the work files.
            output_path: The path to the output PDF file.
            compile_result: The result of the PDF engine compilation.

        Returns:
            A list of paths to the copied files.

        """
        debug_base = output_path.with_suffix("")
        artifact_map = {
            work_dir / "full_translation.tex": debug_base.with_suffix(".tex"),
            work_dir / "full_translation.log": debug_base.with_suffix(".log"),
        }
        copied: list[Path] = []
        for src, dst in artifact_map.items():
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                    copied.append(dst)
                except OSError:
                    continue

        if compile_result and compile_result.stderr:
            stderr_path = debug_base.with_suffix(".stderr.txt")
            try:
                stderr_path.write_text(compile_result.stderr, encoding="utf-8")
                copied.append(stderr_path)
            except OSError:
                pass
        return copied

    def _build_document_tex(self, project: Project) -> str:
        """
        Build complete LaTeX source for a project export.

        Args:
            project: The project to export.

        Returns:
            The complete LaTeX source for the project export.

        """
        header_lines: list[str] = [
            r"\section*{Translation: " + self._latex_escape(project.name) + "}"
        ]
        if project.source:
            header_lines.append(
                r"\noindent\textbf{Source:} "
                + self._latex_escape(project.source)
                + r"\par"
            )
        if project.translator:
            header_lines.append(
                r"\noindent\textbf{Translator:} "
                + self._latex_escape(project.translator)
                + r"\par"
            )

        glossary_entries = self._build_glossary_entries(project)
        glossary_lines = self._render_glossary(glossary_entries)

        about_text = ""
        if project.notes:
            about_text = (
                r"\section*{About this text}"
                "\n" + r"\noindent " + self._latex_escape(project.notes) + r"\par"
                "\n" + self._horizontal_rule()
            )

        return (
            r"\documentclass[10pt]{article}"
            "\n"
            r"\usepackage[utf8]{inputenc}"
            "\n"
            r"\usepackage[T1]{fontenc}"
            "\n"
            r"\usepackage{lmodern}"
            "\n"
            r"\usepackage[landscape,margin=0.5in]{geometry}"
            "\n"
            r"\usepackage{paracol}"
            "\n"
            r"\usepackage{multicol}"
            "\n"
            r"\usepackage{needspace}"
            "\n"
            r"\usepackage[hidelinks]{hyperref}"
            "\n"
            r"\usepackage{xcolor}"
            "\n"
            r"\makeatletter"
            "\n"
            r"\@ifundefined{footnoteplacement}{}{\footnoteplacement{m}}"
            "\n"
            r"\@ifundefined{footnotelayout}{}{\footnotelayout{p}}"
            "\n"
            r"\makeatother"
            "\n"
            r"\renewcommand{\footnoterule}{\kern-3pt\noindent\rule{\dimexpr\textwidth\relax}{0.4pt}\kern2.6pt}"
            "\n"
            r"\setlength{\columnsep}{0.7in}"
            "\n"
            r"\setlength{\parindent}{0pt}"
            "\n"
            r"\setlength{\parskip}{0.45em}"
            "\n"
            r"\begin{document}"
            "\n"
            + "\n".join(header_lines)
            + "\n"
            + self._horizontal_rule()
            + self._render_two_columns(project)
            + "\n"
            + self._horizontal_rule()
            + about_text
            + "\n"
            + r"\clearpage"
            + "\n"
            + r"\section*{Glossary}"
            + "\n"
            + glossary_lines
            + "\n"
            + r"\end{document}"
            + "\n"
        )

    def _render_two_columns(self, project: Project) -> str:
        """
        Render OE + ModE into real parallel columns using the ``paracol`` LaTeX
        package.

        Args:
            project: The project to render.

        Returns:
            The rendered two-column text.

        """
        blocks = [r"\begin{paracol}{2}"]
        oe_parts: list[str] = []
        mode_parts: list[str] = []
        previous_sentence: Sentence | None = None

        for sentence in project.sentences:
            titles = self._visible_titles(previous_sentence, sentence)
            if titles:
                if oe_parts:
                    oe_parts.append(r"\par ")
                    mode_parts.append(r"\par ")
                for title in titles:
                    escaped_title = self._latex_escape(title)
                    oe_parts.append(r"\textbf{" + escaped_title + r"}\newline ")
                    mode_parts.append(r"\textbf{" + escaped_title + r"}\newline ")

            sep = self._separator(previous_sentence, sentence, has_titles=bool(titles))
            if sep:
                oe_parts.append(sep)
                mode_parts.append(sep)

            note_map = self._notes_by_end_token(sentence)
            oe_rendered = self._render_oe_sentence(sentence, note_map)
            mode_rendered = self._render_modern_sentence(
                sentence.text_modern or "[...]"
            )
            if sentence.is_verse:
                oe_rendered = self._indent_rendered_lines(oe_rendered)
                mode_rendered = self._indent_rendered_lines(mode_rendered)
            oe_parts.append(oe_rendered)
            mode_parts.append(mode_rendered)

            if sentence.is_verse and sentence.verse_line_end is not None:
                marker = self._latex_escape(str(sentence.verse_line_end))
                oe_parts.append(r"\newline \textbf{" + marker + r"}")
                mode_parts.append(r"\newline \textbf{" + marker + r"}")

            previous_sentence = sentence

        blocks.append(r"\noindent\raggedright " + "".join(oe_parts) + r"\par")
        blocks.append(r"\switchcolumn")
        blocks.append(r"\noindent\raggedright " + "".join(mode_parts) + r"\par")
        blocks.append(r"\end{paracol}")
        return "\n".join(blocks)

    def _indent_rendered_lines(self, rendered: str) -> str:
        """
        Indent each rendered line by four-space equivalent width.

        Args:
            rendered: Rendered LaTeX content.

        Returns:
            Indented LaTeX content.

        """
        if not rendered:
            return rendered
        indent = rf"\hspace*{{{self._VERSE_INDENT_EM:.2f}em}}"
        return indent + rendered.replace(r"\newline ", r"\newline " + indent)

    def _visible_titles(
        self, previous: Sentence | None, current: Sentence
    ) -> list[str]:
        """
        Resolve chapter/section titles that should be rendered at this boundary.

        Args:
            previous: Previous sentence in render order.
            current: Current sentence in render order.

        Returns:
            List of visible titles (official-only, auto titles suppressed).

        """
        titles: list[str] = []
        current_section = current.paragraph.section if current.paragraph else None
        current_chapter = current_section.chapter if current_section else None
        previous_section = (
            previous.paragraph.section if previous and previous.paragraph else None
        )
        previous_chapter = previous_section.chapter if previous_section else None

        chapter_changed = (
            current_chapter is not None
            and (previous_chapter is None or current_chapter.id != previous_chapter.id)
        )
        if (
            current_chapter is not None
            and chapter_changed
            and current_chapter.title
            and not current_chapter.title_auto
        ):
            titles.append(current_chapter.title)

        section_changed = (
            current_section is not None
            and (previous_section is None or current_section.id != previous_section.id)
        )
        if (
            current_section is not None
            and section_changed
            and current_section.title
            and not current_section.title_auto
        ):
            titles.append(current_section.title)
        return titles

    def _separator(
        self, previous: Sentence | None, current: Sentence, has_titles: bool
    ) -> str:
        """
        Return LaTeX separator between adjacent sentence render blocks.

        Args:
            previous: Previous sentence in render order.
            current: Current sentence.
            has_titles: Whether titles were rendered before ``current``.

        Returns:
            LaTeX separator string.

        """
        if previous is None or has_titles:
            return ""
        if current.is_verse:
            return r"\newline " if previous.is_verse else r"\par "
        if previous.is_verse:
            return r"\par "
        return r"\par " if self._is_paragraph_start(current) else " "

    def _group_sentences_by_paragraph(self, project: Project) -> list[list[Sentence]]:
        """
        Group ordered sentences by paragraph boundaries.

        Args:
            project: The project to export.

        Returns:
            A list of lists of sentences, grouped by paragraph.

        """
        paragraphs: list[list[Sentence]] = []
        current: list[Sentence] = []

        for sentence in project.sentences:
            if self._is_paragraph_start(sentence) and current:
                paragraphs.append(current)
                current = [sentence]
            else:
                current.append(sentence)

        if current:
            paragraphs.append(current)

        return paragraphs

    def _is_paragraph_start(self, sentence: Sentence) -> bool:
        """
        Return ``True`` if sentence is first in its paragraph.

        Args:
            sentence: The sentence to check.

        Returns:
            ``True`` if sentence is first in its paragraph, ``False`` otherwise.

        """
        if not sentence.paragraph:
            return False
        ordered = sorted(sentence.paragraph.sentences, key=lambda s: s.display_order)
        return bool(ordered and ordered[0].id == sentence.id)

    def _notes_by_end_token(self, sentence: Sentence) -> dict[int, list[Note]]:
        """
        Map sentence notes by end-token ID to render end-anchored footnotes.

        Args:
            sentence: The sentence to map notes for.

        Returns:
            A dictionary mapping end-token IDs to lists of notes.

        """
        note_map: dict[int, list[Note]] = {}
        for note in sentence.sorted_notes:
            if note.end_token:
                note_map.setdefault(note.end_token, []).append(note)
        return note_map

    def _render_oe_sentence(
        self, sentence: Sentence, note_map: dict[int, list[Note]]
    ) -> str:
        """
        Render OE sentence text while injecting LaTeX footnotes.

        Args:
            sentence: The sentence to render.
            note_map: A dictionary mapping end-token IDs to lists of notes.

        Returns:
            The rendered OE sentence text.

        """
        tokens, token_id_to_start = sentence.sorted_tokens
        text = sentence.text_oe
        last_pos = 0
        out_parts: list[str] = []
        at_line_start = True

        for token in tokens:
            token_start = token_id_to_start[token.id]
            if token_start > last_pos:
                rendered_gap, at_line_start = self._render_oe_text_segment(
                    text[last_pos:token_start],
                    at_line_start,
                )
                out_parts.append(rendered_gap)

            rendered_surface, at_line_start = self._render_oe_text_segment(
                token.surface,
                at_line_start,
            )
            out_parts.append(rendered_surface)
            for note in note_map.get(token.id, []):
                out_parts.append(self._render_footnote(sentence, note))  # noqa: PERF401

            last_pos = token_start + len(token.surface)

        if last_pos < len(text):
            rendered_tail, _at_line_start = self._render_oe_text_segment(
                text[last_pos:],
                at_line_start,
            )
            out_parts.append(rendered_tail)

        return "".join(out_parts)

    def _render_oe_text_segment(
        self,
        segment: str,
        at_line_start: bool,
    ) -> tuple[str, bool]:
        """
        Render OE text while preserving line alignment and half-line spacing.

        - Line starts preserve leading spaces for verse indentation.
        - Runs of interior spaces are expanded to explicit horizontal space.

        Args:
            segment: The text segment to render.
            at_line_start: Whether the segment is at the start of a line.

        Returns:
            A tuple containing the rendered text and whether the segment ends
            with a newline.

        """
        if not segment:
            return "", at_line_start

        out_parts: list[str] = []
        raw_lines = segment.split("\n")
        trailing_newline = segment.endswith("\n")
        for idx, raw_line in enumerate(raw_lines):
            if idx > 0:
                out_parts.append(r"\newline ")
                at_line_start = True

            out_parts.append(
                self._latex_escape_preserving_space_runs(
                    raw_line,
                    preserve_leading=at_line_start,
                )
            )
            at_line_start = False

        return "".join(out_parts), trailing_newline

    def _render_modern_sentence(self, text: str) -> str:
        """
        Render modern-English sentence text while preserving line indentation.

        Args:
            text: The text to render.

        Returns:
            The rendered modern-English sentence text.

        """
        out_parts: list[str] = []
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            if idx > 0:
                out_parts.append(r"\newline ")
            out_parts.append(
                self._latex_escape_preserving_space_runs(
                    line,
                    preserve_leading=True,
                )
            )
        return "".join(out_parts)

    def _latex_escape_preserving_space_runs(
        self, value: str, *, preserve_leading: bool = False
    ) -> str:
        """
        Escape text for LaTeX and preserve repeated interior spaces.

        Args:
            value: The text to escape.
            preserve_leading: Whether to preserve leading spaces.

        Returns:
            The escaped text.

        """
        escaped = self._latex_escape(value)
        leading_prefix = ""
        if preserve_leading:
            match = re.match(r" +", escaped)
            if match:
                leading_prefix = self._leading_space_hspace(len(match.group(0)))
                escaped = escaped[len(match.group(0)) :]
        escaped = re.sub(
            r"(?<=\S) {3,}(?=\S)",
            self._normalize_verse_gap,
            escaped,
        )
        escaped = re.sub(r" {2}", self._space_run_to_hspace, escaped)
        return leading_prefix + escaped

    def _leading_space_hspace(self, count: int) -> str:
        """
        Convert leading spaces to explicit LaTeX horizontal width.

        Args:
            count: The number of leading spaces to convert.

        Returns:
            The converted text.

        """
        width_em = f"{count * 0.6:.2f}"
        return rf"\hspace*{{{width_em}em}}"

    def _space_run_to_hspace(self, match: re.Match[str]) -> str:
        """
        Convert runs of spaces into one normal space + explicit width.

        Args:
            match: The match object.

        Returns:
            The converted text.

        """
        count = len(match.group(0))
        extra_spaces = count - 1
        width_em = f"{extra_spaces * 0.6:.2f}"
        return " " + rf"\hspace*{{{width_em}em}}"

    def _normalize_verse_gap(self, _match: re.Match[str]) -> str:
        """
        Normalize wide internal gaps to a fixed 4 space visual width.

        Args:
            _match: The match object.

        Returns:
            The converted text.

        """
        # One literal space + width for 9 additional spaces.
        return r" \hspace*{2.40em}"

    def _render_footnote(self, sentence: Sentence, note: Note) -> str:
        """
        Render a footnote body for a note.

        Args:
            sentence: The sentence to render the footnote for.
            note: The note to render the footnote for.

        Returns:
            The rendered footnote body.

        """
        token_text = self._get_note_token_text(note, sentence)
        note_body = self._latex_escape(note.note_text_md)
        if token_text:
            token_prefix = r"\emph{" + self._latex_escape(token_text) + r"} --- "
            note_body = token_prefix + note_body
        return r"\footnote{" + note_body + "}"

    def _get_note_token_text(self, note: Note, sentence: Sentence) -> str:
        """
        Return surface text for a note span.

        Args:
            note: The note to get the token text for.
            sentence: The sentence to get the token text for.

        Returns:
            The surface text for the note span.

        """
        if not note.start_token or not note.end_token:
            return ""

        start_token: Token | None = None
        end_token = None
        for token in sentence.tokens:
            if token.id == note.start_token:
                start_token = token
            if token.id == note.end_token:
                end_token = token
        if not start_token or not end_token:
            return ""

        tokens_in_range: list[str] = []
        in_range = False
        for token in sorted(sentence.tokens, key=lambda t: t.order_index):
            if token.id == start_token.id:
                in_range = True
            if in_range:
                tokens_in_range.append(token.surface)
            if token.id == end_token.id:
                break
        return " ".join(tokens_in_range)

    def _build_glossary_entries(self, project: Project) -> list[GlossaryEntry]:
        """
        Aggregate and sort glossary entries with Old English collation rules.

        Args:
            project: The project to build glossary entries for.

        Returns:
            A list of glossary entries.

        """
        entries: dict[tuple[str, str, str | None], GlossaryEntry] = {}
        meaning_seen: dict[tuple[str, str, str | None], set[str]] = {}
        example_seen: dict[
            tuple[str, str, str | None], set[tuple[str, str, str | None]]
        ] = {}

        for sentence in project.sentences:
            for token in sorted(sentence.tokens, key=lambda t: t.order_index):
                annotation = token.annotation
                if not annotation or not annotation.root or not annotation.pos:
                    continue
                root = annotation.root.strip()
                root_normalized = annotation.root_normalized or normalize_old_english(
                    root
                )
                pos = annotation.pos.strip()
                if not root or not root_normalized or not pos:
                    continue

                prep_case = annotation.prep_case if pos == "E" else None
                key = (root_normalized, pos, prep_case)
                if key not in entries:
                    entries[key] = GlossaryEntry(
                        root=root,
                        normalized_root=root_normalized,
                        pos=pos,
                        classification=self._classification(annotation),
                        prep_case=prep_case,
                        sort_key=self._oe_glossary_sort_key(root_normalized, pos),
                        root_variants=[],
                        verb_class_label=self._verb_class_label(annotation),
                        verb_direct_object_case=annotation.verb_direct_object_case,
                        verb_requires_infinitive=bool(
                            annotation.verb_requires_infinitive
                        ),
                        verb_impersonal=bool(annotation.verb_impersonal),
                        verb_intransitive=(
                            annotation.verb_transitivity == "intransitive"
                        ),
                    )
                    meaning_seen[key] = set()
                    example_seen[key] = set()
                self._merge_root_variant(entries[key], root)
                self._accumulate_glossary_entry(
                    entry=entries[key],
                    annotation=annotation,
                    token=token,
                    seen_meanings=meaning_seen[key],
                    seen_examples=example_seen[key],
                )

        return sorted(
            entries.values(),
            key=lambda item: (
                item.sort_key,
                item.pos,
                item.prep_case or "",
                item.normalized_root,
            ),
        )

    def _accumulate_glossary_entry(
        self,
        entry: GlossaryEntry,
        annotation: Annotation,
        token: Token,
        seen_meanings: set[str],
        seen_examples: set[tuple[str, str, str | None]],
    ) -> None:
        """
        Merge one attestation into an existing glossary entry.

        Args:
            entry: Glossary entry to update.
            annotation: Annotation source data.
            token: Token source data.
            seen_meanings: Dedup tracker for meanings.
            seen_examples: Dedup tracker for examples.

        """
        for meaning in self._split_meanings(annotation.modern_english_meaning):
            norm = meaning.casefold()
            if norm not in seen_meanings:
                entry.meanings.append(meaning)
                seen_meanings.add(norm)

        code = (
            "" if annotation.pos in ("C", "E") else self._attested_form_code(annotation)
        )
        sense = annotation.sense.strip() if annotation.sense else None
        example = (token.surface.lower(), code, sense)
        example_norm = (
            token.surface.lower(),
            code,
            sense.casefold() if sense else None,
        )
        if example_norm not in seen_examples:
            entry.examples.append(example)
            seen_examples.add(example_norm)
        if annotation.gender:
            entry.used_genders.add(annotation.gender)
        if annotation.case:
            entry.used_cases.add(annotation.case)
        if annotation.prep_case:
            entry.used_cases.add(annotation.prep_case)
        if annotation.verb_direct_object_case:
            entry.used_cases.add(annotation.verb_direct_object_case)
        if annotation.pos == "V":
            if entry.verb_class_label is None:
                entry.verb_class_label = self._verb_class_label(annotation)
            if (
                entry.verb_direct_object_case is None
                and annotation.verb_direct_object_case
            ):
                entry.verb_direct_object_case = annotation.verb_direct_object_case
            entry.verb_requires_infinitive = entry.verb_requires_infinitive or bool(
                annotation.verb_requires_infinitive
            )
            entry.verb_impersonal = entry.verb_impersonal or bool(
                annotation.verb_impersonal
            )
            entry.verb_intransitive = entry.verb_intransitive or (
                annotation.verb_transitivity == "intransitive"
            )

    def _merge_root_variant(self, entry: GlossaryEntry, root: str) -> None:
        """
        Merge a new root spelling into an existing glossary entry.

        Args:
            entry: Existing glossary entry.
            root: Incoming root spelling from annotation data.

        """
        if root == entry.root or root in entry.root_variants:
            return
        if self._root_display_score(root) > self._root_display_score(entry.root):
            entry.root_variants.append(entry.root)
            entry.root = root
            return
        entry.root_variants.append(root)
        entry.root_variants = sorted(set(entry.root_variants), key=str.casefold)

    def _root_display_score(self, root: str) -> tuple[int, int]:
        """
        Score a root form for display preference.

        Higher values win and favor richer diacritics and internal dashes.

        Args:
            root: The root form to score.

        Returns:
            Tuple score for comparison.

        """
        diacritics = sum(1 for ch in root if ch in "āēīōūȳǣċġ")
        dashes = sum(1 for ch in root if ch in "-–—")  # noqa: RUF001
        return diacritics + dashes, len(root)

    def _classification(self, annotation: Annotation) -> str:  # noqa: PLR0911
        """
        Render classification text for glossary entries.

        Args:
            annotation: The annotation to render the classification for.

        Returns:
            The rendered classification text.

        """
        if annotation.pos == "N":
            declension = (
                self.DECLENSION_MAP.get(annotation.declension, annotation.declension)
                if annotation.declension
                else None
            )
            parts = [part for part in (annotation.gender, declension) if part]
            return " ".join(parts)
        if annotation.pos == "V":
            verb_class = "?"
            if annotation.verb_class:
                verb_class = self.VERB_CLASS_MAP.get(
                    annotation.verb_class, annotation.verb_class
                )
            parts = [verb_class]
            if (
                annotation.verb_direct_object_case
                and annotation.verb_direct_object_case != "a"
            ):
                case_name = self.CASE_CODE_TO_SHORT_MAP.get(
                    annotation.verb_direct_object_case,
                    annotation.verb_direct_object_case,
                )
                parts.append(f"(+ {case_name})")
            return " ".join(parts)
        if annotation.pos == "R":
            if annotation.pronoun_type:
                return self.PRONOUN_TYPE_MAP.get(
                    annotation.pronoun_type, annotation.pronoun_type
                )
            return ""
        if annotation.pos == "E":
            if not annotation.prep_case:
                return ""
            case_name = self.CASE_CODE_TO_SHORT_MAP.get(
                annotation.prep_case, annotation.prep_case
            )
            return f"(+{case_name})"
        return ""

    def _attested_form_code(self, annotation: Annotation) -> str:  # noqa: PLR0911
        """
        Render compact DB-code annotations for attested forms.

        Args:
            annotation: The annotation to render the attested form code for.

        Returns:
            The rendered attested form code.

        """
        if annotation.pos == "N":
            return self._dot_join(annotation.case, annotation.number)

        if annotation.pos == "V":
            tense_code = self._verb_tense_code(annotation.verb_tense)
            if annotation.verb_form == "p":
                return self._dot_join("p", tense_code)
            if annotation.verb_form == "i":
                return "i"
            if annotation.verb_form == "ii":
                return "ii"
            return self._dot_join(
                tense_code,
                annotation.verb_mood,
                annotation.verb_person,
                annotation.number,
            )

        if annotation.pos == "R":
            return self._dot_join(
                annotation.pronoun_type, annotation.pronoun_number, annotation.case
            )
        if annotation.pos == "D":
            return self._dot_join(
                annotation.article_type, annotation.case, annotation.number
            )
        if annotation.pos == "A":
            return self._dot_join(
                annotation.adjective_degree,
                annotation.adjective_inflection,
                annotation.gender,
                annotation.case,
                annotation.number,
            )
        if annotation.pos == "B":
            return self._dot_join(annotation.adverb_degree)
        if annotation.pos == "L":
            return self._dot_join(annotation.case, annotation.number)
        return self._dot_join(annotation.case, annotation.number)

    def _render_glossary(self, entries: list[GlossaryEntry]) -> str:
        """
        Render glossary legend and entries in three columns.

        Args:
            entries: The list of glossary entries to render.

        Returns:
            The rendered glossary legend and entries.

        """
        if not entries:
            return r"\noindent No glossary entries available."

        lines = [
            self._render_glossary_legend(entries),
            self._render_glossary_decode_block(),
            self._horizontal_rule(),
            r"\footnotesize",
            r"\begin{multicols}{3}",
        ]
        for entry in entries:
            pos_display = self.PART_OF_SPEECH_MAP.get(entry.pos, entry.pos.lower())
            root_block = r"\textbf{" + self._latex_escape(entry.root) + r"}"
            if entry.root_variants:
                root_block += (
                    " "
                    r"\textcolor[HTML]{666666}{("
                    + self._latex_escape("variants: " + ", ".join(entry.root_variants))
                    + r")}"
                )
            classification = self._latex_escape(entry.classification or "?")
            meaning_text = (
                self._latex_escape("; ".join(entry.meanings)) if entry.meanings else "?"
            )
            rendered_examples: list[str] = []
            for surface, code, sense in entry.examples:
                rendered = r"\textbf{" + self._latex_escape(surface) + r"}"
                if sense:
                    rendered += r" \textit{" + self._latex_escape(sense) + r"}"
                if entry.pos not in ("E", "C"):
                    rendered += (
                        r" \textcolor[HTML]{666666}{["
                        + self._latex_escape(code)
                        + r"]}"
                    )
                rendered_examples.append(rendered)
            examples = "; ".join(rendered_examples)
            if not examples:
                examples = ""

            classification_block = ""
            if entry.pos == "V":
                classification_block = self._render_verb_classification(entry)
            elif entry.pos == "E" and entry.classification:
                classification_block = (
                    " "
                    r"\textcolor[HTML]{666666}{"
                    + self._latex_escape(entry.classification)
                    + r"}"
                )
            elif entry.pos not in {"A", "B", "C"}:
                classification_block = r" \textit{" + classification + r"}"

            details = meaning_text
            if examples:
                details += "; " + examples
            lines.append(
                r"\noindent"
                + root_block
                + " "
                + self._latex_escape(pos_display)
                + ":"
                + classification_block
                + " "
                + details
                + r"\par"
            )

        lines.append(r"\end{multicols}")
        lines.append(r"\normalsize")
        return "\n".join(lines)

    def _render_verb_classification(self, entry: GlossaryEntry) -> str:
        """
        Render verb classification block with verb metadata flags.

        Args:
            entry: Glossary entry.

        Returns:
            LaTeX fragment for the classification block.

        """
        verb_class = entry.verb_class_label or "?"
        parts = [r"\textit{" + self._latex_escape(verb_class) + r"}"]
        if entry.verb_impersonal:
            parts.append(r"\textcolor[HTML]{666666}{[impers]}")
        if entry.verb_intransitive:
            parts.append(r"\textcolor[HTML]{666666}{[intrans]}")
        if entry.verb_direct_object_case and entry.verb_direct_object_case != "a":
            case_name = self.CASE_CODE_TO_SHORT_MAP.get(
                entry.verb_direct_object_case,
                entry.verb_direct_object_case,
            )
            parts.append(self._latex_escape(f"(+ {case_name})"))
        if entry.verb_requires_infinitive:
            parts.append(self._latex_escape("(+ inf)"))
        return " " + " ".join(parts)

    def _verb_class_label(self, annotation: Annotation) -> str | None:
        """
        Resolve human-readable verb class label from annotation.

        Args:
            annotation: Source annotation.

        Returns:
            Verb class label or ``None``.

        """
        if not annotation.verb_class:
            return None
        return self.VERB_CLASS_MAP.get(annotation.verb_class, annotation.verb_class)

    def _render_glossary_legend(self, entries: list[GlossaryEntry]) -> str:
        """
        Render glossary legend including full verb/adjective/adverb codebooks.

        Args:
            entries: The list of glossary entries to render.

        Returns:
            The rendered glossary legend.

        """
        del entries
        lines = [r"{\footnotesize", r"\begin{multicols}{5}"]
        lines.append(r"\noindent\textbf{Parts of Speech}\par")
        for pos in self._POS_ORDER:
            lines.append(  # noqa: PERF401
                r"\noindent "
                + self._latex_escape(self.PART_OF_SPEECH_MAP[pos])
                + ": "
                + self._latex_escape(self.POS_LEGEND_MAP.get(pos, pos.lower()))
                + r"\par"
            )

        lines.append(r"\columnbreak")
        lines.append(r"\noindent\textbf{Gender \& Case}\par")
        for code in ["m", "f", "n"]:
            lines.append(  # noqa: PERF401
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(self.GENDER_LEGEND_MAP[code])
                + r"\par"
            )
        for code in ["n", "a", "g", "d", "i"]:
            lines.append(  # noqa: PERF401
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(self.CASE_LEGEND_MAP[code])
                + r"\par"
            )

        lines.append(r"\columnbreak")
        lines.append(r"\noindent\textbf{Verb Notation I}\par")
        for code, label in self.VERB_TENSE_LEGEND_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )
        for code, label in self.VERB_MOOD_LEGEND_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )

        lines.append(r"\columnbreak")
        lines.append(r"\noindent\textbf{Verb Notation II}\par")
        verb_form_legend = {
            "f": "finite",
            "i": "infinitive",
            "p": "participle",
            "ii": "inflected infinitive",
        }
        for code, label in verb_form_legend.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )
        for code, label in self.VERB_PERSON_LEGEND_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )
        for code, label in self.NUMBER_LEGEND_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )

        lines.append(r"\columnbreak")
        lines.append(r"\noindent\textbf{Adjective \& Adverb}\par")
        lines.append(r"\noindent\textbf{Adj/Adv Degree}\par")
        for code, label in self.ADJECTIVE_DEGREE_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )
        lines.append(r"\noindent\textbf{Adj Inflection}\par")
        for code, label in self.ADJECTIVE_INFLECTION_MAP.items():
            lines.append(
                r"\noindent "
                + self._latex_escape(code)
                + ": "
                + self._latex_escape(label)
                + r"\par"
            )
        lines.append(r"\end{multicols}")
        lines.append(r"}")
        return "\n".join(lines)

    def _render_glossary_decode_block(self) -> str:
        """
        Render explanatory text beneath the legend columns.

        Returns:
            The rendered explanatory text.

        """
        return "\n".join(  # noqa: FLY002
            [
                r"{\footnotesize",
                r"\noindent\textbf{How to Decode Annotations}\par",
                r"\noindent Codes in \textcolor[HTML]{666666}{[brackets]} after attested forms "  # noqa: E501
                r"encode morphology using the abbreviations listed above.\par",
                r"}",
            ]
        )

    def _oe_glossary_sort_key(self, root: str, pos: str) -> tuple[int, ...]:
        """
        Return a sort key using Old English collation and ``ġe``-prefix rule.

        Args:
            root: The root of the entry.
            pos: The part-of-speech of the entry.

        Returns:
            A sort key using Old English collation and ``ġe``-prefix rule.

        """
        original = root.casefold()
        if pos in {"N", "V"} and original.startswith("ġe"):
            original = original[2:]

        normalized = self._normalize_oe_for_sort(original)
        key: list[int] = []
        for ch in normalized:
            if ch in self._OE_ALPHA_ORDER:
                key.append(self._OE_ALPHA_ORDER[ch])
                continue
            if ch.isalpha():
                key.extend((999, ord(ch)))
        return tuple(key)

    def _normalize_oe_for_sort(self, text: str) -> str:
        """Normalize text for OE glossary collation."""
        translations = str.maketrans(
            {
                "ā": "a",
                "ē": "e",
                "ī": "i",
                "ō": "o",
                "ū": "u",
                "ȳ": "y",
                "ǣ": "æ",
                "ċ": "c",
                "ġ": "g",
                "ð": "þ",
            }
        )
        normalized = text.translate(translations)
        normalized = normalized.lstrip("-–— ")  # noqa: RUF001
        return re.sub(r"[^a-zæþ]", "", normalized)

    def _split_meanings(self, modern_meaning: str | None) -> list[str]:
        """
        Split and dedupe senses on semicolon/comma boundaries.

        Args:
            modern_meaning: The modern meaning to split.

        Returns:
            A list of split and deduped senses.

        """
        if not modern_meaning:
            return []
        parts = [
            part.strip() for part in re.split(r"[;,]", modern_meaning) if part.strip()
        ]
        deduped: list[str] = []
        seen: set[str] = set()
        for part in parts:
            norm = part.casefold()
            if norm not in seen:
                deduped.append(part)
                seen.add(norm)
        return deduped

    def _dot_join(self, *parts: str | None) -> str:
        """
        Join non-empty code segments without separators.

        Args:
            *parts: The parts to join.

        Returns:
            A string of the joined parts.

        """
        filtered = [part for part in parts if part]
        return "".join(filtered) if filtered else "-"

    def _verb_tense_code(self, tense: str | None) -> str | None:
        """
        Render concise verb tense codes without POS ambiguity.

        Args:
            tense: The tense to render the code for.

        Returns:
            The rendered tense code.

        """
        if tense == "n":
            return "pr"
        if tense == "p":
            return "pa"
        return tense

    def _horizontal_rule(self) -> str:
        """
        Return LaTeX for a full-width horizontal rule.

        Returns:
            The LaTeX for a full-width horizontal rule.

        """
        return r"\par\noindent\rule{\textwidth}{0.4pt}\par"

    def _latex_escape(self, value: str) -> str:
        """
        Escape user text for safe insertion into LaTeX source.

        Args:
            value: The text to escape.

        Returns:
            The escaped text.

        """
        unicode_macros = {
            "ā": r"\={a}",
            "ē": r"\={e}",
            "ī": r"\={\i}",
            "ō": r"\={o}",
            "ū": r"\={u}",
            "ȳ": r"\={y}",
            "ǣ": r"\={\ae}",
            "Ā": r"\={A}",
            "Ē": r"\={E}",
            "Ī": r"\={I}",
            "Ō": r"\={O}",
            "Ū": r"\={U}",
            "Ȳ": r"\={Y}",
            "Ǣ": r"\={\AE}",
            "ġ": r"\.{g}",
            "ċ": r"\.{c}",
            "Ġ": r"\.{G}",
            "Ċ": r"\.{C}",
        }
        escapes = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        escaped = "".join(unicode_macros.get(ch, escapes.get(ch, ch)) for ch in value)
        return escaped.replace("\n", r"\newline ")
