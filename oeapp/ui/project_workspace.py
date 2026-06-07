"""Project workspace UI workflow for chapter/section navigation and reload."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

from oeapp.models.project import Project
from oeapp.ui.sentence_card import SentenceCard

if TYPE_CHECKING:
    from oeapp.commands import CommandManager
    from oeapp.models.annotation import Annotation
    from oeapp.models.idiom import Idiom
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token
    from oeapp.services import AutosaveService
    from oeapp.ui.main_window import MainWindow


class ProjectUI:
    """
    Build out the UI for a particular project inside the main window.

    Important:
        Only run ``ProjectUI(main_window).load(project_id)`` once the main
        window has been built, because it needs to access the main window's
        content+layout.

    Args:
        main_window: Main window hosting project navigation and sentence cards.

    """

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize project workspace UI workflow.

        Args:
            main_window: Main window hosting project widgets.

        """
        #: Main window hosting navigation combos and sentence cards.
        self.main_window = main_window
        #: Shared app context for current ids and command manager.
        self.app_context = main_window.app_context
        #: Main window actions used for command manager access.
        self.action_service = main_window.action_service
        #: Command manager for sentence-level undoable edits.
        self.command_manager = self.action_service.command_manager
        #: Sentence cards currently loaded for the active section.
        self.sentence_cards: list[SentenceCard] = []
        #: Sentence card currently selected for token/idiom details in this workspace.
        self.selected_sentence_card: SentenceCard | None = None
        #: Layout hosting sentence cards in the main scroll area.
        self.content_layout: QVBoxLayout = cast(
            "QVBoxLayout", self.main_window.content_layout
        )
        #: Token details sidebar on the main window.
        self.token_details_sidebar = main_window.token_details_sidebar
        #: Status message helper bound to the main window.
        self.show_message = main_window.messages.show_message
        #: Warning message helper bound to the main window.
        self.show_warning = main_window.messages.show_warning
        #: Error message helper bound to the main window.
        self.show_error = main_window.messages.show_error
        #: Information message helper bound to the main window.
        self.show_information = main_window.messages.show_information

    @property
    def autosave_service(self) -> AutosaveService | None:
        """
        Get the autosave service owned by the main window.

        Returns:
            Autosave service when configured, else ``None``.

        """
        return self.main_window.autosave_service

    def load(self, project: Project, clear_search: bool = True) -> None:
        """
        Build the project.

        Args:
            project: Project to load
            clear_search: Whether to clear the search toolbar

        """
        # Clear or re-apply search
        if clear_search:
            self.main_window._clear_search_without_focus_restore()
        else:
            self.main_window.action_service.perform_search(
                self.main_window.search_input.text(),
                self.main_window.search_scope_combo.currentText(),
            )

        if self.main_window.autosave_service:
            self.main_window.autosave_service.cancel()

        self.app_context.current_project_id = project.id

        # Update chapter dropdown
        self.main_window.chapter_combo.blockSignals(True)  # noqa: FBT003
        self.main_window.chapter_combo.clear()
        for chapter in project.chapters:
            self.main_window.chapter_combo.addItem(chapter.display_title, chapter.id)
        self.main_window.chapter_combo.blockSignals(False)  # noqa: FBT003

        # Select first chapter if available
        if project.chapters:
            self.main_window.chapter_combo.setCurrentIndex(0)
            chapter_id = project.chapters[0].id
            self.app_context.current_chapter_id = chapter_id
            self.update_sections_for_chapter(chapter_id)
        else:
            # Handle empty project (should not happen with new logic)
            self.main_window.section_combo.clear()
            self._clear_content()

    def update_sections_for_chapter(self, chapter_id: int) -> None:
        """
        Update section dropdown for the given chapter.

        Args:
            chapter_id: Chapter whose sections should populate the combo.

        """
        # Import here to avoid circular import
        from oeapp.models.chapter import Chapter  # noqa: PLC0415

        chapter = Chapter.get(chapter_id)
        if not chapter:
            return

        self.main_window.section_combo.blockSignals(True)  # noqa: FBT003
        self.main_window.section_combo.clear()
        for section in chapter.sections:
            self.main_window.section_combo.addItem(section.display_title, section.id)
        self.main_window.section_combo.blockSignals(False)  # noqa: FBT003

        if chapter.sections:
            self.main_window.section_combo.setCurrentIndex(0)
            section_id = chapter.sections[0].id
            self.app_context.current_section_id = section_id
            self.load_section(section_id)
        else:
            self._clear_content()

    def load_section(self, section_id: int) -> None:
        """
        Load sentences for the given section.

        Args:
            section_id: Section whose sentences should be shown.

        """
        # Import here to avoid circular import
        from oeapp.models.section import Section  # noqa: PLC0415

        section = Section.get(section_id)
        if not section:
            return

        self.clear_selected_sentence_card()
        self._clear_content()
        self.sentence_cards = []
        self.main_window.sentence_cards = []

        for paragraph in section.paragraphs:
            # Add paragraph separator if not the first paragraph in section
            if paragraph.order > 1:
                self._add_paragraph_separator()

            for sentence in paragraph.sentences:
                card = SentenceCard(
                    sentence,
                    command_manager=self.app_context.command_manager,
                    main_window=self.main_window,
                )
                self.sentence_cards.append(card)
                self.main_window.sentence_cards.append(card)
                self.content_layout.addWidget(card)
                self._connect_card_signals(card)

    def find_sentence_card(self, sentence_id: int) -> SentenceCard | None:
        """
        Find a loaded sentence card by sentence id.

        Args:
            sentence_id: Target sentence id.

        Returns:
            Matching sentence card when loaded, else ``None``.

        """
        for card in self.sentence_cards:
            if card.sentence.id == sentence_id:
                return card
        return None

    def get_selected_sentence_card(self) -> SentenceCard | None:
        """
        Get the workspace-local selected sentence card.

        Returns:
            Selected sentence card, or ``None`` when no card is selected.

        """
        return self.selected_sentence_card

    def set_selected_sentence_card(self, sentence_card: SentenceCard) -> None:
        """
        Store the workspace-local selected sentence card.

        Args:
            sentence_card: Sentence card selected for token or idiom details.

        """
        self.selected_sentence_card = sentence_card

    def clear_selected_sentence_card(self) -> None:
        """Clear the workspace-local selected sentence card."""
        self.selected_sentence_card = None

    def _set_combo_to_data(self, combo: QComboBox, target_id: int) -> bool:
        """
        Set combo current index by item data id.

        Args:
            combo: Combo box to update.
            target_id: Item data id to activate.

        Returns:
            ``True`` when target exists in combo, else ``False``.

        """
        for index in range(combo.count()):
            if combo.itemData(index) == target_id:
                combo.setCurrentIndex(index)
                return True
        return False

    def navigate_to_sentence(
        self, chapter_id: int, section_id: int, sentence_id: int
    ) -> SentenceCard | None:
        """
        Load chapter/section for a sentence and return its sentence card.

        Args:
            chapter_id: Target chapter id.
            section_id: Target section id.
            sentence_id: Target sentence id.

        Returns:
            Loaded sentence card when found, else ``None``.

        """
        if not self._set_combo_to_data(self.main_window.chapter_combo, chapter_id):
            return None
        if not self._set_combo_to_data(self.main_window.section_combo, section_id):
            return None
        return self.find_sentence_card(sentence_id)

    def _clear_content(self) -> None:
        """Clear existing content from the layout."""
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def _add_paragraph_separator(self) -> None:
        """Add a paragraph separator to the layout."""
        separator = QWidget()
        separator.setFixedHeight(20)
        palette = separator.palette()
        mid = palette.color(QPalette.ColorRole.Mid)
        h, s, v, a = mid.getHsv()  # type: ignore[misc]
        v = min(v, 255)  # type: ignore[has-type]
        v = int((v + 255 + 20) % 255)
        background = QColor.fromHsv(h, s, v, a)  # type: ignore[has-type]
        h, s, v, a = mid.getHsv()  # type: ignore[misc]
        v = min(v, 0)  # type: ignore[has-type]
        v = int((v + 255 + 20) % 255)
        border = QColor.fromHsv(h, s, v, a)  # type: ignore[has-type]
        separator.setStyleSheet(
            f"background-color: {background.name()}; "
            f"border-top: 2px solid {border.name()};"
            f"border-bottom: 2px solid {border.name()};"
        )
        self.content_layout.addWidget(separator)

    def _connect_card_signals(self, card: SentenceCard) -> None:
        """
        Connect signals for a sentence card.

        Args:
            card: Sentence card whose signals should be wired.

        """
        card.translation_edit.textChanged.connect(self._on_translation_changed)
        card.oe_text_edit.textChanged.connect(self._on_sentence_text_changed)
        card.sentence_merged.connect(self._on_sentence_merged)
        card.sentence_added.connect(self._on_sentence_added)
        card.sentence_deleted.connect(self._on_sentence_deleted)
        card.token_selected_for_details.connect(self._on_token_selected_for_details)
        card.idiom_selected_for_details.connect(self._on_idiom_selected_for_details)
        card.annotation_applied.connect(self._on_annotation_applied)
        card.edit_mode_started.connect(
            lambda: self.main_window.update_search_ui_state(True)  # noqa: FBT003
        )
        card.edit_mode_finished.connect(
            lambda: self.main_window.update_search_ui_state(False)  # noqa: FBT003
        )
        card.edit_mode_started.connect(
            self.main_window._clear_search_without_focus_restore
        )

    def _can_reload_current_project(self) -> bool:
        """
        Return whether the workspace can reload the active project.

        Returns:
            ``True`` when session and current project id are available.

        """
        return (
            bool(self.app_context.session) and self.app_context.has_current_project()
        )

    def _restore_command_manager_on_cards(
        self, command_manager: CommandManager | None,
    ) -> None:
        """
        Restore command manager identity on workspace and sentence cards.

        Args:
            command_manager: Command manager instance to preserve across reload.

        """
        if command_manager:
            self.command_manager = command_manager  # type: ignore[assignment]

        for card in self.sentence_cards:
            card.command_manager = self.command_manager

    def _reload_after_structure_change(
        self,
        *,
        clear_search: bool,
        message: str | None = None,
    ) -> bool:
        """
        Reload project structure after merge/add/delete while preserving undo.

        Keyword Args:
            clear_search: Whether to clear search state before reload.
            message: Optional status message shown after reload.

        Returns:
            ``True`` when reload completed, else ``False``.

        """
        if not self._can_reload_current_project():
            return False

        project_id = self.app_context.current_project_id
        if project_id is None:
            return False

        project = Project.get(project_id)
        if project is None:
            return False

        existing_command_manager = self.app_context.command_manager

        self.load(project, clear_search=clear_search)

        self._restore_command_manager_on_cards(existing_command_manager)

        self.main_window.reload_main_window()

        if message:
            self.show_message(message, duration=2000)
        return True

    def reload(self) -> None:
        """
        Reload the entire project structure from database.

        This is needed after structural changes like merge/undo merge
        that change the number of sentences.
        """
        self._reload_after_structure_change(clear_search=False)

    def refresh(self) -> None:
        """
        Refresh all sentence cards from database.

        - If there is no database or the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        if not self._can_reload_current_project():
            return
        # Reload annotations for all cards
        for card in self.sentence_cards:
            if card.sentence.id:
                card.set_tokens()

        # Re-apply search highlighting after refresh
        self.main_window.action_service.perform_search(
            self.main_window.search_input.text(),
            self.main_window.search_scope_combo.currentText(),
        )

    def save(self) -> None:
        """
        Save current project.
        """
        if not self._can_reload_current_project():
            self.show_warning("No project open")
            return
        if self.autosave_service:
            self.autosave_service.save_now()
            self.show_message("Project saved")
        else:
            self.show_information("Project saved (autosave enabled)", title="Info")

    def _on_translation_changed(self) -> None:
        """
        Handle translation text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def _on_sentence_text_changed(self) -> None:
        """
        Handle sentence text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def _on_sentence_merged(self) -> None:
        """
        Handle sentence merge signal.

        Reloads the project from the database to refresh all sentence cards
        after a merge operation.

        """
        self._reload_after_structure_change(
            clear_search=False,
            message="Sentences merged",
        )

    def _on_sentence_added(self, sentence_id: int) -> None:
        """
        Handle sentence added signal.

        Reloads the project from the database to refresh all sentence cards
        after adding a new sentence, then puts the new sentence card in edit mode.

        Args:
            sentence_id: ID of the newly added sentence

        """
        if not self._reload_after_structure_change(clear_search=True):
            return

        new_card = self.find_sentence_card(sentence_id)

        if new_card:
            # Defer focus to the next event-loop cycle so it is not overridden
            # by immediate post-load UI updates.
            _new_card = cast("SentenceCard", new_card)

            def _focus_new_card(card: SentenceCard = _new_card) -> None:
                self.main_window.ensure_visible(card)
                card.enter_edit_mode()
                card.flash_added()

            QTimer.singleShot(0, _focus_new_card)

        self.show_message("Sentence added", duration=2000)

    def _on_sentence_deleted(self, sentence_id: int) -> None:  # noqa: ARG002
        """
        Handle sentence deleted signal.

        Reloads the project from the database to refresh all sentence cards
        after a deletion operation.

        Args:
            sentence_id: ID of the deleted sentence

        """
        self._reload_after_structure_change(
            clear_search=False,
            message="Sentence deleted",
        )

    def _on_token_selected_for_details(
        self, token: Token, sentence: Sentence, sentence_card: SentenceCard
    ) -> None:
        """
        Handle token selection for details sidebar.

        Args:
            token: Selected token
            sentence: Sentence containing the token
            sentence_card: Sentence card containing the token

        """
        # Clear selection on all other sentence cards to ensure only one selection
        # exists across the entire project view
        for other_card in self.sentence_cards:
            if other_card != sentence_card:
                other_card.clear_token_selection()

        # Check if token is being deselected (selected_token_index is None)
        if sentence_card.oe_text_edit.current_token_index() is None:
            # Clear sidebar
            self.token_details_sidebar.clear_sidebar()
            self.clear_selected_sentence_card()
        else:
            # Update sidebar with token details
            self.token_details_sidebar.render_token(token, sentence)

            # Store reference to currently selected sentence card
            self.set_selected_sentence_card(sentence_card)

    def _on_idiom_selected_for_details(
        self, idiom: Idiom, sentence: Sentence, sentence_card: SentenceCard
    ) -> None:
        """
        Handle idiom selection for details sidebar.

        Args:
            idiom: Selected idiom
            sentence: Sentence containing the idiom
            sentence_card: Sentence card containing the idiom

        """
        # Clear selection on all other sentence cards
        for other_card in self.sentence_cards:
            if other_card != sentence_card:
                other_card.clear_token_selection()

        # Update sidebar with idiom details
        self.token_details_sidebar.render_idiom(idiom, sentence)

        # Store reference to currently selected sentence card
        self.set_selected_sentence_card(sentence_card)

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        If the annotation is for the currently selected token in the sidebar,
        refresh the sidebar.

        Args:
            annotation: Applied annotation

        """
        # Check if this annotation is for the currently selected token
        if not self.app_context.has_current_project():
            return
        card = self.get_selected_sentence_card()
        if card is None:
            return
        order_index = card.oe_text_edit.current_token_index()
        if order_index is None:
            return
        token = card.oe_text_edit.tokens_by_index.get(order_index)
        if token and token.id == annotation.token_id:
            # Refresh sidebar with updated annotation
            # Refresh token from database to ensure annotation relationship
            # is up-to-date
            if self.app_context.session:
                self.app_context.session.refresh(token)
            self.token_details_sidebar.render_token(token, card.sentence)
