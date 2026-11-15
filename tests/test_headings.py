"""Tests for heading sentences."""

from __future__ import annotations

from oeapp.models.sentence import Sentence

from tests.conftest import create_test_sentence


def test_sentence_json_round_trips_heading_role(db_session) -> None:
    """A heading role is written to the sentence JSON."""
    sentence = create_test_sentence(db_session, text="Beowulf")
    sentence.heading_role = "chapter"
    sentence.save()
    assert sentence.to_json()["heading_role"] == "chapter"


def test_old_sentence_json_without_heading_role_imports(db_session) -> None:
    """Sentence JSON from files predating heading roles still imports."""
    sentence = create_test_sentence(db_session, text="Hwæt")
    payload = sentence.to_json()
    payload.pop("heading_role", None)
    lookup = {
        (
            sentence.paragraph.section.chapter.number,
            sentence.paragraph.section.number,
            sentence.paragraph.order,
        ): sentence.paragraph_id
    }
    project_id = sentence.project_id
    sentence.delete()
    imported = Sentence.from_json(project_id, payload, lookup, session=db_session)
    assert imported.heading_role is None
