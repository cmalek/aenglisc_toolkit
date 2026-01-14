from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QComboBox, QTextEdit
from qtpy.QtWidgets import QApplication

from oeapp.ui.dialogs import (
    CaseFilterDialog,
    NumberFilterDialog,
    PartOfSpeechFilterDialog,
)

from .mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.idiom import Idiom
    from oeapp.models.token import Token
    from oeapp.ui.dialogs import SentenceFilterDialog
    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.sentence_card import SentenceCard


class SelectTokensMixin(AnnotationLookupsMixin):
    """
    Mixin for selecting tokens in the Old English text edit.
    """

    def __init__(self, card: SentenceCard):
        """
        Initialize the mixin.
        """
        #: The sentence card
        self.card = card
        #: The tokens in the sentence
        self.tokens: list[Token] = card.oe_text_edit.tokens
        #: The Old English text edit
        self.oe_text_edit: QTextEdit = card.oe_text_edit
        #: The token positions in the sentence
        self.token_positions: dict[int, tuple[int, int]] = (
            card.oe_text_edit.token_to_position
        )
        #: The tokens by index
        self.tokens_by_index: dict[int, Token] = card.oe_text_edit.tokens_by_index

    def get_token_positions(
        self, start_order: int, end_order: int
    ) -> list[tuple[int, int]]:
        """
        Get the token positions in the sentence for the range of tokens.

        A position in this case is a tuple of the start and end positions of the
        token in the sentence.

        Returns:
            List of token positions in the sentence

        """
        # Build list of token positions
        token_positions: list[tuple[int, int]] = []  # (start_pos, end_pos)
        for order_idx in range(start_order, end_order + 1):
            token = self.tokens_by_index.get(order_idx)
            if token and token.id in self.token_positions:
                token_positions.append(self.token_positions[token.id])
        return token_positions

    def select_tokens(
        self, token: Token, color: QColor
    ) -> QTextEdit.ExtraSelection | None:
        """
        Create an extra selection for highlighting a token's surface text.

        Args:
            token: Token to highlight
            color: Color to use for highlighting

        Returns:
            ExtraSelection object or None if token not found

        """
        if token.id not in self.token_positions:
            return None
        token_start, token_end = self.token_positions[token.id]
        return self.highlight_positions(token_start, token_end, color)

    def highlight_positions(
        self,
        start_pos: int,
        end_pos: int,
        color: QColor,
        highlight_property: int | None = None,
    ) -> QTextEdit.ExtraSelection:
        """
        Create an extra selection for highlighting a range of positions.

        Args:
            start_pos: Starting position
            end_pos: Ending position
            color: Color to use for highlighting

        Keyword Args:
            highlight_property: Property ID to use for highlighting. Defaults to not
              applying a property ID.

        Returns:
            Extra selection for highlighting the range of positions

        """
        assert start_pos >= 0, "Start position must be greater than 0"  # noqa: S101
        assert end_pos >= start_pos, "End position must be greater than start position"  # noqa: S101
        # Create cursor and highlight the text
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)

        # Apply highlight format
        char_format = QTextCharFormat()
        char_format.setBackground(color)
        if self.is_dark_theme:
            char_format.setForeground(self.theme_base_color)

        # Mark as selection highlight if a property is provided
        if highlight_property:
            # Mark as selection highlight
            char_format.setProperty(highlight_property, True)  # noqa: FBT003

        # Create extra selection
        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.cursor = cursor  # type: ignore[attr-defined]
        extra_selection.format = char_format  # type: ignore[attr-defined]

        return extra_selection


class HighlighterCommandBase(SelectTokensMixin):
    """
    Base class for highlighting tokens in the Old English text edit.  This is
    used as the base class for the various highlighting modes: POS, Case,
    Number, and Idioms.

    Subclasses of this base class are used by
    :class:`~oeapp.ui.highlighting.WholeSentenceHighlighter` to highlight tokens
    based on annotation data in the sentence based on the active command.

    Args:
        card: :class:`~oeapp.ui.sentence_card.SentenceCard` instance

    """

    #: Descriptive name of the highlighting mode.  This will be used in the
    #: highlighting dropdown and filter dialog.
    DESCRIPTIVE_NAME: ClassVar[str] = ""
    #: Color map for highlighting tokens, or a single color if there is no mapping
    #: needed.  This is either a string name of a color map from
    #: :class:`~oeapp.mixins.AnnotationLookupsMixin` : or a single
    #: :class:`~PySide6.QtGui.QColor`.
    COLORS: ClassVar[str | QColor] = ""
    #: Atrribute db code to human-readable name.  Set this to one of the `*_MAP`
    # attributes : From :class:`~oeapp.mixins.AnnotationLookupsMixin`.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str] | None] = None
    #: Dialog class for filtering tokens (if any)
    FILTER_DIALOG_CLASS: ClassVar[type[SentenceFilterDialog] | None] = None

    def __init__(self, highlighter: WholeSentenceHighlighter):
        super().__init__(cast("SentenceCard", highlighter.card))
        #: The highlighter
        self.highlighter = highlighter
        #: The idioms in the sentence
        self.idioms: list[Idiom] = highlighter.idioms
        #: The annotations for the tokens
        self.annotations: dict[int, Annotation | None] = highlighter.annotations
        #: The dialog instance for filtering tokens
        self.dialog: SentenceFilterDialog | None = None

    @property
    def filter_selection(self) -> set[str]:
        """
        Get the filter selection.
        """
        return self.dialog.filter_selection if self.dialog else set()

    @filter_selection.setter
    def filter_selection(self, selection: set[str]) -> None:
        """
        Set the filter selection.
        """
        if self.dialog:
            self.dialog.filter_selection = selection

    def show_filter_dialog(self) -> None:
        """
        Show the filter dialog (if any) for the command.

        """
        if not self.FILTER_DIALOG_CLASS:
            # There is no filter dialog for this command
            return
        if not self.dialog:
            self.dialog = self.FILTER_DIALOG_CLASS(parent=self.card)
            self.dialog.command = self
            # Restore selection if we have one saved
            if self.highlighter.active_index in self.highlighter.item_selections:
                self.dialog.set_selected_items(
                    self.highlighter.item_selections[self.highlighter.active_index]
                )
            self.dialog.selection_changed.connect(self._on_filter_changed)
            self.dialog.dialog_closed.connect(self._on_filter_dialog_closed)
            self.dialog.dialog_closed.connect(self.highlighter._on_filter_dialog_closed)
        self.dialog.show()

    def hide_filter_dialog(self) -> None:
        """
        Hide the filter dialog for the command.
        """
        if self.dialog:
            self.dialog.hide()

    def highlight(self) -> None:
        """
        Apply the highlighting for the command.
        """
        colors: QColor | dict[str | None, QColor]
        if isinstance(self.COLORS, QColor):
            colors = cast("QColor", self.COLORS)
        else:
            colors = self.color_map(self.COLORS)
        self.unhighlight()
        text = self.highlighter.get_oe_text()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue
            value = self.get_value(annotation)
            if not value:
                # Don't highlight if there is no value for the annotation
                continue
            if not self.dialog or value in self.filter_selection:
                if isinstance(colors, QColor):
                    color = colors
                else:
                    color = colors.get(value, colors[None])
                    if color == colors[None]:
                        # Don't highlight if the value is the default
                        continue
                if selection := self.select_tokens(token, color):
                    extra_selections.append(selection)

        self.highlighter.set_highlights(extra_selections)

    def get_value(self, annotation: Annotation) -> str | None:
        """
        Get the value of the annotation for the command.

        This is implemented by the subclasses.

        Args:
            annotation: Annotation to get the value from

        Returns:
            Value from the annotation for the command, or None if the token
            should not be highlighted, or has no value for the required
            attribute.

        """
        msg = "Subclasses must implement this method"
        raise NotImplementedError(msg)

    def unhighlight(self) -> None:
        """
        Unhighlight the tokens for the command.
        """
        self.highlighter.unhighlight()

    # Event handlers

    def _on_filter_changed(self, _: set[str]) -> None:
        """
        Handle filter selection changes.

        Args:
            selection: Set of selected codes

        """
        self.highlight()

    def _on_filter_dialog_closed(self) -> None:
        """
        Handle filter dialog close event.
        """
        self.unhighlight()


class NoneHighlighterCommand(HighlighterCommandBase):
    """
    Highlighter for no highlighting.  This is the default highlighting mode.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "None"

    def highlight(self) -> None:
        """
        Clear all highlights.
        """
        self.unhighlight()


class POSHighlighterCommand(HighlighterCommandBase):
    """
    Highlighter command for POS highlighting.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Part of Speech"
    COLORS: ClassVar[str | QColor] = "POS_COLORS"
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str] | None] = (
        AnnotationLookupsMixin.PART_OF_SPEECH_MAP
    )
    FILTER_DIALOG_CLASS = PartOfSpeechFilterDialog

    def get_value(self, annotation: Annotation) -> str | None:
        """
        Get the value of the annotation for the command.

        Args:
            annotation: Annotation to get the value from

        Returns:
            The part of speech code, or None if the token should not be
            highlighted, or has no value for the part of speech.

        """
        return annotation.pos


class CaseHighlighterCommand(HighlighterCommandBase):
    """
    Highlighter for highlighting cases in the Old English text edit.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Case"
    COLORS: ClassVar[str | QColor] = "CASE_COLORS"
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str] | None] = (
        AnnotationLookupsMixin.CASE_MAP
    )
    FILTER_DIALOG_CLASS = CaseFilterDialog

    def get_value(self, annotation: Annotation) -> str | None:
        """
        Get the value of the case for the token.

        We only highlight articles (D), nouns (N), pronouns (R), and adjectives (A)
        and prepositions (E), because these are the only tokens that can have a case.

        - For prepositions, use the :attr:`~oeapp.models.Annotation.prep_case`
          attribute.
        - For other tokens, use the :attr:`~oeapp.models.Annotation.case` attribute.

        Args:
            annotation: Annotation to get the value from

        Returns:
            The case code, or None if the token should not be highlighted, or
            has no value for the case.

        """
        pos = annotation.pos
        # Only highlight articles (D), nouns (N), pronouns (R),
        # adjectives (A), and prepositions (E)
        if pos not in ["D", "N", "R", "A", "E"]:
            return None

        # For prepositions, use prep_case; for others, use case
        return annotation.prep_case if pos == "E" else annotation.case


class NumberHighlighterCommand(HighlighterCommandBase):
    """
    Highlighter for number highlighting in the Old English text edit:
    singular, dual, and plural.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Number"
    COLORS: ClassVar[str | QColor] = "NUMBER_COLORS"
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str] | None] = (
        AnnotationLookupsMixin.NUMBER_MAP
    )
    FILTER_DIALOG_CLASS = NumberFilterDialog

    def get_value(self, annotation: Annotation) -> str | None:
        """
        Get the value of the number for the token.

        We only highlight articles (D), nouns (N), pronouns (R), and adjectives
        (A) and verbs (V), because these are the only tokens that can have a
        number.

        - For nouns, verbs, and adjectives, highlight based on the
          :attr:`~oeapp.models.Annotation.number` attribute.
        - For pronouns, highlight based on the
          :attr:`~oeapp.models.Annotation.pronoun_number` attribute.

        Args:
            annotation: Annotation to get the value from

        Returns:
            The number code, or None if the token should not be highlighted, or
            has no value for the number.

        """
        if annotation.pos not in ["D", "N", "R", "A", "V"]:
            return None
        if annotation.pos == "R":
            return annotation.pronoun_number
        return annotation.number


class IdiomHighlighterCommand(HighlighterCommandBase):
    """
    Highlighter for idiom highlighting in the Old English text edit.

    An idiom is a multi-token group that is treated as a single unit.  We highlight
    the tokens in the idiom span with a different color: light magenta.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Idiom"
    # Color for idiom highlighting
    COLORS: ClassVar[str | QColor] = AnnotationLookupsMixin.IDIOM_HIGHLIGHT_COLOR

    def highlight(self) -> None:
        """
        Highlight the tokens in the sentence based on the active command.

        Note:
            Because we're highlighting a and specifically looking at idioms, we
            can't use :meth:`HighlighterCommandBase.highlight` because it only
            highlights individual tokens.  Thus we completely override the
            method.

        """
        color = cast("QColor", self.COLORS)
        self.unhighlight()
        text = self.highlighter.get_oe_text()
        if not text or not self.tokens or not self.idioms:
            return

        extra_selections = []
        for idiom in self.idioms:
            # Highlight every token in the idiom
            start_order = idiom.start_token.order_index
            end_order = idiom.end_token.order_index
            for order_idx in range(start_order, end_order + 1):
                token = self.tokens_by_index.get(order_idx)
                if token:
                    selection = self.select_tokens(token, color)
                    if selection:
                        extra_selections.append(selection)

        self.highlighter.set_highlights(extra_selections)


class WholeSentenceHighlighter:
    """
    Highlighter for a sentence for the highlighting combo box.
    """

    #: Mapping of highlighting combo box index to highlighter command class
    HIGHLIGHTERS: ClassVar[dict[int, type[HighlighterCommandBase]]] = {
        0: NoneHighlighterCommand,
        1: POSHighlighterCommand,
        2: CaseHighlighterCommand,
        3: NumberHighlighterCommand,
        4: IdiomHighlighterCommand,
    }

    def __init__(self) -> None:
        #: The sentence card
        self.card: SentenceCard | None = None
        #: The tokens in the sentence
        self.tokens: list[Token] = []
        #: The idioms in the sentence
        self.idioms: list[Idiom] = []
        #: The annotations for the tokens
        self.annotations: dict[int, Annotation | None] = {}
        #: The active command
        self.active_command: HighlighterCommandBase | None = None
        #: The index of the active command
        self.active_index: int = 0
        #: The highlighter combo box
        self.highlighting_combo: QComboBox | None = None
        #: Initial filter selections for command filter dialogs
        self.item_selections: dict[int, set[str]] = {
            idx: cmd.FILTER_DIALOG_CLASS.full_filter_selection()
            for idx, cmd in self.HIGHLIGHTERS.items()
            if cmd.FILTER_DIALOG_CLASS is not None
        }

    @property
    def sentence_card(self) -> SentenceCard | None:
        """
        Get the Old English text edit for the sentence card.
        """
        return self.card

    @sentence_card.setter
    def sentence_card(self, value: SentenceCard) -> None:
        """
        Set the sentence card for the sentence highlighter.
        """
        self.card = value
        self.tokens = value.oe_text_edit.tokens
        self.idioms = value.oe_text_edit.idioms
        self.annotations = value.oe_text_edit.annotations

    def hide_filter_dialog(self) -> None:
        """
        Hide the filter dialog for the active command, if any.
        """
        if self.active_command:
            self.active_command.hide_filter_dialog()

    def show_filter_dialog(self) -> None:
        """
        Show the filter dialog for the active command, if any.
        """
        if self.active_command:
            self.active_command.show_filter_dialog()

    def build_combo_box(self) -> QComboBox:
        """
        Build the highlighting combo box for :attr:`card`.

        Returns:
            Highlighting combo box

        """
        self.highlighting_combo = QComboBox()
        self.highlighting_combo.addItems(
            [cmd.DESCRIPTIVE_NAME for cmd in self.HIGHLIGHTERS.values()]
        )
        self.highlighting_combo.currentIndexChanged.connect(
            self._on_highlighting_changed
        )
        return self.highlighting_combo

    def get_oe_text(self) -> str:
        """
        Get the live Old English text from our sentence card.
        """
        assert self.card, "Sentence card is required"  # noqa: S101
        return self.card.oe_text_edit.live_text

    def unhighlight(self) -> None:
        """
        Clear all highlights in our associated sentence card's OE text edit.
        """
        assert self.card, "Sentence card is required"  # noqa: S101
        assert self.highlighting_combo, (  # noqa: S101
            "You must build the highlighting combo box before calling clear_highlights"
        )
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.card.oe_text_edit.setExtraSelections([])
        # Set the active command to None
        self.active_command = NoneHighlighterCommand(self)
        # Set the active index to 0
        self.active_index = 0
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003

    def clear_active_command(self) -> None:
        """
        Clear the active command.
        """
        assert self.highlighting_combo, (  # noqa: S101
            "You must build the highlighting combo box before calling "
            "clear_active_command"
        )
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        self.active_command = NoneHighlighterCommand(self)

    def set_highlights(self, extra_selections: list[QTextEdit.ExtraSelection]) -> None:
        """
        Set the highlights for the sentence, preserving search highlights.

        Args:
            extra_selections: List of extra selections to set

        """
        assert self.card, "Sentence card is required"  # noqa: S101

        # Get existing search highlights
        existing = self.card.oe_text_edit.extraSelections()
        search_highlights = [
            s
            for s in existing
            if s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        # Combine new highlights with search highlights
        all_highlights = [*extra_selections, *search_highlights]
        self.card.oe_text_edit.setExtraSelections(all_highlights)

    def highlight(self) -> None:
        """
        Highlight the tokens in the sentence based on the active command.

        If there is no active command, do nothing.
        """
        if not self.active_command:
            return
        self.active_command.highlight()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_highlighting_changed(self, index: int) -> None:
        """
        Handle highlighting dropdown selection change.

        What this does:

        - Set the highlighting combo box to the selected index
        - Save the index as :attr:`active_index`
        - If there is an active command, hide the filter dialog (if any), and
          save the filter selection for the active command so we can restore it
          when the command is active again.
        - Set the active command to the one for the selected combo box index
        - Highlight the tokens in the sentence based on the new active command
          when the command is active again.
        - Show the filter dialog for the new active command, if any.

        Args:
            index: Selected index from the highlighting combo box

        """
        assert self.highlighting_combo, (  # noqa: S101
            "You must call build_combo_box before calling _on_highlighting_changed"
        )
        # Block signals to prevent recursive calls when updating dropdown
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(index)
        # If there is an active command, hide the filter dialog (if any) and set
        # the active command to None
        if self.active_command:
            if self.active_index in self.item_selections:
                # Save the filter selection for the active command so we can
                # restore it when the command is active again.
                self.item_selections[self.active_index] = (
                    self.active_command.filter_selection
                )
            self.active_command.hide_filter_dialog()
        # Set the active command and show the filter dialog (if any)
        self.active_index = index
        self.active_command = cast(
            "HighlighterCommandBase", self.HIGHLIGHTERS[index](self)
        )
        if self.active_command:
            self.active_command.highlight()
            self.active_command.show_filter_dialog()

    def _on_filter_dialog_closed(self) -> None:
        """
        Handle dialog close event by resetting the highlighting combo box to the
        first item, which is "No highlighting".

        Note:
            We don't need to reset the active command because it will be reset
            to None when the highlighting combo box is set to the first item.

            And we don't need to unhighlight the tokens because it will be done
            by the active command's own _on_filter_dialog_closed method.

        """
        assert self.highlighting_combo, (  # noqa: S101
            "You must call build_combo_box before calling _on_filter_dialog_closed"
        )
        self.clear_active_command()

    def _on_edit_oe_clicked(self) -> None:
        """
        Handle Edit OE button click.
        """
        self.unhighlight()
        self.hide_filter_dialog()
        self.clear_active_command()


class SingleInstanceHighlighter(SelectTokensMixin):
    """
    Highlighter for a a kind of highlight that can only appear once in the
    sentence.

    Used by :class:`~oeapp.ui.sentence_card.SentenceCard` to highlight a single
    token, idiom span or note span.

    Args:
        card: :class:`~oeapp.ui.sentence_card.SentenceCard` instance

    """

    #: Color for highlighting tokens
    COLORS: ClassVar[dict[str, QColor]] = {
        "default": QColor(200, 200, 0, 150),  # Yellow with semi-transparency
        "idiom": QColor(255, 200, 255, 150),  # Pale magenta
    }
    # Property ID for selection highlight in ExtraSelection
    HIGHLIGHT_PROPERTY: ClassVar[int] = 1001

    def __init__(self, card: SentenceCard):
        super().__init__(card)
        #: The main window
        self.main_window: MainWindow = cast("MainWindow", card.main_window)
        #: Existing extra selections
        self.existing_selections: list[QTextEdit.ExtraSelection] = []
        #: The current highlight start position
        self._current_highlight_start: int | None = None
        #: The current highlight length
        self._current_highlight_length: int | None = None

    @property
    def is_highlighted(self) -> bool:
        """
        Check if the tokens in the sentence are highlighted.
        """
        return (
            self._current_highlight_start is not None
            and self._current_highlight_length is not None
        )

    def set_existing_selections(
        self, selections: list[QTextEdit.ExtraSelection]
    ) -> None:
        """
        Set the existing extra selections, preserving search highlights.
        """
        # Get existing search highlights
        existing = self.oe_text_edit.extraSelections()
        search_highlights = [
            s
            for s in existing
            if s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        # Combine provided selections with search highlights
        all_selections = [*selections, *search_highlights]
        self.oe_text_edit.setExtraSelections(all_selections)
        self.existing_selections = [
            s
            for s in self.oe_text_edit.extraSelections()
            if not s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

    def unhighlight(self) -> None:
        """
        Unhighlight the tokens in the sentence.
        """
        filtered_selections = [
            selection
            for selection in self.existing_selections
            if not selection.format.property(self.HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]
        self.set_existing_selections(filtered_selections)
        self.reset()

    def reset(self) -> None:
        """
        Reset the current highlight to None.
        """
        self._current_highlight_start = None
        self._current_highlight_length = None

    def highlight(
        self,
        start_order: int,
        end_order: int | None = None,
        color_name: str = "default",
    ) -> None:
        """
        Highlight the token(s) in the sentence.

        Args:
            start_order: Starting token order_index (inclusive)

        Keyword Args:
            end_order: Ending token order_index (inclusive)
            color_name: Color to use for highlighting. Defaults to "default".

        """
        assert color_name in self.COLORS, "Invalid color name"  # noqa: S101
        color = self.COLORS[color_name]

        if end_order is None:
            end_order = start_order

        assert start_order is not None, "Start order must be provided"  # noqa: S101
        assert start_order <= end_order, (  # noqa: S101
            "Start order must be less or equal to end order"
        )
        assert start_order >= 0, "Start order must be greater than 0"  # noqa: S101

        self.unhighlight()

        if not self.tokens:
            return

        # Build list of token positions
        token_positions = self.get_token_positions(start_order, end_order)
        if not token_positions:
            return

        # Create highlights for all tokens in range
        range_highlights = []
        for token_start, token_end in token_positions:
            selection = self.highlight_positions(
                token_start, token_end, color, self.HIGHLIGHT_PROPERTY
            )
            range_highlights.append(selection)

        # Combine existing selections with range highlights
        all_selections = [*self.existing_selections, *range_highlights]
        self.set_existing_selections(all_selections)

        # Store range for clearing later
        first_start = token_positions[0][0]
        last_end = token_positions[-1][1]
        self._current_highlight_start = first_start
        self._current_highlight_length = last_end - first_start


class SearchHighlighter:
    """
    Highlighter for search results in a QTextEdit.
    """

    #: Color for search highlighting (bright yellow)
    SEARCH_COLOR: ClassVar[QColor] = QColor(255, 255, 0)
    #: Property ID for search highlight in ExtraSelection
    SEARCH_HIGHLIGHT_PROPERTY: ClassVar[int] = 1002

    @staticmethod
    def highlight_text(text_edit: QTextEdit, pattern: str) -> int:
        """
        Highlight all occurrences of pattern in text_edit.

        Args:
            text_edit: QTextEdit to highlight
            pattern: Search pattern

        Returns:
            int: Number of matches found

        """
        settings = QSettings()
        is_dark_theme = settings.value("theme/name", "dark", type=str) == "dark"
        # First, remove existing search highlights
        selections = text_edit.extraSelections()
        selections = [
            s
            for s in selections
            if not s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        if not pattern:
            text_edit.setExtraSelections(selections)
            return 0

        matches = 0
        doc = text_edit.document()
        cursor = QTextCursor(doc)

        while True:
            cursor = doc.find(
                pattern,
                cursor,
                QTextDocument.FindFlag.FindCaseSensitively
                if False
                else QTextDocument.FindFlag(0),
            )
            if cursor.isNull():
                break

            matches += 1

            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(SearchHighlighter.SEARCH_COLOR)  # type: ignore[attr-defined]
            if is_dark_theme:
                theme_base_color = (
                    cast("QApplication", QApplication.instance())
                    .palette()
                    .color(QPalette.ColorRole.Base)
                )
                selection.format.setForeground(theme_base_color)  # type: ignore[attr-defined]
            selection.format.setProperty(  # type: ignore[attr-defined]
                SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY,
                True,  # noqa: FBT003
            )
            selection.cursor = cursor  # type: ignore[attr-defined]
            selections.append(selection)

        text_edit.setExtraSelections(selections)
        return matches

    @staticmethod
    def clear_highlight(text_edit: QTextEdit) -> None:
        """
        Clear search highlights from ``text_edit``.

        If the text edit is read-only, do nothing.

        Args:
            text_edit: QTextEdit to clear highlights from

        """
        if text_edit.isReadOnly():
            return
        selections = text_edit.extraSelections()
        selections = [
            s
            for s in selections
            if not s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]
        text_edit.setExtraSelections(selections)
