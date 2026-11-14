"""Unit tests for Sentence model."""

from datetime import UTC, datetime

import pytest
from oeapp.db import get_runtime_session
from oeapp.models.sentence import Sentence

from tests.conftest import create_test_project


class TestSentence:
    """Test cases for Sentence model."""

    def test_create_model(self, db_session):
        """Test model creation."""
        project = create_test_project(db_session)


        paragraph = project.chapters[0].sections[0].paragraphs[0]

        sentence = Sentence(
            project_id=project.id,
            display_order=1,
            paragraph_id=paragraph.id,
            text_oe="Se cyning",
        )
        sentence.save()

        assert sentence.id is not None
        assert sentence.project_id == project.id
        assert sentence.text_oe == "Se cyning"
        assert isinstance(sentence.created_at, datetime)

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing sentence."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )
        sentence_id = sentence.id

        retrieved = Sentence.get(sentence_id, session=session)
        assert retrieved is not None
        assert retrieved.id == sentence_id
        assert retrieved.text_oe == "Se cyning"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent sentence."""
        session = get_runtime_session()
        result = Sentence.get(99999, session=session)
        assert result is None

    def test_list_returns_sentences_for_project(self, db_session):
        """Test list() returns sentences for project."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        sentence2 = Sentence.create(
            project_id=project.id, display_order=2, text_oe="Second", session=session
        )

        sentences = Sentence.list(project.id, session=session)
        assert len(sentences) == 2
        assert all(s.project_id == project.id for s in sentences)

    def test_list_returns_empty_when_no_sentences(self, db_session):
        """Test list() returns empty list when no sentences exist."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentences = Sentence.list(project.id, session=session)
        assert sentences == []

    def test_get_next_sentence_returns_next(self, db_session):
        """Test get_next_sentence() returns next sentence."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        sentence2 = Sentence.create(
            project_id=project.id, display_order=2, text_oe="Second", session=session
        )

        next_sentence = Sentence.get_next_sentence(project.id, 2, session=session)
        assert next_sentence is not None
        assert next_sentence.id == sentence2.id

    def test_get_next_sentence_returns_none_when_no_next(self, db_session):
        """Test get_next_sentence() returns None when no next sentence."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        result = Sentence.get_next_sentence(project.id, 2, session=session)
        assert result is None

    def test_create_creates_sentence_with_tokens(self, db_session):
        """Test create() creates sentence and tokens."""
        session = get_runtime_session()
        project = create_test_project(db_session)

        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )

        assert sentence.id is not None
        assert len(sentence.tokens) > 0
        assert all(token.sentence_id == sentence.id for token in sentence.tokens)

    def test_create_calculates_paragraph_numbers_first_sentence(self, db_session):
        """Test create() calculates paragraph numbers for first sentence."""
        session = get_runtime_session()
        project = create_test_project(db_session)

        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )

        assert sentence.paragraph is not None
        assert sentence.paragraph.order == 1

    def test_create_calculates_paragraph_numbers_continuing_paragraph(self, db_session):
        """Test create() calculates paragraph numbers for continuing paragraph."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        sentence2 = Sentence.create(
            project_id=project.id,
            display_order=2,
            text_oe="Second",
            paragraph_id=sentence1.paragraph_id,
            session=session,
        )

        assert sentence2.paragraph_id == sentence1.paragraph_id

    def test_create_calculates_paragraph_numbers_new_paragraph(self, db_session):
        """Test create() calculates paragraph numbers for new paragraph."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        from oeapp.models.paragraph import Paragraph

        p2 = Paragraph(section_id=sentence1.paragraph.section_id, order=2)
        db_session.add(p2)
        db_session.flush()

        sentence2 = Sentence.create(
            project_id=project.id,
            display_order=2,
            text_oe="Second",
            paragraph_id=p2.id,
            session=session,
        )

        assert sentence2.paragraph_id == p2.id
        assert sentence2.paragraph.order == 2

    def test_calculate_paragraph_and_sentence_numbers_continuing(self, db_session):
        """Test recalculate_project_structure()."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        # This method now just updates order
        Sentence.recalculate_project_structure(project.id, session=session)

        db_session.refresh(sentence1.paragraph)
        assert sentence1.paragraph.order == 1

    def test_update_updates_sentence_text(self, db_session):
        """Test update() updates sentence text_oe and retokenizes."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Original", session=session
        )
        updated = sentence.update("Updated text")

        db_session.refresh(sentence)
        assert sentence.text_oe == "Updated text"
        # Tokens should be updated
        assert len(sentence.tokens) > 0

    def test_to_json_serializes_sentence(self, db_session):
        """Test to_json() serializes sentence data."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )
        sentence.text_modern = "The king"

        data = sentence.to_json()
        assert data["text_oe"] == "Se cyning"
        assert data["text_modern"] == "The king"
        assert "tokens" in data
        assert "notes" in data
        assert "idioms" in data
        assert "paragraph_ref" in data
        assert "created_at" in data

    def test_reference_label_uses_verse_span_when_present(self, db_session):
        """Verse sentences should expose ``Verse: a-b`` labels."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id,
            display_order=1,
            text_oe="l1\nl2\nl3\nl4\nl5",
            verse_line_start=1,
            verse_line_end=5,
            session=session,
        )
        assert sentence.is_verse is True
        assert sentence.reference_label == "Verse: 1-5"

    def test_reference_label_uses_sentence_number_for_prose(self, db_session):
        """Prose sentences should expose ``S:n`` labels."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )
        assert sentence.is_verse is False
        assert sentence.reference_label == "S:1"

    def test_from_json_creates_sentence(self, db_session):
        """Test from_json() creates sentence from data."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        paragraph = project.chapters[0].sections[0].paragraphs[0]
        paragraph_lookup = {
            (
                project.chapters[0].number,
                project.chapters[0].sections[0].number,
                paragraph.order,
            ): paragraph.id
        }

        sentence_data = {
            "text_oe": "Se cyning",
            "text_modern": "The king",
            "display_order": 1,
            "paragraph_ref": {
                "chapter_number": project.chapters[0].number,
                "section_number": project.chapters[0].sections[0].number,
                "paragraph_order": paragraph.order,
            },
            "tokens": [],
            "notes": [],
            "idioms": [],
        }
        sentence = Sentence.from_json(
            project.id, sentence_data, paragraph_lookup, session=session
        )

        assert sentence.project_id == project.id
        assert sentence.text_oe == "Se cyning"
        assert sentence.text_modern == "The king"

    def test_subsequent_sentences_returns_subsequent(self, db_session):
        """Test subsequent_sentences() returns subsequent sentences."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        sentence2 = Sentence.create(
            project_id=project.id, display_order=2, text_oe="Second", session=session
        )
        sentence3 = Sentence.create(
            project_id=project.id, display_order=3, text_oe="Third", session=session
        )

        subsequent = Sentence.subsequent_sentences(project.id, 1, session=session)
        assert len(subsequent) == 2
        assert all(s.display_order > 1 for s in subsequent)
        assert sentence2 in subsequent
        assert sentence3 in subsequent

    def test_subsequent_sentences_returns_empty_when_none(self, db_session):
        """Test subsequent_sentences() returns empty when no subsequent sentences."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        subsequent = Sentence.subsequent_sentences(project.id, 1, session=session)
        assert subsequent == []

    def test_renumber_sentences_updates_display_order(self, db_session):
        """Test renumber_sentences() updates display order."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        sentence2 = Sentence.create(
            project_id=project.id, display_order=2, text_oe="Second", session=session
        )

        order_mapping = {sentence1.id: 2, sentence2.id: 1}
        changes = Sentence.renumber_sentences(
            [sentence1, sentence2], order_mapping=order_mapping, session=session
        )

        assert len(changes) == 2
        db_session.refresh(sentence1)
        db_session.refresh(sentence2)
        assert sentence1.display_order == 2
        assert sentence2.display_order == 1

    def test_renumber_sentences_raises_error_without_mapping(self, db_session):
        """Test renumber_sentences() raises ValueError without mapping."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )

        with pytest.raises(ValueError, match="Either order_mapping or order_function"):
            Sentence.renumber_sentences([sentence], session=session)

    def test_restore_display_orders_restores_original_values(self, db_session):
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence1 = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        sentence2 = Sentence.create(
            project_id=project.id, display_order=2, text_oe="Second", session=session
        )
        sentence3 = Sentence.create(
            project_id=project.id, display_order=3, text_oe="Third", session=session
        )

        changes = Sentence.renumber_sentences(
            [sentence1, sentence2, sentence3],
            order_mapping={sentence1.id: 3, sentence2.id: 1, sentence3.id: 2},
            session=session,
        )
        Sentence.restore_display_orders(changes, session=session)

        db_session.refresh(sentence1)
        db_session.refresh(sentence2)
        db_session.refresh(sentence3)
        assert (
            sentence1.display_order,
            sentence2.display_order,
            sentence3.display_order,
        ) == (1, 2, 3)

    def test_restore_display_orders_with_empty_changes_is_noop(self, db_session):
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="First", session=session
        )
        Sentence.restore_display_orders([], session=session)
        db_session.refresh(sentence)
        assert sentence.display_order == 1

    def test_recalculate_project_structure_reorders_paragraphs_in_each_section(
        self, db_session
    ):
        session = get_runtime_session()
        project = create_test_project(db_session, text="")
        from oeapp.models.paragraph import Paragraph

        section = project.chapters[0].sections[0]
        p1 = Paragraph(section_id=section.id, order=5)
        p2 = Paragraph(section_id=section.id, order=9)
        db_session.add_all([p1, p2])
        db_session.commit()

        Sentence.recalculate_project_structure(project.id, session=session)
        db_session.refresh(section)
        db_session.refresh(p1)
        db_session.refresh(p2)
        assert [paragraph.order for paragraph in section.paragraphs] == [1, 2, 3]

    def test_created_at_set_on_creation(self, db_session):
        """Test created_at is set on creation."""
        session = get_runtime_session()
        project = create_test_project(db_session)

        before = datetime.now(UTC).replace(tzinfo=None)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )
        after = datetime.now(UTC).replace(tzinfo=None)

        assert before <= sentence.created_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when sentence is modified."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Original", session=session
        )
        original_updated = sentence.updated_at

        import time

        time.sleep(0.01)

        sentence.text_oe = "Updated"
        sentence.save()
        db_session.refresh(sentence)

        assert sentence.updated_at > original_updated

    def test_relationship_with_project(self, db_session):
        """Test sentence has relationship with project."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )

        assert sentence.project.id == project.id
        assert sentence.project.name == project.name

    def test_relationship_with_tokens(self, db_session):
        """Test sentence has relationship with tokens."""
        session = get_runtime_session()
        project = create_test_project(db_session)
        sentence = Sentence.create(
            project_id=project.id, display_order=1, text_oe="Se cyning", session=session
        )

        assert len(sentence.tokens) > 0
        assert all(token.sentence_id == sentence.id for token in sentence.tokens)
