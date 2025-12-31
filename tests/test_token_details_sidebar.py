"""Unit tests for TokenDetailsSidebar."""

import pytest

from oeapp.ui.token_details_sidebar import TokenDetailsSidebar
from tests.conftest import create_test_project


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

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        assert sidebar._current_sentence == sentence

    def test_token_details_sidebar_updates_token(self, db_session, qapp):
        """Test TokenDetailsSidebar updates when token changes."""
        project = create_test_project(db_session, name="Test", text="Se cyning. Þæt scip.")
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

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Ensure token has annotation
        if token.annotation:
            annotation = token.annotation
        else:
            from oeapp.models.annotation import Annotation
            annotation = Annotation(token_id=token.id)
            annotation.save(commit=False)

        annotation.pos = "R"
        annotation.pronoun_type = "d"
        annotation.save()

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        assert sidebar._current_token.annotation is not None

    def test_token_details_sidebar_handles_token_without_annotation(self, db_session, qapp):
        """Test TokenDetailsSidebar handles token without annotation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Remove annotation if it exists
        if token.annotation:
            token.annotation.delete(commit=False)
            db_session.refresh(token)

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        assert sidebar._current_token == token
        # Should handle None annotation gracefully
        # The method should not crash even if annotation is None

    def test_modern_english_meaning_formatting(self, db_session, qapp):
        """Test that Modern English Meaning is split into two labels with correct styling."""
        from PySide6.QtWidgets import QLabel
        from oeapp.models.annotation import Annotation

        project = create_test_project(db_session, name="Test", text="Se")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Ensure token has annotation with a modern meaning
        if token.annotation:
            annotation = token.annotation
        else:
            annotation = Annotation(token_id=token.id)
            annotation.save(commit=False)

        annotation.pos = "N"  # Need POS for common fields to show
        annotation.modern_english_meaning = "the king; a ruler of a people"
        annotation.save()

        sidebar = TokenDetailsSidebar(parent=None)
        sidebar.update_token(token, sentence)

        # Find the labels in the layout
        labels = []
        for i in range(sidebar.content_layout.count()):
            widget = sidebar.content_layout.itemAt(i).widget()
            if isinstance(widget, QLabel):
                labels.append(widget)

        # Look for the "Modern English Meaning:" label and the value label
        label_found = False
        value_found = False

        for i, label in enumerate(labels):
            if label.text() == "Modern English Meaning:":
                label_found = True
                # The value label should be the next QLabel
                if i + 1 < len(labels):
                    value_label = labels[i + 1]
                    if value_label.text() == "the king; a ruler of a people":
                        value_found = True
                        assert value_label.wordWrap() is True
                        assert "background-color: #888" in value_label.styleSheet()

        assert label_found is True
        assert value_found is True
