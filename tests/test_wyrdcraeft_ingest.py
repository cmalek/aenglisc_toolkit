"""Tests for wyrdcraeft-driven ingest mapping."""

from __future__ import annotations

from wyrdcraeft.models import (
    Line,
    OldEnglishText,
    Paragraph,
    Section,
    Sentence,
    TextMetadata,
)

from oeapp.services.wyrdcraeft_ingest import WyrdcraeftIngestService


def _canonical_mixed() -> OldEnglishText:
    """Build mixed prose/verse canonical content."""
    return OldEnglishText(
        metadata=TextMetadata(title="Mixed"),
        content=Section(
            sections=[
                Section(
                    paragraphs=[
                        Paragraph(
                            sentences=[
                                Sentence(text="Her onginþ þis spell."),
                                Sentence(text="Hit is langsumlic."),
                            ]
                        )
                    ]
                ),
                Section(
                    title="Embedded Poem",
                    lines=[
                        Line(text=f"Verse line {i}", number=i)
                        for i in range(1, 11)
                    ],
                ),
                Section(
                    paragraphs=[
                        Paragraph(
                            sentences=[
                                Sentence(text="Þa forðferde he to tune."),
                                Sentence(text="And eft com ham."),
                            ]
                        )
                    ]
                ),
            ]
        ),
    )


def test_ingest_mixed_creates_poem_chapter_and_prose_auto_titles(
    db_session, monkeypatch
):
    """Mixed canonical text should split prose/poem runs into separate chapters."""
    service = WyrdcraeftIngestService()
    monkeypatch.setattr(service, "_ingest", lambda **_kwargs: _canonical_mixed())

    project = service.create_project(name="Mixed Ingest", text="ignored")
    chapters = sorted(project.chapters, key=lambda c: c.number)
    assert len(chapters) == 3

    assert chapters[0].title_auto is True
    assert chapters[0].title is not None
    assert chapters[0].title.endswith(" ....")

    assert chapters[1].title == "Embedded Poem"
    assert chapters[1].title_auto is False
    verse_sections = sorted(chapters[1].sections, key=lambda s: s.number)
    assert len(verse_sections) == 1
    assert verse_sections[0].title == "Lines 1-10"
    assert verse_sections[0].title_auto is True

    verse_sentences = []
    for paragraph in sorted(verse_sections[0].paragraphs, key=lambda p: p.order):
        verse_sentences.extend(sorted(paragraph.sentences, key=lambda s: s.display_order))
    assert len(verse_sentences) == 2
    assert verse_sentences[0].verse_line_start == 1
    assert verse_sentences[0].verse_line_end == 5
    assert verse_sentences[0].text_oe.count("\n") == 4
    assert verse_sentences[1].verse_line_start == 6
    assert verse_sentences[1].verse_line_end == 10

    assert chapters[2].title_auto is True
    assert chapters[2].title is not None
    assert chapters[2].title.endswith(" ....")


def test_ingest_pure_verse_chunks_sections_by_20_stanzas(db_session, monkeypatch):
    """Pure verse input should auto-chunk into 20-stanza sections."""
    line_count = 105  # 21 stanzas at 5 lines each
    canonical = OldEnglishText(
        metadata=TextMetadata(title="Pure Verse"),
        content=Section(
            lines=[Line(text=f"L{i}", number=i) for i in range(1, line_count + 1)]
        ),
    )
    service = WyrdcraeftIngestService()
    monkeypatch.setattr(service, "_ingest", lambda **_kwargs: canonical)

    project = service.create_project(name="Pure Verse", text="ignored")
    chapters = sorted(project.chapters, key=lambda c: c.number)
    assert len(chapters) == 1

    sections = sorted(chapters[0].sections, key=lambda s: s.number)
    assert len(sections) == 2
    assert sections[0].title == "Lines 1-100"
    assert sections[0].title_auto is True
    assert sections[1].title == "Lines 101-105"
    assert sections[1].title_auto is True

    verse_sentence_count = sum(
        len(paragraph.sentences) for section in sections for paragraph in section.paragraphs
    )
    assert verse_sentence_count == 21
