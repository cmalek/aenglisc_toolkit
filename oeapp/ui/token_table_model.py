"""Qt table model for token annotation rows."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt

from oeapp.models.token import Token

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation


@dataclass(frozen=True)
class TokenTableColumn:
    """Metadata for one token table column."""

    #: Horizontal header label.
    header: str
    #: Annotation attribute name, or ``None`` for the token surface column.
    attr: str | None = None


#: Placeholder shown for empty annotation values.
EMPTY_ANNOTATION_VALUE: Final[str] = "—"

#: Token table columns in display order.
TOKEN_TABLE_COLUMNS: Final[tuple[TokenTableColumn, ...]] = (
    TokenTableColumn("Word"),
    TokenTableColumn("POS", "pos"),
    TokenTableColumn("ModE", "modern_english_meaning"),
    TokenTableColumn("Root", "root"),
    TokenTableColumn("Gender", "gender"),
    TokenTableColumn("Number", "number"),
    TokenTableColumn("Case", "case"),
    TokenTableColumn("Declension", "declension"),
    TokenTableColumn("PronounType", "pronoun_type"),
    TokenTableColumn("VerbClass", "verb_class"),
    TokenTableColumn("VerbForm", "verb_form"),
    TokenTableColumn("PrepObjCase", "prep_case"),
)


class TokenTableModel(QAbstractTableModel):
    """
    Qt model exposing token surfaces and annotation columns.

    Args:
        tokens: Tokens to display.
        parent: Parent Qt object.

    """

    def __init__(
        self,
        tokens: list[Token] | None = None,
        parent: Any = None,
    ) -> None:
        """
        Initialize model with optional token rows.

        Args:
            tokens: Tokens to display.
            parent: Parent Qt object.

        """
        super().__init__(parent)
        #: Tokens backing each table row.
        self._tokens: list[Token] = []
        #: Annotation overrides keyed by token id.
        self._annotations: dict[int, Annotation] = {}
        if tokens is not None:
            self.set_tokens(tokens)

    @property
    def tokens(self) -> list[Token]:
        """
        Return token rows currently displayed.

        Returns:
            Tokens backing table rows.

        """
        return self._tokens

    @property
    def annotations(self) -> dict[int, "Annotation"]:
        """
        Return annotation overrides keyed by token id.

        Returns:
            Annotation mapping used by update refreshes.

        """
        return self._annotations

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        """
        Return number of token rows.

        Args:
            parent: Parent model index.

        Returns:
            Token row count.

        """
        if parent is not None and parent.isValid():
            return 0
        return len(self._tokens)

    def columnCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        """
        Return number of display columns.

        Args:
            parent: Parent model index.

        Returns:
            Column count.

        """
        if parent is not None and parent.isValid():
            return 0
        return len(TOKEN_TABLE_COLUMNS)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """
        Return horizontal header text.

        Args:
            section: Header section index.
            orientation: Header orientation.
            role: Qt data role.

        Returns:
            Header text for display role, otherwise ``None``.

        """
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(TOKEN_TABLE_COLUMNS)
        ):
            return TOKEN_TABLE_COLUMNS[section].header
        return None

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """
        Return display data for one cell.

        Args:
            index: Model index to read.
            role: Qt data role.

        Returns:
            Cell display value for display role, otherwise ``None``.

        """
        if (
            role != Qt.ItemDataRole.DisplayRole
            or not index.isValid()
            or not (0 <= index.row() < len(self._tokens))
            or not (0 <= index.column() < len(TOKEN_TABLE_COLUMNS))
        ):
            return None

        token = self._tokens[index.row()]
        column = TOKEN_TABLE_COLUMNS[index.column()]
        if column.attr is None:
            return token.surface

        annotation = self._annotation_for_token(token)
        if annotation is None:
            return EMPTY_ANNOTATION_VALUE
        return getattr(annotation, column.attr) or EMPTY_ANNOTATION_VALUE

    def set_tokens(self, tokens: list[Token]) -> None:
        """
        Replace token rows and reset model data.

        Side Effects:
            Emits Qt model reset signals.

        Args:
            tokens: Tokens to display.

        """
        self.beginResetModel()
        self._tokens = list(tokens)
        self._annotations = {
            token.id: token.annotation
            for token in self._tokens
            if token.id is not None and token.annotation is not None
        }
        self.endResetModel()

    def update_annotation(self, annotation: "Annotation") -> int | None:
        """
        Update annotation data for a token row.

        Side Effects:
            Emits ``dataChanged`` for the annotation columns when token row
            exists.

        Args:
            annotation: Updated annotation.

        Returns:
            Updated row index, or ``None`` when token is not displayed.

        """
        if annotation.token_id is None:
            msg = "Token ID is required"
            raise AssertionError(msg)

        self._annotations[annotation.token_id] = annotation
        for row, token in enumerate(self._tokens):
            if token.id == annotation.token_id:
                top_left = self.index(row, 1)
                bottom_right = self.index(row, len(TOKEN_TABLE_COLUMNS) - 1)
                self.dataChanged.emit(
                    top_left,
                    bottom_right,
                    [Qt.ItemDataRole.DisplayRole.value],
                )
                return row
        return None

    def _annotation_for_token(self, token: Token) -> "Annotation | None":
        """
        Return current annotation for a token.

        Args:
            token: Token whose annotation should be displayed.

        Returns:
            Updated annotation override, token annotation, or ``None``.

        """
        if token.id is not None and token.id in self._annotations:
            return self._annotations[token.id]
        return token.annotation
