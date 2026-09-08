"""Export-only renderer for Old English and Translation reading-text shares."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from oeapp.models.text_flow import (
    plain_text_separator,
    sentence_separator_kind,
    visible_titles,
)

if TYPE_CHECKING:
    from pathlib import Path

    from oeapp.models.project import Project
    from oeapp.models.sentence import Sentence


class ReadingTextExporter:
    """
    Build UTF-8 reading-text strings from persisted project sentences.

    Rendering uses ``Project.sentences`` and ``oeapp.models.text_flow``. Notes
    and Full Translation widgets are not consulted.
    """

    #: Emit a running verse-line number after this many verse lines.
    VERSE_NUMBER_INTERVAL: Final[int] = 5
    #: Leading spaces applied to each non-empty verse line.
    VERSE_INDENT: Final[str] = "    "

    def render_old_english(self, project: Project) -> str:
        """
        Render the project's Old English reading text.

        Args:
            project: Project whose sentences are rendered.

        Returns:
            Plain UTF-8 reading text using ``text_oe``.

        """
        return self._render(project, translation=False)

    def render_translation(self, project: Project) -> str:
        """
        Render the project's Modern English reading text.

        Empty translations stay empty; ``[...]`` is never inserted.

        Args:
            project: Project whose sentences are rendered.

        Returns:
            Plain UTF-8 reading text using ``text_modern``.

        """
        return self._render(project, translation=True)

    def write_utf8(self, path: Path, text: str) -> None:
        """
        Write ``text`` as UTF-8 with LF newlines and no BOM.

        If ``path`` does not already use a ``.txt`` suffix, ``.txt`` is
        appended to the filename.

        Args:
            path: Destination path; ``.txt`` is enforced when missing.
            text: Rendered reading text.

        Raises:
            ValueError: If the file cannot be written.

        Side Effects:
            Creates or overwrites a ``.txt`` file on disk.

        """
        if path.suffix.lower() != ".txt":
            path = path.with_name(f"{path.name}.txt")
        try:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        except (OSError, PermissionError) as exc:
            msg = f"Failed to write export file:\n{exc!s}"
            raise ValueError(msg) from exc

    def _render(self, project: Project, *, translation: bool) -> str:
        """
        Render OE or translation reading text from persisted sentences.

        Args:
            project: Project whose sentences are rendered.

        Keyword Args:
            translation: Use Modern English bodies when ``True``.

        Returns:
            Concatenated reading text.

        """
        parts: list[str] = []
        previous: Sentence | None = None
        verse_line_count = 0
        sentences = sorted(project.sentences, key=lambda s: s.display_order)
        for sentence in sentences:
            titles = visible_titles(previous, sentence)
            if titles:
                if parts:
                    parts.append("\n\n")
                parts.append("\n".join(titles) + "\n")
            kind = sentence_separator_kind(previous, sentence, bool(titles))
            parts.append(plain_text_separator(kind))
            body = (sentence.text_modern or "") if translation else sentence.text_oe
            if sentence.is_verse and body:
                body = self._indent_verse_body(body)
            parts.append(body)
            if sentence.is_verse and not (previous is not None and previous.is_verse):
                # A new verse run starts after prose (or at the very start of
                # the document): number this run 5, 10, ... independently of
                # any earlier run's leftover count.
                verse_line_count = 0
            marker, verse_line_count = self._verse_number_marker(
                sentence,
                verse_line_count,
                translation=translation,
            )
            if marker:
                parts.append(marker)
            previous = sentence
        return "".join(parts)

    def _indent_verse_body(self, body: str) -> str:
        """
        Prefix each non-empty line with :attr:`VERSE_INDENT`.

        Args:
            body: Verse body text.

        Returns:
            Indented verse body.

        """
        return "\n".join(
            f"{self.VERSE_INDENT}{line}" if line else line for line in body.split("\n")
        )

    def _verse_number_marker(
        self,
        sentence: Sentence,
        verse_line_count: int,
        *,
        translation: bool,
    ) -> tuple[str, int]:
        """
        Advance the verse-line counter and optionally emit crossed numbers.

        Line counting always uses the sentence's unindented ``text_oe``, even
        on a Translation render, so a short Modern English body never
        under-counts verse lines. A number is emitted for every multiple of
        :attr:`VERSE_NUMBER_INTERVAL` that this stanza's lines cross, not
        only when the running total lands exactly on a multiple, so a short
        stanza that leaves the total off-multiple does not permanently stop
        numbering.

        Args:
            sentence: Current sentence.
            verse_line_count: Running count of verse lines so far.

        Keyword Args:
            translation: Whether this is a translation render.

        Returns:
            Marker string (may be empty) and updated verse-line count.

        """
        if not sentence.is_verse:
            return "", verse_line_count
        line_count = len(sentence.text_oe.split("\n")) if sentence.text_oe else 0
        if not line_count:
            return "", verse_line_count
        before = verse_line_count
        verse_line_count = before + line_count
        modern = (sentence.text_modern or "").strip()
        skip_empty_translation = translation and not modern
        crossed = self._crossed_multiples(before, verse_line_count)
        if crossed and not skip_empty_translation:
            marker = "".join(f"\n{number}" for number in crossed)
            return marker, verse_line_count
        return "", verse_line_count

    def _crossed_multiples(self, before: int, after: int) -> list[int]:
        """
        List multiples of :attr:`VERSE_NUMBER_INTERVAL` crossed by an increase.

        Args:
            before: Running verse-line count before this stanza.
            after: Running verse-line count after this stanza.

        Returns:
            Multiples of :attr:`VERSE_NUMBER_INTERVAL` in ``(before, after]``.

        """
        interval = self.VERSE_NUMBER_INTERVAL
        first = (before // interval + 1) * interval
        return list(range(first, after + 1, interval))
