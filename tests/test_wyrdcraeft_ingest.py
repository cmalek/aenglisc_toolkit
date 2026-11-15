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
    # The official title "Embedded Poem" becomes the chapter heading sentence.
    assert len(verse_sentences) == 3
    assert verse_sentences[0].text_oe == "Embedded Poem"
    assert verse_sentences[0].heading_role == "chapter"
    verse_sentences = verse_sentences[1:]
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


def test_ingest_official_chapter_title_becomes_heading_sentence(
    db_session, monkeypatch
):
    """An official chapter title is inserted as the chapter heading sentence."""
    service = WyrdcraeftIngestService()
    monkeypatch.setattr(service, "_ingest", lambda **_kwargs: _canonical_mixed())

    project = service.create_project(name="Heading Ingest", text="ignored")
    chapters = sorted(project.chapters, key=lambda c: c.number)

    sentences = sorted(
        (
            s
            for paragraph in chapters[1].sections[0].paragraphs
            for s in paragraph.sentences
        ),
        key=lambda s: s.display_order,
    )
    assert sentences[0].text_oe == "Embedded Poem"
    assert sentences[0].heading_role == "chapter"
    assert sentences[0].text_modern is None
    assert chapters[1].title == "Embedded Poem"
    assert chapters[1].title_auto is False
    assert all(s.heading_role is None for s in sentences[1:])
    for chapter in (chapters[0], chapters[2]):
        assert all(
            s.heading_role is None
            for section in chapter.sections
            for paragraph in section.paragraphs
            for s in paragraph.sentences
        )
    orders = sorted(s.display_order for s in project.sentences)
    assert orders == list(range(1, len(orders) + 1))
