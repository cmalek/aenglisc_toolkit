from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QTextEdit, QWidget

from oeapp.models import Idiom
from oeapp.ui.highlighting import SingleInstanceHighlighter, WholeSentenceHighlighter

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token
    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.sentence_card import SentenceCard


class OldEnglishTextSelector:
    """
    Selector for tokens, ranges, and idioms in the Old English text edit.

    Args:
        text_edit: Old English text edit

    """

    def __init__(self, text_edit: OldEnglishTextEdit):
        """
        Initialize the selector.
        """
        assert text_edit.sentence_card is not None, "Sentence card is required"  # noqa: S101
        #: Text edit associated with the selector
        self.text_edit = text_edit
        #: Sentence card associated with the text edit
        self.sentence_card: SentenceCard = cast("SentenceCard", text_edit.sentence_card)
        #: The sentence associated with the sentence card
        self.sentence: Sentence = cast("Sentence", text_edit.sentence)
        #: Tokens associated with the text edit
        self.tokens: list[Token] = text_edit.tokens

        #: Mapping of token order_index to index in self.tokens list
        self.order_to_list_index: dict[int, int] = text_edit.order_to_list_index
        #: Mapping of token order_index to Token object
        self.tokens_by_index: dict[int, Token] = text_edit.tokens_by_index
        #: Span highlighter for the sentence card
        self.span_highlighter = cast(
            "SingleInstanceHighlighter", text_edit.span_highlighter
        )

        #: Timer to delay deselection to allow double-click to cancel it
        self._deselect_timer = QTimer(self.text_edit)
        #: Whether the selected token range is pending deselection
        self._pending_deselect_token_range: tuple[int, int] | None = None
        #: The token index that is pending deselection
        self._pending_deselect_token_index: int | None = None
        #: The deselection timer
        self._deselect_timer.setSingleShot(True)
        self._deselect_timer.timeout.connect(self.deselect)

        #: Selected token index
        self.selected_token_index: int | None = None
        #: The selected token range
        self.selected_token_range: tuple[int, int] | None = None

    def stop_deselect_timer(self) -> None:
        """
        Stop the deselection timer.
        """
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
            self._pending_deselect_token_index = None

    def current_range(self) -> tuple[int, int] | None:
        """
        Get the current selected token range.
        """
        return self.selected_token_range

    def get_selected_tokens(self) -> tuple[Token, Token] | None:
        """
        Return the tokens that are the start and end tokens of the current
        selected range or token.

        - If a range is selected, return the start and end tokens of the range.
        - If a token is selected, return the token and itself.
        - If nothing is selected, return None.

        Raises:
            ValueError: If the start or end token is not in this sentence
            ValueError: If the start or end token has no ID
            ValueError: If the token is not in this sentence
            ValueError: If the token has no ID

        Returns:
            Tuple of start and end tokens if a range is selected, or the token
            and itself if a token is selected, or None if nothing is selected.

        """
        if self.selected_token_range is not None:
            start_token = self.tokens_by_index.get(self.selected_token_range[0])
            end_token = self.tokens_by_index.get(self.selected_token_range[1])
            if start_token is None:
                msg = (
                    f"Start token {self.selected_token_range[0]} is not in this "
                    "sentence"
                )
                raise ValueError(msg)
            if not start_token.id:
                msg = f"Start token {self.selected_token_range[0]} has no ID"
                raise ValueError(msg)
            if end_token is None:
                msg = (
                    f"End token {self.selected_token_range[1]} is not in this sentence"
                )
                raise ValueError(msg)
            if not end_token.id:
                msg = f"End token {self.selected_token_range[1]} has no ID"
                raise ValueError(msg)
            return (start_token, end_token)
        if self.selected_token_index is not None:
            token = self.tokens_by_index.get(self.selected_token_index)
            if token is None:
                msg = f"Token {self.selected_token_index} is not in this sentence"
                raise ValueError(msg)
            if not token.id:
                msg = f"Token {self.selected_token_index} has no ID"
                raise ValueError(msg)
            return (token, token)
        return None

    def current_token_index(self) -> int | None:
        """
        Get the current selected token index.
        """
        return self.selected_token_index

    def set_selected_token_index(self, index: int) -> None:
        """
        Set the selected token index.

        - Stop the deselection timer
        - Set the selected token index
        - Clear the selected token range
        """
        self.stop_deselect_timer()
        self.selected_token_index = index
        self.selected_token_range = None

    def reset_selection(self) -> None:
        """
        Reset the selected token index and range.

        - Stop the deselection timer
        - Set the selected token index to None
        - Set the selected token range to None
        """
        self.stop_deselect_timer()
        self.selected_token_index = None
        self.selected_token_range = None

    def select_tokens(self, position: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        """
        Handle click on Old English text to select corresponding token.

        Args:
            position: Position of the click in the Old English text edit
            modifiers: Modifiers pressed (Ctrl, Shift, etc.)

        """
        if not self.sentence_card:
            return
        # If in edit mode, don't handle clicks for selection
        if self.text_edit.in_edit_mode:
            return

        # Get the cursor position from the click position
        cursor = self.text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        if not self.text_edit.toPlainText() or not self.tokens:
            return

        order_index = self.text_edit.find_token_at_position(cursor_pos)
        if order_index is None:
            return

        # Cancel any pending deselection
        self.stop_deselect_timer()

        if modifiers & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier
        ):
            # Cmd/Ctrl+Click for idiom selection
            self.idiom_selection(order_index)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift+click for range selection (notes)
            self.range_selection(order_index)
        else:
            # Normal click
            self.token_selection(order_index)

    def idiom_selection(self, order_index: int) -> None:
        """
        Handle Cmd/Ctrl+Click for idiom selection.  This will start a new idiom
        selection or extend the existing idiom selection.

        Args:
            order_index: Order index of the token that was clicked

        """
        if not self.sentence_card:
            return
        highlighter = cast("SingleInstanceHighlighter", self.span_highlighter)
        # Un-highlight and deselect any currently selected or highlighted tokens
        # if we are starting a new idiom selection or if it's already selected
        # Check if we are starting a new idiom selection
        if self.selected_token_range is None:
            # Start new idiom selection
            self.selected_token_index = order_index
            self.selected_token_range = (order_index, order_index)
            # Emit signal to clear other cards and update sidebar
            token = self.tokens_by_index.get(order_index)
            if token:
                self.sentence_card.token_selected_for_details.emit(
                    token, self.sentence_card.sentence, self.sentence_card
                )
        else:
            # Extend idiom selection
            start_order, end_order = self.selected_token_range
            new_start = min(start_order, order_index)
            new_end = max(end_order, order_index)
            self.selected_token_range = (new_start, new_end)
            self.selected_token_index = new_start

        highlighter.highlight(
            self.selected_token_range[0],
            self.selected_token_range[1],
            color_name="idiom",
        )
        self.text_edit.new_idiom_selection.emit(
            self.selected_token_range[0], self.selected_token_range[1]
        )

    def range_selection(self, order_index: int) -> None:
        """
        Handle Shift+Click for range selection for Note creation and management.
        This will start a new range selection or extend the existing range
        selection.

        Args:
            order_index: Order index of the token that was clicked

        """
        if not self.sentence_card:
            return
        # Clear any active idiom selection/highlight
        self.selected_token_range = None
        self.span_highlighter.unhighlight()

        start_order = None
        end_order = None

        if self.selected_token_index is not None:
            start_order = min(self.selected_token_index, order_index)
            end_order = max(self.selected_token_index, order_index)
            self.selected_token_range = (start_order, end_order)
            self.stop_deselect_timer()
            self.selected_token_index = None
            self.span_highlighter.highlight(start_order, end_order)
        else:
            self.token_selection(order_index)
            # If token_selection set a selected_token_index, we use it as both
            # start and end
            if self.selected_token_index is not None:
                start_order = self.selected_token_index
                end_order = self.selected_token_index

        if start_order is not None and end_order is not None:
            self.text_edit.range_selection.emit(start_order, end_order)

    def token_selection(self, order_index: int) -> None:
        """
        Handle normal click for single token selection.  This will select a
        single token.

        Processing order:

        1. If click is within existing range selection, don't clear it yet.
           This allows double-click to work on the selection. Emit the range
           selection signal.
        2. Check if clicking a SAVED idiom token.  If so, select the whole idiom
           and emit the idiom selection signal. Emit the token selected signal.
        3. Standard single token selection

           a. If the clicked token is already selected, start deselection timer
              so double-click can cancel it.
           b. If the clicked token is not selected, select it and highlight it
              in the text.
           c. Emit the token selected signal.
           d. Enable the add note button.

        Args:
            order_index: Order index of the token that was clicked

        """
        if not self.sentence_card:
            return
        # 1. If click is within existing range selection, don't clear it yet.
        # This allows double-click to work on the selection.
        if self.selected_token_range:
            start, end = self.selected_token_range
            if start <= order_index <= end:
                # Clicked inside active range.
                # Start deselection timer so double-click can cancel it.
                self._pending_deselect_token_index = order_index
                self._deselect_timer.start(100)
                self.text_edit.range_selection.emit(start, end)
                return
            # Clicked outside range, clear it
            self.selected_token_range = None

        # 2. Check if clicking a SAVED idiom token
        idiom = self.text_edit.find_idiom(order_index)
        if idiom:
            self.text_edit.reset_selection()
            # Select the whole idiom
            self.selected_token_range = (
                idiom.start_token.order_index,
                idiom.end_token.order_index,
            )
            self.span_highlighter.highlight(
                self.selected_token_range[0],
                self.selected_token_range[1],
                color_name="idiom",
            )
            self.text_edit.idiom_selection.emit(idiom)
            return

        # 3. Standard single token selection
        if self.selected_token_index == order_index:
            # click on the token again to deselect it
            self._pending_deselect_token_index = order_index
            self._deselect_timer.start(100)
        else:
            self.selected_token_index = order_index
            token = self.tokens_by_index.get(order_index)
            if token:
                self.span_highlighter.highlight(token.order_index)
                self.sentence_card.token_selected_for_details.emit(
                    token, self.sentence, self.sentence_card
                )
                list_index = self.order_to_list_index.get(order_index)
                if list_index is not None:
                    self.sentence_card.token_table.select_token(list_index)
                self.text_edit.token_selected.emit(token)

    def deselect(self) -> None:
        """
        Perform deselection if still pending. Called by timer after delay.

        This means:

        - Deselect the token if the selected token index still matches
        - Clear the selected token range if it exists and the click was inside it
        - Clear the highlight
        - Disable the add note button
        - Emit signal to clear sidebar (main window will handle it)
        """
        if not self.sentence_card:
            return
        if self._pending_deselect_token_index is not None:
            order_index = self._pending_deselect_token_index
            # Only deselect if the token index still matches or click was in range
            # Case 1: Single token selection matches
            if self.selected_token_index == order_index:
                self.text_edit.reset_selection()
                # Emit signal to clear sidebar
                token = self.tokens_by_index.get(order_index)
                if token:
                    self.sentence_card.token_selected_for_details.emit(
                        token, self.sentence_card.sentence, self.sentence_card
                    )

            # Case 2: Range selection exists and click was inside it
            elif self.selected_token_range:
                start, end = self.selected_token_range
                if start <= order_index <= end:
                    self.text_edit.reset_selection()
                    # Emit signal to clear sidebar
                    token = self.tokens_by_index.get(order_index)
                    if token:
                        self.sentence_card.token_selected_for_details.emit(
                            token, self.sentence_card.sentence, self.sentence_card
                        )

            self._pending_deselect_token_index = None


class OldEnglishTextEdit(QTextEdit):
    """
    QTextEdit that is tailored editing, navigation, and annotating
    Old English text.

    This currently handles:

    - Mouse clicks
    - Double mouse clicks
    - Key presses for annotation copy/paste
    - Navigation by tokens

    """

    # =======================
    # Signals
    # =======================

    # Signal emitted when a token is clicked
    clicked = Signal(QPoint, object)  # position, modifiers
    # Signal emitted when a token is double-clicked
    double_clicked = Signal(QPoint)
    # Signal emitted when a token is selected
    token_selected = Signal(object)
    # Range selection signal
    range_selection = Signal(int, int)
    # Idiom selection signal
    idiom_selection = Signal(Idiom)
    # New Idiom selection signal
    new_idiom_selection = Signal(int, int)
    # Signal emitted when a token is deselected
    token_deselected = Signal()

    # =======================
    # Constants
    # =======================

    #: Property ID for token index in QTextCharFormat
    TOKEN_INDEX_PROPERTY: Final[int] = 1000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Start read-only by default
        self.setReadOnly(True)
        #: Whether the text edit is in edit mode
        self._edit_mode: bool = False
        #: Sentence Card associated with this text edit
        self._sentence_card: SentenceCard | None = None
        #: Main Window associated with this text edit
        self._main_window: MainWindow | None = None

        #: The sentence associated with this text edit
        self.sentence: Sentence | None = None
        #: Tokens associated with this text edit
        self.tokens: list[Token] = []
        #: Idioms associated with this text edit
        self.idioms: list[Idiom] = []

        #: Mapping of token order_index to Token object
        self.tokens_by_index: dict[int, Token] = {}
        #: Mapping of token ID to Token object
        self.tokens_by_id: dict[int, Token] = {}
        #: Mapping of token order_index to index in self.tokens list
        self.order_to_list_index: dict[int, int] = {}
        #: Token to position in the text editor
        self.token_to_position: dict[int, tuple[int, int]] = {}

        #: Original Old English text
        self._original_oe_text: str | None = None

        #: The span highlighter for the QTextEdit
        self.span_highlighter: SingleInstanceHighlighter | None = None
        #: The sentence highlighter for the QTextEdit
        self.sentence_highlighter: WholeSentenceHighlighter | None = None
        #: Token selector associated with this text edit
        self.selector: OldEnglishTextSelector | None = None

    @property
    def sentence_card(self) -> SentenceCard | None:
        """
        Sentence Card associated with this text edit.
        """
        return self._sentence_card

    @sentence_card.setter
    def sentence_card(self, value: SentenceCard) -> None:
        """
        Set the sentence card associated with this text edit.

        Args:
            value: Sentence card

        """
        if value is self._sentence_card:
            return
        if self._sentence_card is not None:
            self.disconnect_signals()
        self._sentence_card = value
        self._main_window = value.main_window
        assert self._main_window is not None, "Main window is required"  # noqa: S101
        self.sentence_highlighter = value.sentence_highlighter
        self.sentence = value.sentence
        self.set_tokens()
        self.span_highlighter = SingleInstanceHighlighter(value)
        self.selector = OldEnglishTextSelector(self)
        self.clicked.connect(self.selector.select_tokens)
        QTimer.singleShot(0, self.render_readonly_text)
        self.connect_signals()

    def disconnect_signals(self) -> None:
        """
        Disconnect signals from sentence card, token table, and token details
        sidebar.
        """
        if not self._sentence_card:
            return

        # Sentence card
        self.token_deselected.disconnect(self._sentence_card.reset_selected_token)
        self.new_idiom_selection.disconnect(self._sentence_card._on_idiom_selection)
        self.token_selected.disconnect(self._sentence_card._on_token_selection)
        self.range_selection.disconnect(self._sentence_card._on_range_selection)

        # Token table
        self.token_selected.disconnect(
            self._sentence_card.token_table._on_token_selected
        )
        self.token_deselected.disconnect(
            self._sentence_card.token_table._on_token_deselected
        )

        # Token details sidebar
        self.token_selected.disconnect(
            cast(
                "MainWindow", self._main_window
            ).token_details_sidebar._on_token_selected
        )
        self.token_deselected.disconnect(
            cast(
                "MainWindow", self._main_window
            ).token_details_sidebar._on_token_deselected
        )

    def connect_signals(self) -> None:
        """
        Connect signals to sentence card, token table, and token details
        sidebar.
        """
        if not self._sentence_card:
            return

        token_details_sidebar = cast(
            "MainWindow", self._main_window
        ).token_details_sidebar
        token_table = self._sentence_card.token_table

        # Sentence card
        self.token_selected.connect(self._sentence_card._on_token_selection)
        self.token_deselected.connect(self._sentence_card.reset_selected_token)
        self.idiom_selection.connect(self._sentence_card._on_idiom_selection)
        self.new_idiom_selection.connect(self._sentence_card._on_idiom_selection)
        self.range_selection.connect(self._sentence_card._on_range_selection)

        # Token table
        self.token_selected.connect(token_table._on_token_selected)
        self.token_deselected.connect(token_table._on_token_deselected)

        # Token details sidebar
        self.token_selected.connect(token_details_sidebar._on_token_selected)
        self.idiom_selection.connect(token_details_sidebar._on_idiom_selected)
        self.token_deselected.connect(token_details_sidebar._on_token_deselected)

    @property
    def in_edit_mode(self) -> bool:
        """
        Whether the text edit is in edit mode (read-only or editable).
        """
        return self._edit_mode

    @in_edit_mode.setter
    def in_edit_mode(self, value: bool) -> None:
        assert self.sentence is not None, "Sentence is required"  # noqa: S101
        self._edit_mode = value
        if value:
            self.setReadOnly(False)
            self.reset_selection()
            self._original_oe_text = self.sentence_text
            cast("SingleInstanceHighlighter", self.span_highlighter).unhighlight()
            cast("WholeSentenceHighlighter", self.sentence_highlighter).unhighlight()
            self.render_editable_text(self._original_oe_text)
        else:
            self.setReadOnly(True)
            self._original_oe_text = None
            self.render_readonly_text()
            cast("WholeSentenceHighlighter", self.sentence_highlighter).highlight()

    @property
    def sentence_text(self) -> str:
        """
        The OE text of the sentence associated with this text edit.
        """
        if self.sentence:
            return cast("Sentence", self.sentence).text_oe
        return ""

    @property
    def live_text(self) -> str:
        """
        The actual text in the text edit.
        """
        return self.toPlainText()

    @property
    def selected_tokens(self) -> tuple[Token, Token] | None:
        """
        Get the selected tokens.

        Raises:
            ValueError: If the start or end token is not in this sentence
            ValueError: If the start or end token has no ID
            ValueError: If the token is not in this sentence
            ValueError: If the token has no ID

        Returns:
            Tuple of start and end tokens if a range is selected, or the token
            and itself if a token is selected, or None if nothing is selected.

        """
        if self.selector:
            return self.selector.get_selected_tokens()
        return None

    def highlight_span_by_token_ids(
        self, start_token_id: int, end_token_id: int
    ) -> None:
        """
        Highlight a span of tokens by their IDs.

        Raises:
            ValueError: If the start or end token is not in this sentence
            ValueError: If the start or end token has no ID

        Args:
            start_token_id: Start token ID
            end_token_id: End token ID

        """
        start_token = self.tokens_by_id.get(start_token_id)
        end_token = self.tokens_by_id.get(end_token_id)
        if start_token is None:
            msg = f"Start token {start_token_id} is not in this sentence"
            raise ValueError(msg)
        if end_token is None:
            msg = f"End token {end_token_id} is not in this sentence"
            raise ValueError(msg)
        if self.span_highlighter:
            self.span_highlighter.highlight(
                start_token.order_index, end_token.order_index
            )

    def highlight_note(self, note: Note) -> None:
        """
        Highlight a note by its ID.

        If the note has no start or end token, do nothing.

        Raises:
            ValueError: If the start or end token is not in this sentence
            ValueError: If the start or end token has no ID

        Args:
            note: Note to highlight

        """
        if note.start_token and note.end_token:
            self.highlight_span_by_token_ids(note.start_token, note.end_token)

    def stop_deselect_timer(self) -> None:
        """
        Stop the deselection timer.
        """
        if self.selector:
            self.selector.stop_deselect_timer()

    def current_range(self) -> tuple[int, int] | None:
        """
        Get the current selected token range.
        """
        if self.selector:
            return self.selector.current_range()
        return None

    def current_token_index(self) -> int | None:
        """
        Get the current selected token index.
        """
        if self.selector:
            return self.selector.selected_token_index
        return None

    def set_selected_token_index(self, index: int, emit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Set the selected token index and highlight the token.

        If ``emit`` is ``True``, also emit the :attr:`token_selected` signal.
        Otherwise, only highlight the token.

        Args:
            index: Token index to set
            emit: Whether to emit the :attr:`token_selected` signal

        """
        if self.selector:
            self.selector.set_selected_token_index(index)
            cast("SingleInstanceHighlighter", self.span_highlighter).highlight(index)
            if emit:
                token = self.tokens_by_index.get(index)
                self.token_selected.emit(token)

    def reset_selection(self) -> None:
        """
        Reset the selected token.

        - Reset the selected token index and range
        - Clear the highlight
        - Emit the token deselected signal
        """
        if self.span_highlighter:
            self.stop_deselect_timer()
            self.span_highlighter.unhighlight()
            if self.selector:
                self.selector.reset_selection()

    def highlight_sentence(self) -> None:
        """
        Highlight the sentence.

        - Highlight the sentence
        - Show the filter dialog (if any)
        """
        if self.sentence_highlighter:
            self.sentence_highlighter.highlight()
            self.sentence_highlighter.show_filter_dialog()

    # -------------------------------------------------------------------------
    # Text rendering methods
    # -------------------------------------------------------------------------

    def restore_original_text(self) -> None:
        """
        Restore the original text.

        - Restore the original text to the sentence
        - Render the read-only text
        - Clear the saved original text
        - Emit the text changed signal
        """
        if self._original_oe_text is not None:
            cast("Sentence", self.sentence).text_oe = self._original_oe_text
            self.render_readonly_text()
            self._original_oe_text = None

    def resize_to_fit_text(self) -> None:
        """
        Resize the text edit to fit the text and its superscripts with a 20% margin.

        This is used to ensure the text edit is the correct height to fit the
        text and its superscripts.
        """
        # set the maximum height of the oe_text_edit to just fit the text
        # and its superscripts
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(int(height))

    def render_editable_text(self, text: str) -> None:
        """
        Render editable OE text.

        Args:
            text: Text to render

        """
        self.setPlainText(text)

    def render_readonly_text(self) -> None:
        """
        Render OE text with note superscripts and idiom italics.

        This is the method we use to render the OE text with note superscripts
        and idiom italics, for reading.  We use a different method to render it
        for editing.

        Only renders superscripts when NOT in edit mode.
        """
        if self.in_edit_mode or not self.sentence_card:
            return

        sentence = cast("Sentence", self.sentence_card.sentence)
        highlighter = cast("SingleInstanceHighlighter", self.span_highlighter)

        # Ensure relationships are loaded
        try:
            if sentence.id:
                self.sentence_card.session.refresh(
                    self.sentence, ["notes", "idioms", "tokens"]
                )
        except Exception:  # noqa: BLE001
            return

        self.token_to_position.clear()
        self.clear()
        cursor = QTextCursor(self.document())

        tokens, token_id_to_start = sentence.sorted_tokens
        token_to_notes = sentence.token_to_note_map
        idiom_token_ids = self.get_all_idiom_token_ids()

        last_pos = 0
        text = self.sentence_text
        for token in tokens:
            token_id = cast("int", token.id)
            token_start = token_id_to_start[token_id]
            token_end = token_start + len(token.surface)

            if token_start < last_pos:
                continue

            # Insert text before token
            if token_start > last_pos:
                cursor.insertText(text[last_pos:token_start], QTextCharFormat())

            # Render token
            self.render_token(
                cursor, token, token_start, token_end, idiom_token_ids, token_to_notes
            )
            last_pos = token_end

        # Insert remaining text
        if last_pos < len(text):
            cursor.insertText(text[last_pos:], QTextCharFormat())

        # Restore highlight if a token was selected
        current_token_index = self.current_token_index()
        if current_token_index is not None:
            token = cast("Token", self.tokens_by_index.get(current_token_index))
            if token:
                highlighter.highlight(token.order_index)
        self.resize_to_fit_text()

    def render_token(  # noqa: PLR0913
        self,
        cursor: QTextCursor,
        token: Token,
        token_start: int,
        token_end: int,
        idiom_token_ids: set[int],
        token_to_notes: dict[int, list[int]],
    ) -> None:
        """
        Render a single token with its formatting and superscripts.

        Args:
            cursor: QTextCursor to render the token in
            token: Token to render
            token_start: Start position of the token in the text
            token_end: End position of the token in the text
            idiom_token_ids: Set of token IDs that are part of an idiom
            token_to_notes: Dictionary of token IDs to list of note IDs

        """
        if not self.sentence_card:
            return
        token_id = cast("int", token.id)
        text = self.sentence_text

        # Token format (italics if in idiom)
        token_format = QTextCharFormat()
        token_format.setProperty(self.TOKEN_INDEX_PROPERTY, token.order_index)
        if token_id in idiom_token_ids:
            token_format.setFontItalic(True)

        # Insert token text
        editor_token_start = cursor.position()
        cursor.insertText(text[token_start:token_end], token_format)
        self.token_to_position[token_id] = (
            editor_token_start,
            cursor.position(),
        )

        # Insert superscripts
        if token_id in token_to_notes:
            self.render_superscripts(cursor, token_to_notes[token_id])

    def render_superscripts(self, cursor: QTextCursor, note_numbers: list[int]) -> None:
        """
        Render note superscripts.

        Args:
            cursor: QTextCursor to render the superscripts in
            note_numbers: List of note numbers to render

        """
        super_format = QTextCharFormat()
        super_format.setVerticalAlignment(
            QTextCharFormat.VerticalAlignment.AlignSuperScript
        )
        font = super_format.font()
        super_format.setFont(font)
        cursor.insertText(",".join(map(str, note_numbers)), super_format)

    # -------------------------------------------------------------------------
    # Token related methods
    # -------------------------------------------------------------------------

    def set_tokens(self) -> None:
        """
        Set the tokens for the text edit, and highlight the sentence
        with the sentence highlighter.

        This populates the following attributes:

        - :attr:`tokens`
        - :attr:`idioms`
        - :attr:`tokens_by_index`
        - :attr:`order_to_list_index`
        - :attr:`annotations`

        """
        # Ensure tokens are sorted by their position in the text
        # We always use the sentence's sorted_tokens as the source of truth for order
        # as requested in the plan.
        sentence = cast("Sentence", self.sentence)
        sorted_tokens, _ = sentence.sorted_tokens
        self.tokens = sorted_tokens
        self.idioms = sentence.idioms

        self.tokens_by_index = {t.order_index: t for t in self.tokens}
        self.tokens_by_id = {t.id: t for t in self.tokens}
        self.order_to_list_index = {t.order_index: i for i, t in enumerate(self.tokens)}
        self.annotations = {
            cast("int", token.id): token.annotation for token in self.tokens if token.id
        }
        cast("WholeSentenceHighlighter", self.sentence_highlighter).highlight()

    def get_token(self, order_index: int) -> Token | None:
        """
        Get a token by its order index.
        """
        assert self.tokens_by_index is not None, "Tokens by index is required"  # noqa: S101
        return self.tokens_by_index.get(order_index)

    def get_selected_token(self) -> Token | None:
        """
        Get the selected token.
        """
        if not self.sentence_card:
            return None
        current_token_index = self.current_token_index()
        if current_token_index is None:
            return None
        return self.tokens_by_index.get(current_token_index)

    def find_token_at_position(self, position: int) -> int | None:
        """
        Find the token index that contains the given character position.

        Uses the custom :attr:`TOKEN_INDEX_PROPERTY` stored in the
        :class:`QTextCharFormat`.  Checks both the character after and before
        the cursor to handle edge clicks.

        Args:
            position: Character position in the document

        Returns:
            Token index if found, None otherwise

        """
        if not self.tokens:
            return None

        # Get the cursor at the position
        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(position)

        # 1. Try character AFTER the cursor (preferred for clicks on left half of char)
        if position < doc.characterCount() - 1:
            test_cursor = QTextCursor(doc)
            test_cursor.setPosition(position)
            test_cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
            )
            fmt = test_cursor.charFormat()
            val = fmt.property(self.TOKEN_INDEX_PROPERTY)
            if val is not None:
                return cast("int", val)

        # 2. Try character BEFORE the cursor (for clicks on right half of char)
        fmt = cursor.charFormat()
        val = fmt.property(self.TOKEN_INDEX_PROPERTY)
        if val is not None:
            return cast("int", val)

        return None

    def find_idiom(
        self, start_index: int, end_index: int | None = None
    ) -> Idiom | None:
        """
        If ``end_index`` is ``None``, find an idiom that covers the given
        ``start_index``.  Otherwise, find an idiom that exactly matches the
        given range of tokens ``[start_index, end_index]``, inclusive.

        Args:
            start_index: Start order index of the token to check
            end_index: End order index of the token to check

        Returns:
            Idiom that covers the given token order index

        """
        if not self.idioms:
            return None
        if end_index is None:
            for idiom in self.idioms:
                if (
                    idiom.start_token.order_index
                    <= start_index
                    <= idiom.end_token.order_index
                ):
                    return idiom
            return None
        for idiom in self.idioms:
            if (
                idiom.start_token.order_index == start_index
                and idiom.end_token.order_index == end_index
            ):
                return idiom
        return None

    def get_all_idiom_token_ids(self) -> set[int]:
        """
        Get set of all token IDs that are part of an idiom.

        Returns:
            Set of all token IDs that are part of an idiom

        """
        idiom_token_ids = set()
        for idiom in self.idioms:
            # We need to find all tokens between start and end
            start_token = idiom.start_token
            end_token = idiom.end_token
            if not start_token or not end_token:
                continue

            # Find tokens in this range by order_index
            start_order = start_token.order_index
            end_order = end_token.order_index
            for token in self.tokens:
                if start_order <= token.order_index <= end_order:
                    idiom_token_ids.add(cast("int", token.id))
        return idiom_token_ids

    def next_token(self) -> None:
        """
        Navigate to next token in the sentence and in the token table.

        - If no token is selected, do nothing.
        - If the last token is selected, do nothing.
        """
        if not self.sentence_card:
            return
        selector = cast("OldEnglishTextSelector", self.selector)
        selected_token_index = selector.current_token_index()
        if not self.tokens or selected_token_index is None:
            return

        current_list_index = self.order_to_list_index.get(selected_token_index)
        if current_list_index is not None and current_list_index < len(self.tokens) - 1:
            next_list_index = current_list_index + 1
        else:
            # Already at last token or invalid index
            return

        token = self.tokens[next_list_index]
        self.set_selected_token_index(token.order_index)
        self.sentence_card.token_selected_for_details.emit(
            token, self.sentence_card.sentence, self.sentence_card
        )

    def prev_token(self) -> None:
        """
        Navigate to previous token in the sentence and in the token table.

        - If no token is selected, do nothing.
        - If the first token is selected, do nothing.
        """
        if not self.sentence_card:
            return
        selector = cast("OldEnglishTextSelector", self.selector)
        selected_token_index = selector.current_token_index()
        if not self.tokens or selected_token_index is None:
            return

        current_list_index = self.order_to_list_index.get(selected_token_index)
        if current_list_index is not None and current_list_index > 0:
            prev_list_index = current_list_index - 1
        else:
            # Already at first token or invalid index
            return

        token = self.tokens[prev_list_index]
        self.set_selected_token_index(token.order_index)
        self.sentence_card.token_selected_for_details.emit(
            token, self.sentence_card.sentence, self.sentence_card
        )

    # -------------------------------------------------------------------------
    # Annotation related methods
    # -------------------------------------------------------------------------

    def copy_annotation(self) -> None:
        """Handle copy annotation request from OE text edit."""
        selector = cast("OldEnglishTextSelector", self.selector)
        if (
            self.sentence_card
            and selector.current_token_index() is not None
            and self._main_window
        ):
            self._main_window.action_service.copy_annotation()

    def paste_annotation(self) -> None:
        """Handle paste annotation request from OE text edit."""
        selector = cast("OldEnglishTextSelector", self.selector)
        if (
            self.sentence_card
            and selector.current_token_index() is not None
            and self._main_window
        ):
            self._main_window.action_service.paste_annotation()

    def annotate_token(self, position: QPoint) -> None:
        """
        Annotate the token at the given position.

        Args:
            position: Mouse double-click position in the Old English text edit
                widget coordinates

        """
        if not self.sentence_card:
            return
        # If in edit mode, don't handle double-clicks for annotation
        if self.in_edit_mode:
            return
        token_selector = cast("OldEnglishTextSelector", self.selector)

        # Get cursor at click position
        cursor = self.cursorForPosition(position)
        cursor_pos = cursor.position()

        # Find which token contains this cursor position
        order_index = self.find_token_at_position(cursor_pos)
        if order_index is None:
            return

        # Cancel any pending deselection timer from the first click
        token_selector.stop_deselect_timer()

        # Check if click is already inside current selection
        current_range = token_selector.current_range()
        in_range = current_range and current_range[0] <= order_index <= current_range[1]
        current_token_index = token_selector.current_token_index()
        is_selected = current_token_index == order_index

        if not (in_range or is_selected):
            # Select the token/idiom first (e.g. if double-clicking an unselected token)
            cast("OldEnglishTextSelector", self.selector).token_selection(order_index)
            # Cancel the timer started by token selection
            token_selector.stop_deselect_timer()

        # Then open the annotation modal (handles both tokens and idioms correctly)
        self.sentence_card._open_annotation_modal()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse press event and emit clicked signal.

        Args:
            event: Mouse press event

        """
        super().mousePressEvent(event)
        self.clicked.emit(event.position().toPoint(), event.modifiers())

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse double-click event and open the annotation modal.

        Args:
            event: Mouse double-click event

        """
        super().mouseDoubleClickEvent(event)
        self.annotate_token(event.position().toPoint())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Handle key press events.

        If we are in read-only mode, handle arrow keys and copy/paste shortcuts
        here so the user can navigate by tokens instead of by characters, and
        so the copy and paste shortcuts work.(Cmd/Ctrl+C and Cmd/Ctrl+V) copy/past
        annotations when a token is selected.

        If we are in edit mode, handle the keys normally.

        Args:
            event: Key event

        """
        # Shortcut handling (Copy/Paste)
        if self.isReadOnly():
            if event.matches(QKeySequence.StandardKey.Copy):
                self.copy_annotation()
                event.accept()
                return
            if event.matches(QKeySequence.StandardKey.Paste):
                self.paste_annotation()
                event.accept()
                return

        # Navigation and Annotation handling
        if self.isReadOnly():
            # Navigation and Annotation handling
            if event.key() in (
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                if self.current_token_index() is not None:
                    # If right arrow key is pressed, navigate to next token
                    if event.key() == Qt.Key.Key_Right:
                        self.next_token()
                        event.accept()
                        return
                    # If left arrow key is pressed, navigate to previous token
                    if event.key() == Qt.Key.Key_Left:
                        self.prev_token()
                        event.accept()
                        return
                    # If Enter/Return is pressed, open annotation modal
                    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        if self.sentence_card:
                            cast(
                                "SentenceCard", self.sentence_card
                            )._open_annotation_modal()
                        event.accept()
                        return
                else:
                    # If no token is selected, ignore the key press so it bubbles up
                    event.ignore()
                    return

        # Default behavior for all other cases (including edit mode)
        super().keyPressEvent(event)
