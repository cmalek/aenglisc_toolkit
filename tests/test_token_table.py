"""Unit tests for TokenTable."""

from oeapp.ui.token_table import TokenTable, AnnotationTableWidget
from tests.conftest import create_test_project


class TestTokenTable:
    """Test cases for TokenTable."""

    def test_token_table_initializes(self, qapp):
        """Test TokenTable initializes correctly."""
        table = TokenTable(parent=None)

        assert len(table.tokens) == 0
        assert len(table.annotations) == 0
        assert table.table is not None

    def test_token_table_has_correct_columns(self, qapp):
        """Test TokenTable has correct column headers."""
        table = TokenTable(parent=None)

        expected_columns = [
            "Word", "POS", "ModE", "Root", "Gender", "Number", "Case",
            "Declension", "PronounType", "VerbClass", "VerbForm", "PrepObjCase"
        ]

        assert table.table.columnCount() == 12
        for i, expected in enumerate(expected_columns):
            assert table.table.horizontalHeaderItem(i).text() == expected

    def test_token_table_sets_tokens(self, db_session, qapp):
        """Test TokenTable sets tokens correctly."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        assert len(table.tokens) == len(tokens)
        assert table.table.rowCount() == len(tokens)

    def test_token_table_updates_annotation(self, db_session, qapp):
        """Test TokenTable updates annotation correctly."""
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
        db_session.commit()

        table = TokenTable(parent=None)
        table.set_tokens([token])
        table.update_annotation(annotation)

        assert token.id in table.annotations
        assert table.annotations[token.id] == annotation

    def test_token_table_get_selected_token(self, db_session, qapp):
        """Test TokenTable gets selected token."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        # Select first token
        table.table.selectRow(0)
        selected = table.get_selected_token()

        assert selected is not None
        assert selected == tokens[0]

    def test_token_table_get_selected_token_returns_none_when_no_selection(self, qapp):
        """Test TokenTable returns None when no token is selected."""
        table = TokenTable(parent=None)

        selected = table.get_selected_token()

        assert selected is None

    def test_token_table_emits_token_selected_signal(self, db_session, qapp):
        """Test TokenTable emits token_selected signal."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        # Connect signal
        selected_token = None
        def on_token_selected(token):
            nonlocal selected_token
            selected_token = token
        table.token_selected.connect(on_token_selected)

        # Select a token (simulate selection)
        table.select_token(0)

        assert selected_token == tokens[0]

    def test_token_table_select_token(self, db_session, qapp):
        """Test TokenTable select_token method."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        # Select first token
        table.select_token(0)
        assert table.table.currentRow() == 0

        # Select second token if available
        if len(tokens) > 1:
            table.select_token(1)
            assert table.table.currentRow() == 1


class TestAnnotationTableWidget:
    """Test cases for AnnotationTableWidget."""

    def test_annotation_table_widget_initializes(self, qapp):
        """Test AnnotationTableWidget initializes correctly."""
        widget = AnnotationTableWidget(parent=None)

        assert widget._token_table_ref is None

    def test_annotation_table_widget_sets_token_table_ref(self, qapp):
        """Test AnnotationTableWidget sets token table reference."""
        widget = AnnotationTableWidget(parent=None)
        table = TokenTable(parent=None)

        widget.set_token_table_ref(table)

        assert widget._token_table_ref == table

