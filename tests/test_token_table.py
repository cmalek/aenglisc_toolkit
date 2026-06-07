"""Unit tests for TokenTable."""

from oeapp.models.annotation import Annotation
from oeapp.ui.token_table import AnnotationTableWidget, TokenTable
from oeapp.ui.token_table_model import TokenTableModel
from PySide6.QtCore import Qt

from tests.conftest import create_test_project

_PREP_OBJ_CASE_COLUMN = 11

_EXPECTED_COLUMNS = [
    "Word",
    "POS",
    "ModE",
    "Root",
    "Gender",
    "Number",
    "Case",
    "Declension",
    "PronounType",
    "VerbClass",
    "VerbForm",
    "PrepObjCase",
]


def _prep_obj_case_cell_text(table: TokenTable, row: int = 0) -> str:
    """Return displayed text in the PrepObjCase column for a table row."""
    model = table.table.model()
    value = model.data(
        model.index(row, _PREP_OBJ_CASE_COLUMN), Qt.ItemDataRole.DisplayRole
    )
    if value is None:
        msg = f"PrepObjCase cell missing at row {row}"
        raise AssertionError(msg)
    return str(value)


class TestTokenTableModel:
    """Test cases for TokenTableModel."""

    def test_model_counts_rows_and_columns(self, db_session):
        """TokenTableModel reports token rows and annotation columns."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        tokens = list(project.sentences[0].tokens)

        model = TokenTableModel(tokens)

        assert model.rowCount() == len(tokens)
        assert model.columnCount() == len(_EXPECTED_COLUMNS)

    def test_model_header_data(self):
        """TokenTableModel exposes stable horizontal headers."""
        model = TokenTableModel()

        headers = [
            model.headerData(
                column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
            for column in range(model.columnCount())
        ]

        assert headers == _EXPECTED_COLUMNS

    def test_model_display_data(self, db_session):
        """TokenTableModel displays token surface and annotation values."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        token = project.sentences[0].tokens[0]
        annotation = token.annotation or Annotation(token_id=token.id)
        annotation.pos = "E"
        annotation.modern_english_meaning = "the"
        annotation.prep_case = "d"
        annotation.save()

        model = TokenTableModel([token])

        assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "Se"
        assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "E"
        assert model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "the"
        assert (
            model.data(
                model.index(0, _PREP_OBJ_CASE_COLUMN), Qt.ItemDataRole.DisplayRole
            )
            == "d"
        )

    def test_model_display_data_for_missing_annotation(self, db_session):
        """TokenTableModel displays placeholders for unannotated tokens."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        token = project.sentences[0].tokens[0]
        token.annotation = None

        model = TokenTableModel([token])

        assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "Se"
        assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "—"


class TestTokenTable:
    """Test cases for TokenTable."""

    def test_token_table_initializes(self, qapp):
        """Test TokenTable initializes correctly."""
        table = TokenTable(parent=None)

        assert len(table.tokens) == 0
        assert len(table.annotations) == 0
        assert table.table is not None
        assert isinstance(table.table.model(), TokenTableModel)

    def test_token_table_has_correct_columns(self, qapp):
        """Test TokenTable has correct column headers."""
        table = TokenTable(parent=None)

        assert table.table.columnCount() == 12
        for i, expected in enumerate(_EXPECTED_COLUMNS):
            assert (
                table.table.model().headerData(
                    i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
                )
                == expected
            )

    def test_token_table_sets_tokens(self, db_session, qapp):
        """Test TokenTable sets tokens correctly."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        assert len(table.tokens) == len(tokens)
        assert table.table.model().rowCount() == len(tokens)

    def test_token_table_updates_annotation(self, db_session, qapp):
        """Test TokenTable updates annotation correctly."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Ensure token has annotation
        if token.annotation:
            annotation = token.annotation
        else:
            annotation = Annotation(token_id=token.id)
            annotation.save(commit=False)

        annotation.pos = "R"
        annotation.save()

        table = TokenTable(parent=None)
        table.set_tokens([token])
        table.update_annotation(annotation)

        assert token.id in table.annotations
        assert table.annotations[token.id] == annotation

    def test_prep_case_in_prep_obj_case_column_after_set_tokens(
        self, db_session, qapp
    ):
        """PrepObjCase column shows prep_case after set_tokens."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        token = project.sentences[0].tokens[0]
        annotation = token.annotation or Annotation(token_id=token.id)
        annotation.pos = "E"
        annotation.prep_case = "d"
        annotation.verb_direct_object_case = "a"
        annotation.save()

        table = TokenTable(parent=None)
        table.set_tokens([token])

        assert _prep_obj_case_cell_text(table) == "d"

    def test_prep_case_in_prep_obj_case_column_after_update_annotation(
        self, db_session, qapp
    ):
        """PrepObjCase column shows prep_case after update_annotation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        token = project.sentences[0].tokens[0]
        annotation = token.annotation or Annotation(token_id=token.id)
        annotation.pos = "E"
        annotation.prep_case = "d"
        annotation.save()

        table = TokenTable(parent=None)
        table.set_tokens([token])

        annotation.prep_case = "g"
        annotation.save()
        table.update_annotation(annotation)

        assert _prep_obj_case_cell_text(table) == "g"

    def test_token_table_get_selected_token(self, db_session, qapp):
        """Test TokenTable gets selected token."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

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

    def test_token_table_get_selected_token_returns_none_with_tokens_but_no_selection(
        self, db_session, qapp
    ):
        """No selection should not default to an arbitrary token row."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)
        table.table.clearSelection()

        selected = table.get_selected_token()
        assert selected is None

    def test_token_table_emits_token_selected_signal(self, db_session, qapp):
        """Test TokenTable emits token_selected signal."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

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

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        table = TokenTable(parent=None)
        table.set_tokens(tokens)

        # Select first token
        table.select_token(0)
        assert table.current_row == 0

        # Select second token if available
        if len(tokens) > 1:
            table.select_token(1)
            assert table.current_row == 1


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
