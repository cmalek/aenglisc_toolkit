"""Unit tests for Token.update_from_sentence and related methods."""

import pytest
from sqlalchemy import select

from oeapp.models.token import Token


class TestUpdateFromSentence:
    """Test cases for Token.update_from_sentence."""

    def test_no_changes(self, db_session, project_and_sentence):
        """Test updating with no changes to tokens."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Update with same text
        Token.update_from_sentence("Se cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[0].order_index == 0
        assert tokens[1].surface == "cyning"
        assert tokens[1].order_index == 1

    def test_add_new_tokens(self, db_session, project_and_sentence):
        """Test adding new tokens to sentence."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Add a new token
        Token.update_from_sentence("Se cyning wæs", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 3
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        assert tokens[2].surface == "wæs"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_remove_tokens(self, db_session, project_and_sentence):
        """Test removing tokens from sentence."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save(commit=False)
        token3 = Token(sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Remove a token
        Token.update_from_sentence("Se cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "Se"
        assert tokens[1].surface == "cyning"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_reorder_tokens(self, db_session, project_and_sentence):
        """Test reordering tokens."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Reorder tokens
        Token.update_from_sentence("cyning Se", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 2
        assert tokens[0].surface == "cyning"
        assert tokens[0].order_index == 0
        assert tokens[1].surface == "Se"
        assert tokens[1].order_index == 1

    def test_render_token_surface(self, db_session, project_and_sentence):
        """
        Test render token surface form.

        When surface form changes at the same position, the token is preserved
        and its surface is updated. The algorithm matches by position first,
        then by surface for unmatched positions.
        """
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        original_token_id = token1.id

        # Update surface form - "Se" changes to "Þā" at same position
        Token.update_from_sentence("Þā cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 2
        # First token should be preserved (same position) with updated surface
        assert tokens[0].surface == "Þā"
        assert tokens[0].id == original_token_id  # Token preserved, surface updated
        # Second token should be preserved (same surface and position)
        assert tokens[1].surface == "cyning"
        assert tokens[1].id == token2.id

    def test_complex_reordering_with_duplicates(self, db_session, project_and_sentence):
        """Test complex reordering with duplicate tokens."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens with duplicates manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="þā")
        db_session.add(token1)
        db_session.flush()
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        db_session.add(token2)
        db_session.flush()
        token3 = Token(sentence_id=sentence_id, order_index=2, surface="þā")
        db_session.add(token3)
        db_session.flush()
        token4 = Token(sentence_id=sentence_id, order_index=3, surface="wæs")
        db_session.add(token4)
        db_session.flush()

        # Reorder and change
        Token.update_from_sentence("þā wæs cyning þā", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 4
        assert tokens[0].surface == "þā"
        assert tokens[1].surface == "wæs"
        assert tokens[2].surface == "cyning"
        assert tokens[3].surface == "þā"
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i

    def test_preserve_annotations(self, db_session, project_and_sentence):
        """Test that token annotations are preserved when tokens are matched."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()
        original_token_id = token1.id

        # Add annotation
        from oeapp.models.annotation import Annotation
        annotation = Annotation(token_id=token1.id, pos="R", gender="m", number="s", case="n")
        annotation.save()

        # Update sentence (reorder)
        Token.update_from_sentence("cyning Se", sentence_id)

        # Verify annotation still exists on the matched token
        tokens = Token.list(sentence_id)
        token_with_annotation = None
        for t in tokens:
            if t.id == original_token_id:
                token_with_annotation = t
                break

        assert token_with_annotation is not None
        annotation = db_session.get(Annotation, original_token_id)
        assert annotation is not None
        assert annotation.pos == "R"
        assert annotation.gender == "m"

    def test_sequential_numbering_after_insertion(self, db_session, project_and_sentence):
        """Test that tokens are numbered sequentially after insertion."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # Insert token in middle
        Token.update_from_sentence("Se wæs cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 3
        # Verify sequential numbering (0, 1, 2)
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_sequential_numbering_after_deletion(self, db_session, project_and_sentence):
        """Test that tokens are numbered sequentially after deletion."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save(commit=False)
        token3 = Token(sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Delete middle token
        Token.update_from_sentence("Se wæs", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 2
        # Verify sequential numbering (0, 1)
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_sequential_numbering_after_reorder(self, db_session, project_and_sentence):
        """Test that tokens are numbered sequentially after reordering."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save(commit=False)
        token3 = Token(sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Complete reorder
        Token.update_from_sentence("wæs Se cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 3
        # Verify sequential numbering
        for i, token in enumerate(tokens):
            assert token.order_index == i, f"Token at index {i} has order_index {token.order_index}, expected {i}"

    def test_no_gaps_in_numbering(self, db_session, project_and_sentence):
        """Test that there are no gaps in token numbering."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save(commit=False)
        token3 = Token(sentence_id=sentence_id, order_index=2, surface="wæs")
        token3.save()

        # Make various changes
        Token.update_from_sentence("Þā cyning", sentence_id)

        tokens = Token.list(sentence_id)
        order_indices = [token.order_index for token in tokens]
        order_indices.sort()

        # Should be sequential with no gaps
        assert order_indices == list(range(len(tokens)))

    def test_all_positions_filled(self, db_session, project_and_sentence):
        """Test that all positions are filled after update."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence("Se cyning wæs þā", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 4

        # Check that we have tokens at positions 0, 1, 2, 3
        positions = {token.order_index for token in tokens}
        assert positions == {0, 1, 2, 3}

    def test_handles_empty_sentence(self, db_session, project_and_sentence):
        """Test updating to an empty sentence."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence("", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 0

    def test_handles_single_token(self, db_session, project_and_sentence):
        """Test updating with a single token."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        Token.update_from_sentence("cyning", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 1
        assert tokens[0].surface == "cyning"
        assert tokens[0].order_index == 0

    def test_multiple_updates_preserve_numbering(self, db_session, project_and_sentence):
        """Test that multiple sequential updates maintain proper numbering."""
        _, sentence_id = project_and_sentence

        # Delete existing tokens from the fixture-created sentence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        # Create tokens manually
        token1 = Token(sentence_id=sentence_id, order_index=0, surface="Se")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
        token2.save()

        # First update
        Token.update_from_sentence("Se cyning wæs", sentence_id)
        tokens = Token.list(sentence_id)
        assert len(tokens) == 3
        for i, token in enumerate(tokens):
            assert token.order_index == i

        # Second update
        Token.update_from_sentence("Þā Se cyning", sentence_id)
        tokens = Token.list(sentence_id)
        assert len(tokens) == 3
        for i, token in enumerate(tokens):
            assert token.order_index == i

        # Third update
        Token.update_from_sentence("Se", sentence_id)
        tokens = Token.list(sentence_id)
        assert len(tokens) == 1
        assert tokens[0].order_index == 0

    def test_split_does_not_shift_following_token_annotation(self, db_session, project_and_sentence):
        """
        Splitting one token must not shift annotations from following tokens.
        """
        _, sentence_id = project_and_sentence

        # Reset fixture tokens and create a controlled sequence
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        token0 = Token(sentence_id=sentence_id, order_index=0, surface="godcundre")
        token0.save(commit=False)
        token1 = Token(sentence_id=sentence_id, order_index=1, surface="ġife")
        token1.save(commit=False)
        token2 = Token(sentence_id=sentence_id, order_index=2, surface="ġemǣred")
        token2.save()

        from oeapp.models.annotation import Annotation

        ann0 = Annotation(token_id=token0.id, pos="A")
        ann0.save(commit=False)
        ann1 = Annotation(token_id=token1.id, pos="N")
        ann1.save(commit=False)
        ann2 = Annotation(token_id=token2.id, pos="V")
        ann2.save()

        Token.update_from_sentence("god cundre ġife ġemǣred", sentence_id)

        tokens = Token.list(sentence_id)
        surfaces = [t.surface for t in tokens]
        assert surfaces == ["god", "cundre", "ġife", "ġemǣred"]

        token_by_surface = {t.surface: t for t in tokens}
        # Following tokens keep their own annotation identities.
        assert token_by_surface["ġife"].id == token1.id
        assert token_by_surface["ġemǣred"].id == token2.id

        gi_ann = Annotation.get_by_token(token_by_surface["ġife"].id)
        ge_ann = Annotation.get_by_token(token_by_surface["ġemǣred"].id)
        assert gi_ann is not None and gi_ann.pos == "N"
        assert ge_ann is not None and ge_ann.pos == "V"

    def test_merge_deletes_old_token_annotations_without_orphans(
        self, db_session, project_and_sentence
    ):
        """
        Merging tokens removes annotations of deleted tokens from the DB.
        """
        from oeapp.models.annotation import Annotation

        _, sentence_id = project_and_sentence

        # Reset fixture tokens and create controlled token sequence.
        existing_tokens = Token.list(sentence_id)
        for token in existing_tokens:
            token.delete(commit=False)
        db_session.commit()

        token0 = Token(sentence_id=sentence_id, order_index=0, surface="god")
        token0.save(commit=False)
        token1 = Token(sentence_id=sentence_id, order_index=1, surface="cundre")
        token1.save()

        ann0 = Annotation(token_id=token0.id, pos="A")
        ann0.save(commit=False)
        ann1 = Annotation(token_id=token1.id, pos="N")
        ann1.save()
        old_ann_ids = {ann0.id, ann1.id}
        old_token_ids = {token0.id, token1.id}

        # Merge two tokens into one.
        Token.update_from_sentence("godcundre", sentence_id)

        tokens = Token.list(sentence_id)
        assert len(tokens) == 1
        assert tokens[0].surface == "godcundre"

        # Old token-attached annotations must be removed.
        for old_ann_id in old_ann_ids:
            assert Annotation.get(old_ann_id) is None

        # No annotation row should point to a non-existent token.
        token_ids = {t.id for t in tokens if t.id}
        all_token_annotations = db_session.scalars(
            select(Annotation).where(Annotation.token_id.is_not(None))
        ).all()
        assert all(a.token_id in token_ids for a in all_token_annotations)

        # Sanity: old token IDs are gone.
        assert all(tid not in token_ids for tid in old_token_ids)
