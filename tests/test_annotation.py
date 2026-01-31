"""Unit tests for Annotation model."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from oeapp.models.annotation import Annotation
from oeapp.models.token import Token
from oeapp.models.idiom import Idiom
from tests.conftest import create_test_project, create_test_sentence


class TestAnnotation:
    """Test cases for Annotation model."""

    def test_create_with_all_fields(self, db_session):
        """Test model creation with all fields."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Sentence.create already creates tokens, so get the first one
        tokens = Token.list(sentence.id)
        token = tokens[0]  # Use existing token instead of creating new one

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        annotation = Annotation(
            token_id=token.id,
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="s",
            verb_class="w1",
            verb_tense="p",
            verb_mood="i",
            verb_person=3,
            verb_aspect="p",
            verb_form="f",
            verb_direct_object_case="a",
            prep_case="d",
            adjective_inflection="s",
            adjective_degree="p",
            adverb_degree="p",
            conjunction_type="c",
            pronoun_type="p",
            pronoun_number="s",
            article_type="d",
            confidence=75,
            modern_english_meaning="king",
            root="cyning",
        )
        annotation.save()
        _annotation = Annotation.get(annotation.id)

        assert _annotation.token_id == token.id
        assert _annotation.pos == "N"
        assert _annotation.gender == "m"
        assert _annotation.number == "s"
        assert _annotation.case == "n"
        assert _annotation.declension == "s"
        assert _annotation.verb_class == "w1"
        assert _annotation.verb_tense == "p"
        assert _annotation.verb_person == "3"
        assert _annotation.verb_mood == "i"
        assert _annotation.verb_aspect == "p"
        assert _annotation.verb_form == "f"
        assert _annotation.verb_direct_object_case == "a"
        assert _annotation.prep_case == "d"
        assert _annotation.adjective_inflection == "s"
        assert _annotation.adjective_degree == "p"
        assert _annotation.adverb_degree == "p"
        assert _annotation.conjunction_type == "c"
        assert _annotation.pronoun_type == "p"
        assert _annotation.pronoun_number == "s"
        assert _annotation.article_type == "d"
        assert _annotation.confidence == 75
        assert _annotation.modern_english_meaning == "king"
        assert _annotation.root == "cyning"

    def test_create_with_partial_fields(self, db_session):
        """Test model creation with partial fields (None values)."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        # Sentence.create already creates tokens, so get the first one
        tokens = Token.list(sentence.id)
        token = tokens[0]  # Use existing token instead of creating new one

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        annotation = Annotation(token_id=token.id, pos="N", gender="m")
        annotation.save()

        assert annotation.pos == "N"
        assert annotation.gender == "m"
        assert annotation.number is None
        assert annotation.case is None

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.save()
        annotation_id = annotation.token_id

        retrieved = Annotation.get(annotation_id)
        assert retrieved is not None
        assert retrieved.token_id == annotation_id
        assert retrieved.pos == "N"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent annotation."""
        result = Annotation.get(99999)
        assert result is None

    def test_exists_returns_true_when_exists(self, db_session):
        """Test exists() returns True when annotation exists."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Annotation already exists from Sentence.create
        assert Annotation.exists(token.id) is True

    def test_exists_returns_false_when_not_exists(self, db_session):
        """Test exists() returns False when annotation doesn't exist."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        assert Annotation.exists(token.id) is False

    def test_to_json_serializes_all_fields(self, db_session):
        """Test to_json() serializes all fields."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.declension = "s"
        annotation.article_type = "d"
        annotation.pronoun_type = "p"
        annotation.pronoun_number = "s"
        annotation.verb_class = "w1"
        annotation.verb_tense = "p"
        annotation.verb_person = "3"
        annotation.verb_mood = "i"
        annotation.verb_aspect = "p"
        annotation.verb_form = "f"
        annotation.verb_direct_object_case = "a"
        annotation.prep_case = "d"
        annotation.adjective_inflection = "s"
        annotation.adjective_degree = "p"
        annotation.conjunction_type = "c"
        annotation.adverb_degree = "p"
        annotation.confidence = 75
        annotation.modern_english_meaning = "king"
        annotation.root = "cyning"
        annotation.last_inferred_json = '{"some": "data"}'
        annotation.save()

        data = annotation.to_json()
        assert data["pos"] == "N"
        assert data["gender"] == "m"
        assert data["number"] == "s"
        assert data["case"] == "n"
        assert data["declension"] == "s"
        assert data["article_type"] == "d"
        assert data["pronoun_type"] == "p"
        assert data["pronoun_number"] == "s"
        assert data["verb_class"] == "w1"
        assert data["verb_tense"] == "p"
        assert data["verb_person"] == "3"
        assert data["verb_mood"] == "i"
        assert data["verb_aspect"] == "p"
        assert data["verb_form"] == "f"
        assert data["verb_direct_object_case"] == "a"
        assert data["prep_case"] == "d"
        assert data["adjective_inflection"] == "s"
        assert data["adjective_degree"] == "p"
        assert data["conjunction_type"] == "c"
        assert data["adverb_degree"] == "p"
        assert data["confidence"] == 75
        assert data["modern_english_meaning"] == "king"
        assert data["root"] == "cyning"
        assert data["last_inferred_json"] == '{"some": "data"}'
        assert "updated_at" in data
        assert isinstance(data["updated_at"], str)

    def test_from_json_creates_annotation(self, db_session):
        """Test from_json() creates annotation from data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        ann_data = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "modern_english_meaning": "king",
            "root": "cyning",
        }
        annotation = Annotation.from_json(token.id, ann_data)

        assert annotation.token_id == token.id
        assert annotation.pos == "N"
        assert annotation.gender == "m"
        assert annotation.number == "s"
        assert annotation.case == "n"

    def test_from_json_handles_partial_data(self, db_session):
        """Test from_json() handles partial data."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation created by Sentence.create
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        ann_data = {"pos": "N"}
        annotation = Annotation.from_json(token.id, ann_data)

        assert annotation.pos == "N"
        assert annotation.gender is None

    def test_from_json_with_idiom_id(self, db_session):
        """Test from_json() with idiom_id."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)

        idiom = Idiom(
            sentence_id=sentence.id, start_token_id=tokens[0].id, end_token_id=tokens[1].id
        )
        idiom.save()

        ann_data = {"pos": "V", "confidence": 85}
        annotation = Annotation.from_json(None, ann_data, idiom_id=idiom.id)

        assert annotation.idiom_id == idiom.id
        assert annotation.token_id is None
        assert annotation.pos == "V"
        assert annotation.confidence == 85

    def test_from_json_validation_errors(self, db_session):
        """Test from_json() validation errors."""
        # Case 1: Both IDs provided
        with pytest.raises(
            ValueError, match="Either token_id or idiom_id must be provided, not both"
        ):
            Annotation.from_json(1, {}, idiom_id=1)

        # Case 2: Neither ID provided
        with pytest.raises(ValueError, match="Either token_id or idiom_id must be provided"):
            Annotation.from_json(None, {})

        # Case 3: Invalid field in JSON
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]
        # We need an existing annotation to trigger the "else" branch that checks valid_fields
        # Annotation already exists from Sentence.create

        with pytest.raises(ValueError, match="Invalid annotation field: invalid_field"):
            Annotation.from_json(token.id, {"invalid_field": "value"})

    def test_from_json_updates_existing_annotation(self, db_session):
        """Test from_json() updates existing annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        # Get existing annotation and update it via from_json
        ann_data = {"pos": "V", "gender": "f", "confidence": 99}
        annotation = Annotation.from_json(token.id, ann_data)

        assert annotation.pos == "V"
        assert annotation.gender == "f"
        assert annotation.confidence == 99

        # Verify it's the same record
        retrieved = Annotation.get_by_token(token.id)
        assert retrieved.id == annotation.id
        assert retrieved.pos == "V"

    def test_from_json_with_updated_at(self, db_session):
        """Test from_json() handles updated_at field."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        timestamp = "2024-01-01T12:00:00+00:00"
        ann_data = {"pos": "N", "updated_at": timestamp}
        annotation = Annotation.from_json(token.id, ann_data)

        expected_dt = datetime(2024, 1, 1, 12, 0, 0)
        assert annotation.updated_at == expected_dt

    def test_from_json_commit_false(self, db_session):
        """Test from_json() with commit=False."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        # Delete existing
        ann = Annotation.get_by_token(token.id)
        if ann:
            ann.delete()
        db_session.commit() # Ensure it's committed as deleted

        ann_data = {"pos": "N"}
        # from_json calls annotation.save(commit=commit)
        # SaveDeleteMixin.save(commit=False) calls session.add() and session.flush()
        annotation = Annotation.from_json(token.id, ann_data, commit=False)

        assert annotation.pos == "N"
        assert annotation in db_session

        # Verify it's in the DB (flushed)
        assert Annotation.get_by_token(token.id) is not None

        # Rollback the transaction - this should remove the flushed record
        db_session.rollback()

        # Now it should be gone
        assert Annotation.get_by_token(token.id) is None

    def test_check_constraint_rejects_invalid_pos(self, db_session):
        """Test check constraint rejects invalid POS values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        annotation = Annotation(token_id=token.id, pos="X")
        with pytest.raises(IntegrityError):
            annotation.save()

    def test_check_constraint_rejects_invalid_gender(self, db_session):
        """Test check constraint rejects invalid gender values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        annotation = Annotation(token_id=token.id, pos="N", gender="x")
        with pytest.raises(IntegrityError):
            annotation.save()

    def test_check_constraint_rejects_invalid_number(self, db_session):
        """Test check constraint rejects invalid number values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()
        annotation = Annotation(token_id=token.id, pos="N", number="x")
        with pytest.raises(IntegrityError):
            annotation.save()

    def test_check_constraint_rejects_invalid_case(self, db_session):
        """Test check constraint rejects invalid case values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        annotation = Annotation(token_id=token.id, pos="N", case="x")
        with pytest.raises(IntegrityError):
            annotation.save()

    def test_check_constraint_rejects_invalid_confidence(self, db_session):
        """Test check constraint rejects invalid confidence values."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Delete existing annotation
        existing_ann = Annotation.get(token.id)
        if existing_ann:
            existing_ann.delete()

        # Confidence > 100
        with pytest.raises(IntegrityError):
            annotation = Annotation(token_id=token.id, pos="N", confidence=101)
            annotation.save()

        db_session.rollback()
        # Confidence < 0
        with pytest.raises(IntegrityError):
            annotation2 = Annotation(token_id=token.id, pos="N", confidence=-1)
            annotation2.save()

    def test_updated_at_set_on_creation(self, db_session):
        """Test updated_at is set on creation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Get existing annotation and update it
        annotation = Annotation.get(token.id)
        assert annotation is not None
        before = datetime.now(UTC).replace(tzinfo=None)
        annotation.pos = "N"
        annotation.save()
        after = datetime.now(UTC).replace(tzinfo=None)

        assert before <= annotation.updated_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when annotation is modified."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Get existing annotation
        annotation = Annotation.get(token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.save()
        db_session.refresh(annotation)
        original_updated = annotation.updated_at

        import time

        time.sleep(0.01)  # Small delay to ensure timestamp difference

        annotation.pos = "V"
        annotation.save()
        db_session.refresh(annotation)

        assert annotation.updated_at > original_updated

    def test_relationship_with_token(self, db_session):
        """Test annotation has relationship with token."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        tokens = Token.list(sentence.id)
        token = tokens[0]

        # Get existing annotation
        annotation = Annotation.get(token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.save()

        assert annotation.token.id == token.id
        assert annotation.token.surface in ["Se", "cyning"]  # Could be either token


class TestAnnotationFromAnnotation:
    """Test cases for Annotation.from_annotation method."""

    def test_from_annotation_success_token(self, db_session):
        """Test successful copy from token-based annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        source = Annotation(token_id=token.id, pos="N", gender="m")
        target = Annotation(token_id=token.id)

        result = target.from_annotation(source)

        assert result.pos == "N"
        assert result.gender == "m"
        assert result.token_id == token.id

    def test_from_annotation_success_idiom(self, db_session):
        """Test successful copy from idiom-based annotation."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token1 = sentence.tokens[0]
        token2 = sentence.tokens[1]

        idiom = Idiom(
            sentence_id=sentence.id, start_token_id=token1.id, end_token_id=token2.id
        )
        idiom.save()

        source = Annotation(idiom_id=idiom.id, pos="D", gender="n")
        target = Annotation(idiom_id=idiom.id)

        result = target.from_annotation(source)

        assert result.pos == "D"
        assert result.gender == "n"
        assert result.idiom_id == idiom.id

    def test_from_annotation_validation_both_ids(self, db_session):
        """Test ValueError when source has both token_id and idiom_id."""
        source = Annotation(token_id=1, idiom_id=1)
        target = Annotation(token_id=1)

        with pytest.raises(
            ValueError, match="Either token_id or idiom_id must be provided, not both"
        ):
            target.from_annotation(source)

    def test_from_annotation_validation_no_ids(self, db_session):
        """Test ValueError when source has neither token_id nor idiom_id."""
        source = Annotation()
        target = Annotation(token_id=1)

        with pytest.raises(
            ValueError, match="Either token_id or idiom_id must be provided"
        ):
            target.from_annotation(source)

    def test_from_annotation_validation_token_mismatch(self, db_session):
        """Test ValueError when token_id mismatch between source and target."""
        source = Annotation(token_id=1)
        target = Annotation(token_id=2)

        with pytest.raises(ValueError, match="Token ID mismatch"):
            target.from_annotation(source)

    def test_from_annotation_validation_idiom_mismatch(self, db_session):
        """Test ValueError when idiom_id mismatch between source and target."""
        source = Annotation(idiom_id=1)
        target = Annotation(idiom_id=2)

        with pytest.raises(ValueError, match="Idiom ID mismatch"):
            target.from_annotation(source)

    def test_from_annotation_copies_all_fields(self, db_session):
        """Test all fields are copied correctly."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        source = Annotation(
            token_id=token.id,
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="s",
            article_type="d",
            pronoun_type="p",
            pronoun_number="s",
            verb_class="w1",
            verb_tense="p",
            verb_person="3",
            verb_mood="i",
            verb_aspect="p",
            verb_form="f",
            verb_direct_object_case="a",
            prep_case="d",
            adjective_inflection="s",
            adjective_degree="p",
            conjunction_type="c",
            adverb_degree="p",
            confidence=90,
            last_inferred_json='{"foo": "bar"}',
            modern_english_meaning="king",
            root="cyning",
        )
        target = Annotation(token_id=token.id)

        target.from_annotation(source, commit=False)

        assert target.pos == "N"
        assert target.gender == "m"
        assert target.number == "s"
        assert target.case == "n"
        assert target.declension == "s"
        assert target.article_type == "d"
        assert target.pronoun_type == "p"
        assert target.pronoun_number == "s"
        assert target.verb_class == "w1"
        assert target.verb_tense == "p"
        assert target.verb_person == "3"
        assert target.verb_mood == "i"
        assert target.verb_aspect == "p"
        assert target.verb_form == "f"
        assert target.verb_direct_object_case == "a"
        assert target.prep_case == "d"
        assert target.adjective_inflection == "s"
        assert target.adjective_degree == "p"
        assert target.conjunction_type == "c"
        assert target.adverb_degree == "p"
        assert target.confidence == 90
        assert target.last_inferred_json == '{"foo": "bar"}'
        assert target.modern_english_meaning == "king"
        assert target.root == "cyning"

    def test_from_annotation_commit_false(self, db_session):
        """Test commit=False does not save to DB."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        # Ensure no existing annotation or delete it
        ann = Annotation.get_by_token(token.id)
        if ann:
            ann.delete()

        source = Annotation(token_id=token.id, pos="N")
        target = Annotation(token_id=token.id)

        target.from_annotation(source, commit=False)

        # Check that it's not in DB
        # Note: Annotation.get_by_token uses a new select, so it should be None
        assert Annotation.get_by_token(token.id) is None

    def test_from_annotation_commit_true(self, db_session):
        """Test commit=True saves to DB."""
        project = create_test_project(db_session)
        sentence = create_test_sentence(db_session, project.id, "Se cyning")
        token = sentence.tokens[0]

        # Ensure no existing annotation or delete it
        ann = Annotation.get_by_token(token.id)
        if ann:
            ann.delete()

        source = Annotation(token_id=token.id, pos="N")
        target = Annotation(token_id=token.id)

        target.from_annotation(source, commit=True)

        # Check that it's in DB
        retrieved = Annotation.get_by_token(token.id)
        assert retrieved is not None
        assert retrieved.pos == "N"

