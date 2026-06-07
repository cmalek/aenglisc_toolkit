"""Token table UI component."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt, Signal
from PySide6.QtGui import (
    QKeyEvent,
    QKeySequence,
    QShortcut,
    QShowEvent,
)  # Needed at runtime
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from oeapp.models.token import Token
from oeapp.ui.token_table_model import TokenTableModel

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.ui.main_window import MainWindow


class AnnotationTableWidget(QTableView):
    """
    Custom table view that intercepts "A" key to open annotation dialog.

    This prevents table-view incremental search from handling "A" key when a
    token is selected.

    Args:
        parent: Parent widget

    """

    #: Emitted when Shift+A is pressed while a token row is selected.
    annotation_key_pressed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the custom table widget.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        #: Parent :class:`TokenTable`, set via :meth:`set_token_table_ref`.
        self._token_table_ref: TokenTable | None = None

    def set_token_table_ref(self, token_table: "TokenTable") -> None:
        """
        Set reference to parent :class:`TokenTable` for checking selected token.

        Args:
            token_table: Reference to parent :class:`TokenTable`

        """
        self._token_table_ref = token_table

    def _get_main_window(self) -> "MainWindow | None":
        """
        Get the MainWindow by traversing the parent chain.

        Returns:
            MainWindow instance or None if not found

        """
        # Import here to avoid circular imports
        from oeapp.ui.sentence_card import SentenceCard  # noqa: PLC0415

        # Traverse parent chain to find SentenceCard, then get main_window
        widget = self.parent()
        while widget is not None:
            if isinstance(widget, SentenceCard):
                return widget.main_window
            widget = widget.parent()
        return None

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Override keyPressEvent to intercept "Shift+A" key and emit
        annotation_key_pressed signal, and to handle copy/paste shortcuts.

        If the key is not "Shift+A" or copy/paste, use default behavior
        (including incremental search).

        If no token is selected, allow default behavior (including incremental
        search).

        Args:
            event: Key event

        """
        # Check if a token is selected
        if self._token_table_ref:
            token = self._token_table_ref.get_selected_token()
            if token:
                # Handle Shift+A for annotation
                if (
                    event.key() == Qt.Key.Key_A
                    and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
                ):
                    self.annotation_key_pressed.emit()
                    event.accept()
                    return

                # Handle copy/paste shortcuts
                if event.matches(QKeySequence.StandardKey.Copy):
                    main_window = self._get_main_window()
                    if main_window:
                        main_window.action_service.copy_annotation()
                    event.accept()
                    return

                if event.matches(QKeySequence.StandardKey.Paste):
                    main_window = self._get_main_window()
                    if main_window:
                        main_window.action_service.paste_annotation()
                    event.accept()
                    return

        # For all other keys, use default behavior (including incremental search)
        super().keyPressEvent(event)

    def currentRow(self) -> int:  # noqa: N802
        """
        Return currently selected row.

        Returns:
            Selected row index, or ``-1`` when no row is selected.

        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return -1
        return selected_rows[0].row()

    def rowCount(self) -> int:  # noqa: N802
        """
        Return model row count.

        Returns:
            Number of rows in the current model.

        """
        return self.model().rowCount()

    def columnCount(self) -> int:  # noqa: N802
        """
        Return model column count.

        Returns:
            Number of columns in the current model.

        """
        return self.model().columnCount()


class TokenTable(QWidget):
    """
    Widget displaying token annotation grid.

    Args:
        parent: Parent widget

    """

    #: Signal emitted when a token is selected.
    token_selected = Signal(Token)
    #: Signal emitted when annotation is requested for a token (e.g. when "A"
    #: key is pressed on the table widget).
    annotation_requested = Signal(Token)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the token annotation table widget.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        #: The tokens to display.
        self.tokens: list[Token] = []
        #: The annotations to display.
        self.annotations: dict[
            int, "Annotation"  # noqa: UP037
        ] = {}  # token_id -> Annotation
        #: Qt table model backing the token annotation view.
        self.model = TokenTableModel(parent=self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Set up the UI layout.

        This looks like this:
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Word   | POS    | ModE   | Root   | Gender | Number | Case   | Declension | PronounType | VerbClass | VerbForm | PrepObjCase |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        | Token 1 | POS 1 | ModE 1 | Root 1 | Gender 1 | Number 1 | Case 1 | Declension 1 | PronounType 1 | VerbClass 1 | VerbForm 1 | PrepObjCase 1 |
        | Token 2 | POS 2 | ModE 2 | Root 2 | Gender 2 | Number 2 | Case 2 | Declension 2 | PronounType 2 | VerbClass 2 | VerbForm 2 | PrepObjCase 2 |
        | ...     | ...    | ...    | ...    | ...      | ...      | ...    | ...         | ...         | ...         | ...        | ...         |
        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
        """  # noqa: E501
        # Create the layout.
        layout = QVBoxLayout(self)
        # Create the custom table view that handles "A" key.
        self.table = AnnotationTableWidget(self)
        self.table.setModel(self.model)
        # Set reference to this TokenTable so the widget can check for selected token
        self.table.set_token_table_ref(self)
        # Connect the annotation key signal
        self.table.annotation_key_pressed.connect(self._on_annotation_key_pressed)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._on_index_double_clicked)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.table.setMinimumHeight(150)
        self.table.updateGeometry()
        # Add QShortcut for "A" key on the table widget with WidgetShortcut context
        # This should take precedence over incremental search
        annotate_shortcut = QShortcut(QKeySequence("A"), self.table)
        annotate_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        annotate_shortcut.activated.connect(self._on_annotation_key_pressed)
        layout.addWidget(self.table)
        index = layout.indexOf(self.table)
        layout.setStretch(index, 1)  # give table vertical priority

    @property
    def has_focus(self) -> bool:
        """
        Check if the token table has focus.

        Returns:
            ``True`` when the inner table widget has keyboard focus

        """
        return self.table.hasFocus()

    @property
    def current_row(self) -> int:
        """
        Get the current row of the token table.

        Returns:
            Zero-based index of the selected row, or ``-1`` if none

        """
        return self.table.currentRow()

    def focus(self) -> None:
        """
        Focus the token table.
        """
        self.table.setFocus()

    def setVisible(self, visible: bool) -> None:  # noqa: N802
        """
        Set the visibility of the token table.

        Args:
            visible: Whether to show the token table

        """
        super().setVisible(visible)
        self.table.setVisible(visible)
        if visible:
            self.table.setUpdatesEnabled(True)
            self.table.viewport().update()  # optional, to force a repaint

    def set_tokens(self, tokens: list[Token]) -> None:
        """
        Set tokens and annotations to display.

        Args:
            tokens: List of tokens

        """
        self.model.set_tokens(tokens)
        self.tokens = self.model.tokens
        self.annotations = self.model.annotations

    def update_annotation(self, annotation: "Annotation") -> None:
        """
        Update annotation display for a token.

        Args:
            annotation: Updated annotation

        """
        assert annotation.token_id is not None, "Token ID is required"  # noqa: S101
        self.model.update_annotation(annotation)
        self.annotations = self.model.annotations

    def get_selected_token(self) -> Token | None:
        """
        Get currently selected token.

        - If there is no selected token, return ``None``.
        - If there is a selected token, return the selected token.

        Returns:
            Selected :class:`~oeapp.models.token.Token` object or ``None``

        """
        row = self.current_row
        if 0 <= row < len(self.tokens):
            return self.tokens[row]
        return None

    def select_token(self, token_index: int) -> None:
        """
        Select a token by index, if the index is valid.  If the index is not
        valid, do nothing.

        Args:
            token_index: Index of the :class:`~oeapp.models.token.Token` object
                to select

        """
        # If the token index is valid, select the row.
        if 0 <= token_index < len(self.tokens):
            index = self.model.index(token_index, 0)
            selection_model = self.table.selectionModel()
            selection_model.setCurrentIndex(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self.table.scrollTo(index)

    def select_token_by_id(self, token_id: int | None) -> None:
        """
        Select a token by token ID.

        Args:
            token_id: Token ID to select

        """
        if token_id is None:
            return
        for row, token in enumerate(self.tokens):
            if token.id == token_id:
                self.select_token(row)
                return

    def refresh(self) -> None:
        """
        Refresh the table display from stored tokens.

        This repopulates the table with the tokens currently stored in self.tokens.
        Useful when the widget is shown again after being hidden.
        """
        if self.tokens:
            self.model.set_tokens(self.tokens)
            self.tokens = self.model.tokens
            self.annotations = self.model.annotations

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_index_double_clicked(self, index: QModelIndex) -> None:
        """
        Handle double-click on table index.

        - If the clicked row is not a token, do nothing.
        - If the clicked row is a token, emit the token_selected signal.

        Args:
            index: Clicked table index

        """
        row = index.row()
        # If the row is valid, emit the token_selected signal.
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.annotation_requested.emit(token)

    def _on_token_selected(self, token: Token) -> None:
        """
        Select a token by order index, if the order index is valid.  If the
        order index is not valid, do nothing.

        Args:
            token: Token to select

        """
        self.select_token_by_id(token.id)

    def _on_token_deselected(self) -> None:
        """
        Handle token deselection.
        """
        self.table.clearSelection()

    def _on_selection_changed(self) -> None:
        """
        Handle selection change.

        - If the selected row is not a token, do nothing.
        - If the selected row is a token, get the token and emit the
          token_selected signal.

        """
        # Get the current row of the table.
        row = self.current_row
        if 0 <= row < len(self.tokens):
            token = self.tokens[row]
            self.token_selected.emit(token)

    def _on_annotation_key_pressed(self) -> None:
        """
        Handle "A" key press on the table widget.

        Emits annotation_requested signal if a token is selected.
        """
        token = self.get_selected_token()
        if token:
            self.annotation_requested.emit(token)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """
        Handle show event to refresh table when widget becomes visible.

        Args:
            event: Show event

        """
        super().showEvent(event)
        # Always refresh table when shown if we have stored tokens
        # This handles cases where Qt clears the table when hidden
        # Check if model is empty or if we have tokens to refresh
        if self.tokens and self.model.rowCount() == 0:
            # Model is empty while stored tokens exist - refresh it
            self.refresh()
