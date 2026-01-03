"""Tests to reproduce the annotation shifting bug."""

import pytest
from oeapp.models.token import Token
from oeapp.models.annotation import Annotation
from tests.conftest import create_test_project, create_test_sentence

def test_annotation_shift_on_insertion(db_session):
    """
    Test that inserting a token in the middle of a sentence
    causes later annotations to shift (the bug).
    """
    project = create_test_project(db_session)
    # Original sentence: "Se cyning wæs"
    sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
    tokens = Token.list(sentence.id)
    assert len(tokens) == 3

    # Add annotations to each token
    for i, token in enumerate(tokens):
        annotation = token.annotation
        annotation.modern_english_meaning = f"meaning_{i}"
        annotation.save()

    # Original state:
    # 0: Se (meaning_0)
    # 1: cyning (meaning_1)
    # 2: wæs (meaning_2)

    # Insert "god" after "Se": "Se god cyning wæs"
    sentence.update("Se god cyning wæs")

    # Get updated tokens
    new_tokens = Token.list(sentence.id)
    assert len(new_tokens) == 4

    # Expected (what SHOULD happen):
    # 0: Se (meaning_0)
    # 1: god (empty)
    # 2: cyning (meaning_1)
    # 3: wæs (meaning_2)

    # BUG:
    # 0: Se (meaning_0) - matches at index 0
    # 1: god (meaning_1) - matches at index 1 (old "cyning")
    # 2: cyning (meaning_2) - matches at index 2 (old "wæs")
    # 3: wæs (new) - empty

    se_token = next(t for t in new_tokens if t.surface == "Se")
    god_token = next(t for t in new_tokens if t.surface == "god")
    cyning_token = next(t for t in new_tokens if t.surface == "cyning")
    waes_token = next(t for t in new_tokens if t.surface == "wæs")

    assert se_token.annotation.modern_english_meaning == "meaning_0"
    # This is where it currently fails (it will have meaning_1 instead of None/empty)
    assert god_token.annotation.modern_english_meaning is None or god_token.annotation.modern_english_meaning == ""
    assert cyning_token.annotation.modern_english_meaning == "meaning_1"
    assert waes_token.annotation.modern_english_meaning == "meaning_2"

def test_annotation_shift_on_deletion(db_session):
    """
    Test that deleting a token in the middle of a sentence
    causes later annotations to shift (the bug).
    """
    project = create_test_project(db_session)
    # Original sentence: "Se god cyning wæs"
    sentence = create_test_sentence(db_session, project.id, "Se god cyning wæs")
    tokens = Token.list(sentence.id)
    assert len(tokens) == 4

    # Add annotations to each token
    for i, token in enumerate(tokens):
        annotation = token.annotation
        annotation.modern_english_meaning = f"meaning_{i}"
        annotation.save()

    # Original state:
    # 0: Se (meaning_0)
    # 1: god (meaning_1)
    # 2: cyning (meaning_2)
    # 3: wæs (meaning_3)

    # Remove "god": "Se cyning wæs"
    sentence.update("Se cyning wæs")

    # Get updated tokens
    new_tokens = Token.list(sentence.id)
    assert len(new_tokens) == 3

    # Expected:
    # 0: Se (meaning_0)
    # 1: cyning (meaning_2)
    # 2: wæs (meaning_3)

    # BUG:
    # 0: Se (meaning_0) - matches at index 0
    # 1: cyning (meaning_1) - matches at index 1 (old "god")
    # 2: wæs (meaning_2) - matches at index 2 (old "cyning")

    se_token = next(t for t in new_tokens if t.surface == "Se")
    cyning_token = next(t for t in new_tokens if t.surface == "cyning")
    waes_token = next(t for t in new_tokens if t.surface == "wæs")

    assert se_token.annotation.modern_english_meaning == "meaning_0"
    assert cyning_token.annotation.modern_english_meaning == "meaning_2"
    assert waes_token.annotation.modern_english_meaning == "meaning_3"

def test_annotation_preserved_on_typo_fix(db_session):
    """
    Test that fixing a typo (1-to-1 replacement) preserves the annotation.
    """
    project = create_test_project(db_session)
    # Original sentence: "Se cyning wæs"
    sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
    tokens = Token.list(sentence.id)

    # Add annotation to "cyning"
    cyning_token = tokens[1]
    cyning_token.annotation.modern_english_meaning = "king"
    cyning_token.save()

    # Fix typo: "cyning" -> "kyning"
    sentence.update("Se kyning wæs")

    # Get updated tokens
    new_tokens = Token.list(sentence.id)
    kyning_token = next(t for t in new_tokens if t.surface == "kyning")

    # Annotation should be preserved
    assert kyning_token.annotation.modern_english_meaning == "king"

def test_annotation_preserved_on_multiple_typo_fixes(db_session):
    """
    Test that fixing multiple adjacent typos (N-to-N replacement) preserves annotations.
    """
    project = create_test_project(db_session)
    # Original sentence: "Se cyning wæs"
    sentence = create_test_sentence(db_session, project.id, "Se cyning wæs")
    tokens = Token.list(sentence.id)

    # Add annotations
    tokens[1].annotation.modern_english_meaning = "king"
    tokens[2].annotation.modern_english_meaning = "was"
    tokens[1].save()
    tokens[2].save()

    # Fix typos: "cyning wæs" -> "kyning was"
    sentence.update("Se kyning was")

    # Get updated tokens
    new_tokens = Token.list(sentence.id)
    kyning_token = next(t for t in new_tokens if t.surface == "kyning")
    was_token = next(t for t in new_tokens if t.surface == "was")

    # Annotations should be preserved
    assert kyning_token.annotation.modern_english_meaning == "king"
    assert was_token.annotation.modern_english_meaning == "was"

def test_annotation_stability_with_duplicate_surfaces(db_session):
    """
    Test that annotations stay with the correct instance of duplicate words
    when tokens are inserted/deleted.
    """
    project = create_test_project(db_session)
    # Sentence: "ond he ond hie" (and he and they)
    sentence = create_test_sentence(db_session, project.id, "ond he ond hie")
    tokens = Token.list(sentence.id)
    assert len(tokens) == 4

    # Annotate the two "ond" tokens differently
    first_ond = tokens[0]
    second_ond = tokens[2]
    first_ond.annotation.modern_english_meaning = "AND_1"
    second_ond.annotation.modern_english_meaning = "AND_2"
    first_ond.save()
    second_ond.save()

    # Insert a word in the middle: "ond he þā ond hie"
    sentence.update("ond he þā ond hie")

    # Get updated tokens
    new_tokens = Token.list(sentence.id)
    assert len(new_tokens) == 5

    # Check that the "ond" tokens kept their specific annotations
    assert new_tokens[0].surface == "ond"
    assert new_tokens[0].annotation.modern_english_meaning == "AND_1"

    assert new_tokens[3].surface == "ond"
    assert new_tokens[3].annotation.modern_english_meaning == "AND_2"

    # Now delete the first "ond": "he þā ond hie"
    sentence.update("he þā ond hie")
    new_tokens_after_delete = Token.list(sentence.id)
    assert len(new_tokens_after_delete) == 4

    # The remaining "ond" should still be "AND_2"
    remaining_ond = next(t for t in new_tokens_after_delete if t.surface == "ond")
    assert remaining_ond.annotation.modern_english_meaning == "AND_2"

