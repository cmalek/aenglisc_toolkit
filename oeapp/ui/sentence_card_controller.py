"""Sentence card user-action workflow and annotation modal routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from PySide6.QtWidgets import QMessageBox

from oeapp.commands import (
    AddSentenceCommand,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
)
from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.commands.paragraph import MergeParagraphCommand, SplitParagraphCommand
from oeapp.models import Annotation, Idiom
from oeapp.models.sentence import Sentence
from oeapp.ui.dialogs import AnnotationModal
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from oeapp.models.token import Token
    from oeapp.ui.sentence_card import SentenceCard


@dataclass(frozen=True)
class HierarchyPosition:
    """Where a sentence sits in the paragraph/section/chapter hierarchy."""

    #: Whether the sentence is the first in its paragraph.
    is_paragraph_start: bool
    #: Whether the sentence's paragraph is the first in its section.
    is_section_start: bool
    #: Whether the sentence's paragraph's section is the first in its chapter.
    is_chapter_start: bool


class SentenceCardController:
    """
    Coordinate sentence-card command execution and annotation modal routing.

    Args:
        card: Sentence card widget whose user actions are handled.

    """

    def __init__(self, card: SentenceCard) -> None:
        """
        Initialize controller for a sentence card.

        Args:
            card: Sentence card widget whose user actions are handled.

        """
        #: Sentence card widget whose user actions are handled.
        self.card = card

    def on_edit_oe_clicked(self) -> None:
        """
        Enter Old English edit mode and update related button visibility.
        """
        card = self.card
        card.edit_oe_button.setVisible(False)
        card.add_note_button.setVisible(False)
        card.save_oe_button.setVisible(True)
        card.cancel_edit_button.setVisible(True)
        card.oe_text_edit.in_edit_mode = True
        card.edit_mode_started.emit()

    def on_save_oe_clicked(self) -> None:
        """
        Save Old English edits through the command manager and exit edit mode.
        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            card.oe_text_edit.render_readonly_text()
            return

        new_text = card.oe_text_edit.live_text
        old_text = card.sentence.text_oe

        if new_text != old_text:
            command = EditSentenceCommand(
                sentence_id=card.sentence.id,
                field="text_oe",
                before=old_text,
                after=new_text,
            )
            if card.command_manager.execute(command):
                card.sentence.text_oe = new_text
                if hasattr(command, "messages") and command.messages:
                    for msg in command.messages:
                        if card.main_window:
                            card.main_window.messages.show_message(msg, duration=5000)

                card.session.refresh(card.sentence)
                card.set_tokens()
                card.notes_panel.update_notes()

        card.oe_text_edit.in_edit_mode = False
        card.save_oe_button.setVisible(False)
        card.cancel_edit_button.setVisible(False)
        card.edit_oe_button.setVisible(True)
        card.add_note_button.setVisible(True)
        card.edit_mode_finished.emit()

    def on_cancel_edit_clicked(self) -> None:
        """
        Discard Old English edits and exit edit mode.
        """
        card = self.card
        card.oe_text_edit.restore_original_text()
        card.oe_text_edit.in_edit_mode = False
        card.save_oe_button.setVisible(False)
        card.cancel_edit_button.setVisible(False)
        card.edit_oe_button.setVisible(True)
        card.add_note_button.setVisible(True)
        card.edit_mode_finished.emit()

    def on_translation_changed(self) -> None:
        """
        Save Modern English translation changes through the command manager.
        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            return

        new_text = card.translation_edit.toPlainText()
        old_text = card.sentence.text_modern or ""

        if new_text != old_text:
            command = EditSentenceCommand(
                sentence_id=card.sentence.id,
                field="text_modern",
                before=old_text,
                after=new_text,
            )
            if card.command_manager.execute(command):
                card.sentence.text_modern = new_text

    def on_merge_clicked(self) -> None:
        """
        Merge the current sentence with the next sentence after confirmation.
        """
        card = self.card
        if not card.sentence.id:
            return

        next_sentence = Sentence.get_next_sentence(
            card.sentence.project_id, card.sentence.display_order + 1
        )
        if next_sentence is None:
            QMessageBox.warning(
                card,
                "No Next Sentence",
                "There is no next sentence to merge with.",
            )
            return

        message = (
            f"Merge sentence {card.sentence.display_order} "
            f"with sentence {next_sentence.display_order}?\n\n"
            f"This will combine the Old English text, Modern English translation, "
            f"tokens, annotations, and notes from both sentences."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Merge",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            card,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        if not card.command_manager:
            QMessageBox.warning(
                card,
                "Error",
                "Command manager not available. Cannot perform merge.",
            )
            return

        before_text_oe = card.sentence.text_oe
        before_text_modern = card.sentence.text_modern

        command = MergeSentenceCommand(
            current_sentence_id=card.sentence.id,
            next_sentence_id=next_sentence.id,
            before_text_oe=before_text_oe,
            before_text_modern=before_text_modern,
        )

        if card.command_manager.execute(command):
            if card.sentence.id:
                card.sentence_merged.emit(card.sentence.id)
        else:
            QMessageBox.warning(
                card,
                "Merge Failed",
                "Failed to merge sentences. Please try again.",
            )

    def on_add_sentence_before_clicked(self) -> None:
        """
        Add a new empty sentence before the current sentence.
        """
        self._add_sentence(position="before")

    def on_add_sentence_after_clicked(self) -> None:
        """
        Add a new empty sentence after the current sentence.
        """
        self._add_sentence(position="after")

    def _add_sentence(self, *, position: Literal["before", "after"]) -> None:
        """
        Execute an add-sentence command for the configured position.

        Keyword Args:
            position: Relative position ("before" or "after").

        """
        card = self.card
        if not card.sentence.id or not card.command_manager:
            return

        command = AddSentenceCommand(
            project_id=card.sentence.project_id,
            reference_sentence_id=card.sentence.id,
            position=position,
        )

        if card.command_manager.execute(command):
            if command.new_sentence_id:
                card.sentence_added.emit(command.new_sentence_id)
        else:
            QMessageBox.warning(
                card,
                "Add Sentence Failed",
                "Failed to add sentence. Please try again.",
            )

    def on_delete_clicked(self) -> None:
        """
        Delete the current sentence after confirmation.
        """
        card = self.card
        if not card.sentence.id or not card.command_manager:
            return

        message = (
            f"Delete sentence {card.sentence.display_order}?\n\n"
            f"This will permanently delete the sentence, including its "
            f"Old English text, Modern English translation, tokens, "
            f"annotations, and notes. This action can be undone."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Delete",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            card,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        command = DeleteSentenceCommand(
            sentence_id=card.sentence.id,
        )

        if card.command_manager.execute(command):
            if card.sentence.id:
                card.sentence_deleted.emit(card.sentence.id)
        else:
            QMessageBox.warning(
                card,
                "Delete Failed",
                "Failed to delete sentence. Please try again.",
            )

    def get_hierarchy_position(self, sentence: Sentence) -> HierarchyPosition:
        """
        Classify where a sentence sits in the paragraph/section/chapter hierarchy.

        Args:
            sentence: Sentence to classify.

        Returns:
            The sentence's hierarchy position.

        """
        if not sentence.paragraph:
            return HierarchyPosition(
                is_paragraph_start=False,
                is_section_start=False,
                is_chapter_start=False,
            )

        sentences = sorted(
            sentence.paragraph.sentences, key=lambda s: s.display_order
        )
        is_paragraph_start = bool(sentences) and sentences[0].id == sentence.id

        is_section_start = False
        if is_paragraph_start:
            paragraphs = sorted(
                sentence.paragraph.section.paragraphs, key=lambda p: p.order
            )
            is_section_start = (
                bool(paragraphs) and paragraphs[0].id == sentence.paragraph.id
            )

        is_chapter_start = False
        if is_section_start:
            sections = sorted(
                sentence.paragraph.section.chapter.sections, key=lambda s: s.number
            )
            is_chapter_start = (
                bool(sections)
                and sections[0].id == sentence.paragraph.section.id
            )

        return HierarchyPosition(
            is_paragraph_start=is_paragraph_start,
            is_section_start=is_section_start,
            is_chapter_start=is_chapter_start,
        )

    def on_split_paragraph_clicked(self) -> bool:
        """
        Execute a split-paragraph command for the current sentence.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            return False
        return card.command_manager.execute(
            SplitParagraphCommand(sentence_id=card.sentence.id)
        )

    def on_merge_paragraph_clicked(self) -> bool:
        """
        Execute a merge-paragraph command for the current sentence.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.id:
            return False
        return card.command_manager.execute(
            MergeParagraphCommand(sentence_id=card.sentence.id)
        )

    def on_split_section_clicked(self) -> bool:
        """
        Execute a split-section command for the current sentence's paragraph.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.paragraph:
            return False
        return card.command_manager.execute(
            SplitSectionCommand(paragraph_id=card.sentence.paragraph.id)
        )

    def on_merge_section_clicked(self) -> bool:
        """
        Execute a merge-section command for the current sentence's paragraph.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if not card.command_manager or not card.sentence.paragraph:
            return False
        return card.command_manager.execute(
            MergeSectionCommand(paragraph_id=card.sentence.paragraph.id)
        )

    def on_split_chapter_clicked(self) -> bool:
        """
        Execute a split-chapter command for the current sentence's section.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if (
            not card.command_manager
            or not card.sentence.paragraph
            or not card.sentence.paragraph.section
        ):
            return False
        return card.command_manager.execute(
            SplitChapterCommand(section_id=card.sentence.paragraph.section.id)
        )

    def on_merge_chapter_clicked(self) -> bool:
        """
        Execute a merge-chapter command for the current sentence's section.

        Returns:
            True if the command executed successfully, else False.

        """
        card = self.card
        if (
            not card.command_manager
            or not card.sentence.paragraph
            or not card.sentence.paragraph.section
        ):
            return False
        return card.command_manager.execute(
            MergeChapterCommand(section_id=card.sentence.paragraph.section.id)
        )

    def open_annotation_modal(self) -> None:
        """
        Resolve the current selection and open the appropriate annotation modal.
        """
        card = self.card
        current_range = card.oe_text_edit.current_range()
        if current_range:
            start_order, end_order = current_range
            idiom = card.oe_text_edit.find_idiom(start_order, end_order)
            if idiom:
                card._open_idiom_modal(idiom)
                return

            card._open_new_idiom_modal(start_order, end_order)
            return

        token: Token | None = card.oe_text_edit.get_selected_token()
        card.oe_text_edit.current_token_index()
        if not token:
            token = card.token_table.get_selected_token()

        if not token:
            if card.oe_text_edit.tokens:
                token = card.oe_text_edit.tokens[0]
                card.token_table.select_token(0)
            else:
                return

        idiom = card.oe_text_edit.find_idiom(token.order_index)
        if idiom:
            card._open_idiom_modal(idiom)
            return

        card._open_token_modal(token)

    def open_idiom_modal(self, idiom: Idiom) -> None:
        """
        Open the annotation modal for an existing idiom.

        Args:
            idiom: Idiom to annotate.

        """
        card = self.card
        annotation = idiom.annotation
        if annotation is None:
            annotation = Annotation(idiom_id=idiom.id)

        modal = AnnotationModal(
            idiom=idiom,
            annotation=annotation,
            parent=card,
            main_window=card.main_window,
        )
        modal.annotation_applied.connect(card._on_annotation_applied)
        modal.exec()

    def open_new_idiom_modal(self, start_order: int, end_order: int) -> None:
        """
        Open the annotation modal for a newly selected idiom range.

        Args:
            start_order: Start token order index.
            end_order: End token order index.

        """
        card = self.card
        start_token = card.oe_text_edit.get_token(start_order)
        end_token = card.oe_text_edit.get_token(end_order)
        if not start_token or not end_token:
            return

        idiom = Idiom(
            sentence_id=card.sentence.id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )
        idiom.start_token = start_token
        idiom.end_token = end_token

        annotation = Annotation()

        modal = AnnotationModal(
            idiom=idiom,
            annotation=annotation,
            parent=card,
            main_window=card.main_window,
        )
        modal.annotation_applied.connect(card._on_idiom_annotation_applied)
        modal.exec()

    def open_token_modal(self, token: Token) -> None:
        """
        Open the annotation modal for a single token.

        Args:
            token: Token to annotate.

        """
        card = self.card
        annotation = token.annotation
        if annotation is None and token.id:
            annotation = Annotation.get_by_token(token.id)

        modal = AnnotationModal(
            token=token,
            annotation=annotation,
            parent=card,
            main_window=card.main_window,
        )
        modal.annotation_applied.connect(card._on_annotation_applied)
        modal.exec()
