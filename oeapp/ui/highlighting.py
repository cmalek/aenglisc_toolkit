from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QTextEdit

from oeapp.ui.dialogs.sentence_filters import (
    CaseFilterDialog,
    NumberFilterDialog,
    PartOfSpeechFilterDialog,
)

from .mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from collections.abc import Callable

    from oeapp.models.annotation import Annotation
    from oeapp.models.idiom import Idiom
    from oeapp.models.token import Token
    from oeapp.ui.dialogs.sentence_filters import SentenceFilterDialog
    from oeapp.ui.sentence_card import SentenceCard


class HighligherCommandBase(AnnotationLookupsMixin):
    """
    Base class for highlighting tokens in the Old English text edit.  This is
    used as the base class for the various highlighting modes: POS, Case,
    Number, and Idioms.

    Args:
        card: :class:`~oeapp.ui.sentence_card.SentenceCard` instance

    """

    #: Descriptive name of the highlighting mode.  This will be used in the
    #: highlighting dropdown and filter dialog.
    DESCRIPTIVE_NAME: ClassVar[str] = ""
    #: Color map for highlighting tokens, or a single color if there is no mapping
    #: needed.
    COLORS: ClassVar[dict[str | None, QColor] | QColor | None] = None
    #: Atrribute db code to human-readable name.  Set this to one of the `*_MAP`
    # attributes : From :class:`~oeapp.mixins.AnnotationLookupsMixin`.
    CODE_TO_NAME_MAPPING: ClassVar[dict[str | None, str] | None] = None
    #: Dialog class for filtering tokens (if any)
    FILTER_DIALOG_CLASS: ClassVar[type[SentenceFilterDialog] | None] = None

    def __init__(self, highligher: SentenceHighligher):
        #: The highlighter
        self.highligher = highligher
        #: The sentence card
        self.card = highligher.card
        #: The tokens in the sentence
        self.tokens: list[Token] = highligher.tokens
        #: The idioms in the sentence
        self.idioms: list[Idiom] = highligher.idioms
        #: The annotations for the tokens
        self.annotations: dict[int, Annotation | None] = highligher.annotations
        #: The Old English text edit
        self.oe_text_edit: QTextEdit = highligher.card.oe_text_edit
        #: The token selection helper
        self.select_tokens: Callable[
            [Token, QColor], QTextEdit.ExtraSelection | None
        ] = highligher.card._create_token_selection
        #: The tokens by index
        self.tokens_by_index: dict[int, Token] = highligher.card.tokens_by_index
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
            if self.highligher.active_index in self.highligher.item_selections:
                self.dialog.set_selected_items(
                    self.highligher.item_selections[self.highligher.active_index]
                )
            self.dialog.selection_changed.connect(self._on_filter_changed)
            self.dialog.dialog_closed.connect(self._on_filter_dialog_closed)
            self.dialog.dialog_closed.connect(self.highligher._on_filter_dialog_closed)
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
            colors = cast("dict[str | None, QColor]", self.COLORS)
        self.unhighlight()
        text = self.highligher.get_oe_text()
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

        self.highligher.set_highlights(extra_selections)

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
        self.highligher.clear_highlights()

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


class NoneHighligherCommand(HighligherCommandBase):
    """
    Highlighter command for none highlighting.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "None"

    def highlight(self) -> None:
        """
        Clear all highlights.
        """
        self.unhighlight()


class POSHighligherCommand(HighligherCommandBase):
    """
    Highlighter command for POS highlighting.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Part of Speech"
    COLORS: ClassVar[dict[str | None, QColor] | QColor | None] = (
        AnnotationLookupsMixin.POS_COLORS
    )
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


class CaseHighligherCommand(HighligherCommandBase):
    """
    Highlighter command for case highlighting.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Case"
    COLORS: ClassVar[dict[str | None, QColor] | QColor | None] = (
        AnnotationLookupsMixin.CASE_COLORS
    )
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


class NumberHighligherCommand(HighligherCommandBase):
    """
    Highlighter command for number highlighting.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Number"
    COLORS: ClassVar[dict[str | None, QColor] | QColor | None] = (
        AnnotationLookupsMixin.NUMBER_COLORS
    )
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


class IdiomHighligherCommand(HighligherCommandBase):
    """
    Highlighter command for idiom highlighting.

    An idiom is a multi-token group that is treated as a single unit.
    """

    DESCRIPTIVE_NAME: ClassVar[str] = "Idiom"
    # Color for idiom highlighting
    COLORS: ClassVar[dict[str | None, QColor] | QColor | None] = (
        AnnotationLookupsMixin.IDIOM_HIGHLIGHT_COLOR
    )

    def highlight(self) -> None:
        """
        Highlight the tokens in the sentence based on the active command.

        Note:
            Because we're highlighting a and specifically looking at idioms, we
            can't use :meth:`HighligherCommandBase.highlight` because it only
            highlights individual tokens.  Thus we completely override the
            method.

        """
        color = cast("QColor", self.COLORS)
        self.unhighlight()
        text = self.highligher.get_oe_text()
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

        self.highligher.set_highlights(extra_selections)


class SentenceHighligher:
    """
    Highlighter for a sentence.
    """

    #: Mapping of highlighting combo box index to highlighter command class
    HIGHLIGHTERS: ClassVar[dict[int, type[HighligherCommandBase]]] = {
        0: NoneHighligherCommand,
        1: POSHighligherCommand,
        2: CaseHighligherCommand,
        3: NumberHighligherCommand,
        4: IdiomHighligherCommand,
    }

    def __init__(self, card: SentenceCard):
        #: The sentence card
        self.card = card
        #: The tokens in the sentence
        self.tokens: list[Token] = card.tokens
        #: The idioms in the sentence
        self.idioms: list[Idiom] = card.idioms
        #: The annotations for the tokens
        self.annotations: dict[int, Annotation | None] = card.annotations
        #: The active command
        self.active_command: HighligherCommandBase | None = None
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
        Get the Old English text from our sentence card.
        """
        return self.card.oe_text_edit.toPlainText()

    def clear_highlights(self) -> None:
        """
        Clear all highlights in our associated sentence card's OE text edit.
        """
        assert self.highlighting_combo, (  # noqa: S101
            "You must build the highlighting combo box before calling clear_highlights"
        )
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.card._clear_all_highlights()
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003

    def set_highlights(self, extra_selections: list[QTextEdit.ExtraSelection]) -> None:
        """
        Set the highlights for the sentence.

        Args:
            extra_selections: List of extra selections to set

        """
        self.card.oe_text_edit.setExtraSelections(extra_selections)

    def highlight(self) -> None:
        """
        Highlight the tokens in the sentence based on the active command.

        If there is no active command, do nothing.
        """
        if not self.active_command:
            return
        self.active_command.highlight()

    # Event handlers

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
            "HighligherCommandBase", self.HIGHLIGHTERS[index](self)
        )
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
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
