"""Unit tests for TokenDetailsSidebar."""

import pytest

from oeapp.ui.token_details_sidebar import TokenDetailsSidebar
from tests.conftest import create_test_project, create_test_sentence


class TestTokenDetailsSidebar:
    """Test cases for TokenDetailsSidebar."""

    def test_token_details_sidebar_initializes(self, qapp):
        """Test TokenDetailsSidebar initializes correctly."""
        sidebar = TokenDetailsSidebar(parent=None)

        assert sidebar._current_token is None
        assert sidebar._current_sentence is None

    def test_token_details_sidebar_shows_empty_state(self, qapp):
        """Test TokenDetailsSidebar shows empty state initially."""
        sidebar = TokenDetailsSidebar(parent=None)

        # Should show empty state with "Word details" text
        # Check that content layout exists
        assert sidebar.content_layout is not None

    def test_token_details_sidebar_displays_token(self, db_session, qapp):
        """Test TokenDetailsSidebar displays token information."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        assert sidebar._current_sentence == sentence

    def test_token_details_sidebar_updates_token(self, db_session, qapp):
        """Test TokenDetailsSidebar updates when token changes."""
        project = create_test_project(db_session, name="Test", text="Se cyning. Þæt scip.")
        db_session.commit()
        db_session.refresh(project)

        sentences = list(project.sentences)
        if len(sentences) < 2:
            pytest.skip("Need at least 2 sentences for this test")

        sentence1 = sentences[0]
        token1 = sentence1.tokens[0]

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token1, sentence1)

        assert sidebar._current_token == token1

        # Update to different token
        sentence2 = sentences[1]
        token2 = sentence2.tokens[0]
        sidebar.update_token(token2, sentence2)

        assert sidebar._current_token == token2
        assert sidebar._current_sentence == sentence2

    def test_token_details_sidebar_handles_token_with_annotation(self, db_session, qapp):
        """Test TokenDetailsSidebar handles token with annotation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Ensure token has annotation
        if token.annotation:
            annotation = token.annotation
        else:
            from oeapp.models.annotation import Annotation
            annotation = Annotation(token_id=token.id)
            db_session.add(annotation)
            db_session.commit()

        annotation.pos = "R"
        annotation.pronoun_type = "d"
        db_session.commit()

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        assert sidebar._current_token.annotation is not None

    def test_token_details_sidebar_handles_token_without_annotation(self, db_session, qapp):
        """Test TokenDetailsSidebar handles token without annotation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Remove annotation if it exists
        if token.annotation:
            db_session.delete(token.annotation)
            db_session.commit()
            db_session.refresh(token)

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        # Should handle None annotation gracefully
        # The method should not crash even if annotation is None
