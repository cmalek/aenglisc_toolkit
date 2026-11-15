"""PDF export service for Full Translation window."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

from oeapp.db import get_runtime_session
from oeapp.mixins import AnnotationTextualMixin
from oeapp.models.headings import HeadingRole
from oeapp.models.project import Project
from oeapp.models.text_flow import (
    latex_separator,
    sentence_separator_kind,
    visible_titles,
)
from oeapp.services.glossary import Glossary
from oeapp.services.logs import get_logger
from oeapp.services.pdf_engine import PDFEngineError, compile_latex_with_tectonic

if TYPE_CHECKING:
    import subprocess

    from oeapp.models.glossary import GlossaryEntry
    from oeapp.models.note import Note
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


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
    #: The order of parts of speech, for rendering the glossary legend.
    _POS_ORDER: Final[list[str]] = ["N", "V", "A", "R", "D", "B", "C", "E", "I", "L"]
    #: Fixed four-space verse indent expressed in em width.
    _VERSE_INDENT_EM: Final[float] = 2.0
    #: Space above and below a heading, in points, keyed by heading role.
    #: A chapter heading always sits at the top of its PDF page.
    _HEADING_SPACING_PT: Final[dict[HeadingRole, tuple[int, int]]] = {
        HeadingRole.CHAPTER: (4, 16),
        HeadingRole.SECTION: (12, 12),
        HeadingRole.SUBSECTION: (6, 6),
    }
    #: LaTeX font command that wraps a heading, keyed by heading role.
    _HEADING_WRAPPER: Final[dict[HeadingRole, str]] = {
        HeadingRole.CHAPTER: "textbf",
        HeadingRole.SECTION: "textbf",
        HeadingRole.SUBSECTION: "textit",
    }

    def __init__(self) -> None:
        """
        Initialize the instance.
        """
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
        session = get_runtime_session()
        self.last_error = None
        project = Project.get(project_id, session=session)
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

        glossary_entries = Glossary().entries(project)
        glossary_lines = self._render_glossary(glossary_entries)

        about_text = ""
        if project.notes:
            about_text = (
                r"\section*{About this text}"
                "\n" + r"\noindent " + self._latex_escape(project.notes) + r"\par"
                "\n" + self._horizontal_rule()
            )

        return (
            r"\documentclass[9pt]{article}"
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

        A chapter heading that is not the project's first sentence ends the
        current ``paracol``, clears the page, and opens a new one, so both
        columns start the chapter on a fresh page.

        Args:
            project: The project to render.

        Returns:
            The rendered two-column text.

        """
        segments: list[tuple[list[str], list[str]]] = [([], [])]
        previous_sentence: Sentence | None = None

        for sentence in project.sentences:
            role = sentence.heading_role
            if role == HeadingRole.CHAPTER and previous_sentence is not None:
                segments.append(([], []))
            oe_parts, mode_parts = segments[-1]
            if role:
                self._append_heading(HeadingRole(role), sentence, oe_parts, mode_parts)
            else:
                self._append_body_sentence(
                    previous_sentence, sentence, oe_parts, mode_parts
                )
            previous_sentence = sentence

        page_break = "\n" + r"\clearpage" + "\n"
        return page_break.join(
            self._render_paracol(oe_parts, mode_parts)
            for oe_parts, mode_parts in segments
        )

    def _render_paracol(self, oe_parts: list[str], mode_parts: list[str]) -> str:
        """
        Wrap one page's worth of column parts in a ``paracol`` environment.

        Args:
            oe_parts: Old English column fragments.
            mode_parts: Modern English column fragments.

        Returns:
            The ``paracol`` environment for those fragments.

        """
        return "\n".join(
            [
                r"\begin{paracol}{2}",
                self._column_block(oe_parts),
                r"\switchcolumn",
                self._column_block(mode_parts),
                r"\end{paracol}",
            ]
        )

    def _column_block(self, parts: list[str]) -> str:
        """
        Join column fragments into one column body.

        A column that opens with a heading starts with its vertical space, which
        needs vertical mode, so it skips the no-indent command.

        Args:
            parts: Column fragments.

        Returns:
            The column body.

        """
        body = "".join(parts)
        opens_with_heading = body.startswith(r"\vspace{")
        lead = r"\raggedright " if opens_with_heading else r"\noindent\raggedright "
        return lead + body + r"\par"

    def _append_body_sentence(
        self,
        previous_sentence: Sentence | None,
        sentence: Sentence,
        oe_parts: list[str],
        mode_parts: list[str],
    ) -> None:
        """
        Append a non-heading sentence to both columns.

        Args:
            previous_sentence: The sentence rendered just before this one.
            sentence: The sentence to append.
            oe_parts: Old English column fragments, extended in place.
            mode_parts: Modern English column fragments, extended in place.

        Side Effects:
            Appends to ``oe_parts`` and ``mode_parts``.

        """
        titles = visible_titles(previous_sentence, sentence)
        if titles:
            if oe_parts:
                oe_parts.append(r"\par ")
                mode_parts.append(r"\par ")
            for title in titles:
                escaped_title = self._latex_escape(title)
                oe_parts.append(r"\textbf{" + escaped_title + r"}\newline ")
                mode_parts.append(r"\textbf{" + escaped_title + r"}\newline ")

        after_heading = previous_sentence is not None and bool(
            previous_sentence.heading_role
        )
        sep = latex_separator(
            sentence_separator_kind(
                previous_sentence,
                sentence,
                has_titles=bool(titles) or after_heading,
            )
        )
        if sep:
            oe_parts.append(sep)
            mode_parts.append(sep)

        note_map = self._notes_by_end_token(sentence)
        oe_rendered = self._render_oe_sentence(sentence, note_map)
        mode_rendered = self._render_modern_sentence(sentence.text_modern or "[...]")
        if sentence.is_verse:
            oe_rendered = self._indent_rendered_lines(oe_rendered)
            mode_rendered = self._indent_rendered_lines(mode_rendered)
        oe_parts.append(oe_rendered)
        mode_parts.append(mode_rendered)

        if sentence.is_verse and sentence.verse_line_end is not None:
            marker = self._latex_escape(str(sentence.verse_line_end))
            oe_parts.append(r"\newline \textbf{" + marker + r"}")
            mode_parts.append(r"\newline \textbf{" + marker + r"}")

    def _append_heading(
        self,
        role: HeadingRole,
        sentence: Sentence,
        oe_parts: list[str],
        mode_parts: list[str],
    ) -> None:
        """
        Append a heading sentence to both columns.

        The heading text is the escaped sentence text, not the token-based
        sentence rendering, so it has no verse indent, no verse line marker, and
        no footnote inside its wrapper. A chapter heading is uppercased with
        ``str.upper()`` before escaping. Notes follow the heading.

        Args:
            role: The sentence's heading role.
            sentence: The heading sentence.
            oe_parts: Old English column fragments, extended in place.
            mode_parts: Modern English column fragments, extended in place.

        Side Effects:
            Appends to ``oe_parts`` and ``mode_parts``.

        """
        modern = sentence.text_modern
        modern_text = modern if modern and modern.strip() else sentence.text_oe
        oe_parts.append(self._render_heading(role, sentence.text_oe, bool(oe_parts)))
        mode_parts.append(self._render_heading(role, modern_text, bool(mode_parts)))
        oe_parts.extend(
            self._render_footnote(sentence, note) for note in sentence.sorted_notes
        )

    def _render_heading(self, role: HeadingRole, text: str, follows_text: bool) -> str:
        """
        Render one heading as spacing, a styled wrapper, and spacing.

        Args:
            role: The heading's role.
            text: The plain heading text.
            follows_text: Whether text precedes the heading in the column, so the
                heading needs a paragraph break before its vertical space.

        Returns:
            The LaTeX for the heading.

        """
        above, below = self._HEADING_SPACING_PT[role]
        shown = text.upper() if role == HeadingRole.CHAPTER else text
        wrapper = self._HEADING_WRAPPER[role]
        return (
            (r"\par " if follows_text else "")
            + rf"\vspace{{{above}pt}}"
            + rf"\{wrapper}{{{self._latex_escape(shown)}}}"
            + r"\par "
            + rf"\vspace{{{below}pt}}"
        )

    def _indent_rendered_lines(self, rendered: str) -> str:
        """
        Indent each rendered line by :attr:`_VERSE_INDENT_EM` em width.

        Args:
            rendered: Rendered LaTeX content.

        Returns:
            Indented LaTeX content.

        """
        if not rendered:
            return rendered
        indent = rf"\hspace*{{{self._VERSE_INDENT_EM:.2f}em}}"
        return indent + rendered.replace(r"\newline ", r"\newline " + indent)

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

        Keyword Args:
            preserve_leading: Preserve leading.

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

    def _space_run_to_hspace(self, match: re.Match[str]) -> str:  # noqa: ARG002
        """
        Convert runs of spaces into one normal space + explicit width.

        Args:
            match: The match object.

        Returns:
            The converted text.

        """
        width_em = f"{self._VERSE_INDENT_EM:.2f}"
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
                (
                    r"\noindent Codes in \textcolor[HTML]{666666}{[brackets]} "
                    r"after attested forms "
                    r"encode morphology using the abbreviations listed above.\par"
                ),
                r"}",
            ]
        )

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
