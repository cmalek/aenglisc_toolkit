"""Unit tests for MainWindow."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QSplitter, QStatusBar, QWidget

from oeapp.state import AppContext
from oeapp.ui.main_window import MainWindow, Messages


@pytest.fixture
def mock_services():
    """Fixture to mock MigrationService and BackupService."""
    with (
        patch("oeapp.ui.main_window.MigrationService") as mock_mig,
        patch("oeapp.ui.main_window.BackupService") as mock_back,
    ):
        mock_mig_instance = mock_mig.return_value
        mock_mig_instance.migrate.return_value = MagicMock(
            migration_version="abc",
            app_version="1.0.0",
        )
        yield mock_mig, mock_back


@pytest.fixture
def main_window(qapp, db_session, mock_services):
    """Fixture to create a MainWindow instance with mocked services."""
    window = MainWindow(app_context=AppContext(session=db_session))
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


class TestMainWindowInitialization:
    """Test cases for MainWindow initialization and basic layout."""

    def test_initialization(self, main_window):
        """Test MainWindow initializes with correct basic properties."""
        assert main_window.windowTitle() == "Ænglisc Toolkit"
        assert main_window.centralWidget() is not None
        assert main_window.token_details_sidebar is not None
        assert main_window.content_layout is not None
        assert isinstance(main_window.statusBar(), QStatusBar)

    def test_show_empty_state(self, main_window):
        """Test that the empty state is shown on startup."""
        welcome_label = None
        for i in range(main_window.content_layout.count()):
            widget = main_window.content_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and "Welcome" in widget.text():
                welcome_label = widget
                break

        assert welcome_label is not None
        assert not welcome_label.isHidden()


class TestMainWindowActions:
    """Test cases for MainWindowActions logic."""

    def test_navigation_next_prev_sentence(self, main_window):
        """Test next_sentence and prev_sentence navigation logic."""
        actions = main_window.action_service

        mock_card1 = MagicMock()
        mock_card2 = MagicMock()
        mock_card3 = MagicMock()

        actions.sentence_cards.extend([mock_card1, mock_card2, mock_card3])

        for card in [mock_card1, mock_card2, mock_card3]:
            card.has_focus = False

        actions.next_sentence()
        mock_card1.focus.assert_called_once()

        mock_card1.has_focus = True
        actions.next_sentence()
        mock_card2.focus.assert_called_once()

        mock_card1.has_focus = False
        mock_card2.has_focus = True
        actions.next_sentence()
        mock_card3.focus.assert_called_once()

        for card in [mock_card1, mock_card2, mock_card3]:
            card.has_focus = False
        actions.prev_sentence()
        mock_card3.focus.assert_called_with()

        mock_card3.has_focus = True
        actions.prev_sentence()
        mock_card2.focus.assert_called_with()

    def test_copy_annotation_state(self, main_window):
        """Test that copy_annotation updates AppContext copied annotation."""
        actions = main_window.action_service
        mock_token = MagicMock()
        mock_token.annotation = MagicMock(
            pos="N",
            gender="m",
            number="s",
            case="n",
            modern_english_meaning="king",
            root="cyning",
        )
        mock_token.annotation.to_json.return_value = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "modern_english_meaning": "king",
            "root": "cyning",
        }

        mock_card = MagicMock()
        mock_card.oe_text_edit = MagicMock()
        mock_card.oe_text_edit.current_token_index.return_value = 0
        mock_card.oe_text_edit.get_token.return_value = mock_token

        main_window.project_ui.set_selected_sentence_card(mock_card)

        assert actions.copy_annotation() is True
        assert main_window.app_context.copied_annotation is not None
        assert main_window.app_context.copied_annotation["pos"] == "N"
        assert (
            main_window.app_context.copied_annotation["modern_english_meaning"]
            == "king"
        )

    @patch("oeapp.ui.main_window.AnnotateTokenCommand")
    def test_paste_annotation_state(self, mock_command, main_window):
        """Test that paste_annotation uses copied app-context state."""
        actions = main_window.action_service
        copied_data = {"pos": "V", "root": "gangan"}
        main_window.app_context.copied_annotation = copied_data

        mock_token = MagicMock()
        mock_token.id = 123
        mock_token.annotation = None

        mock_card = MagicMock()
        mock_card.oe_text_edit = MagicMock()
        mock_card.oe_text_edit.selector = MagicMock()
        mock_card.oe_text_edit.selector.current_token_index.return_value = 0
        mock_card.oe_text_edit.get_token.return_value = mock_token
        mock_card.sentence = MagicMock()

        main_window.project_ui.set_selected_sentence_card(mock_card)
        main_window.app_context.command_manager = MagicMock()
        main_window.app_context.command_manager.execute.return_value = True
        main_window.app_context.session = MagicMock()

        with patch.object(main_window.token_details_sidebar, "render_token"):
            assert actions.paste_annotation() is True

        mock_command.assert_called_once()
        assert mock_command.call_args.kwargs["after"] == copied_data

    def test_status_bar_messages(self, main_window):
        """Test that Messages helper updates the status bar."""
        messages = main_window.messages
        messages.show_message("Test Message", duration=1000)
        assert main_window.statusBar().currentMessage() == "Test Message"

    def test_ensure_visible_scrolls_to_show_full_card(self, main_window):
        """ensure_visible should scroll so a fitting card is fully visible."""
        scroll_area = MagicMock()
        scrollbar = MagicMock()
        content_widget = QWidget()
        card_widget = MagicMock()

        scroll_area.widget.return_value = content_widget
        scroll_area.viewport.return_value.height.return_value = 400
        scroll_area.verticalScrollBar.return_value = scrollbar
        scrollbar.value.return_value = 0
        scrollbar.minimum.return_value = 0
        scrollbar.maximum.return_value = 1000

        card_widget.mapTo.return_value = QPoint(0, 350)
        card_widget.height.return_value = 120

        main_window.main_column = scroll_area
        main_window.ensure_visible(card_widget)

        scrollbar.setValue.assert_called_once_with(342)

    def test_autosave_noops_without_current_project(self, main_window):
        """Autosave should safely no-op when no project is active."""
        main_window.app_context.current_project_id = None
        with (
            patch("oeapp.ui.main_window.Project.get") as mock_project_get,
            patch.object(main_window.messages, "show_message") as mock_show_message,
        ):
            main_window.action_service.autosave()

        mock_project_get.assert_not_called()
        mock_show_message.assert_not_called()

    def test_on_sentence_added_defers_focus_to_new_card(self, main_window):
        """Adding a sentence should focus the new card OE editor after reload."""
        project_ui = main_window.project_ui
        main_window.app_context.current_project_id = 1

        project = MagicMock()
        existing_card = MagicMock()
        existing_card.sentence.id = 10
        new_card = MagicMock()
        new_card.sentence.id = 99

        with (
            patch("oeapp.ui.project_workspace.Project.get", return_value=project),
            patch.object(
                project_ui,
                "_reload_after_structure_change",
                return_value=True,
            ),
            patch.object(project_ui, "find_sentence_card", return_value=new_card),
            patch.object(main_window, "reload_main_window"),
            patch.object(main_window, "ensure_visible") as mock_ensure_visible,
            patch("oeapp.ui.project_workspace.QTimer.singleShot") as mock_single_shot,
        ):
            project_ui._on_sentence_added(99)

            mock_single_shot.assert_called_once()
            scheduled_delay, scheduled_callback = mock_single_shot.call_args.args
            assert scheduled_delay == 0

            scheduled_callback()
            mock_ensure_visible.assert_called_once_with(new_card)
            new_card.enter_edit_mode.assert_called_once_with()
            new_card.flash_added.assert_called_once_with()

    def test_reload_after_structure_change_preserves_command_manager(
        self, main_window
    ):
        """Structural reload should keep the same command manager instance."""
        project_ui = main_window.project_ui
        manager = main_window.app_context.command_manager
        main_window.app_context.current_project_id = 1

        project = MagicMock()

        with (
            patch("oeapp.ui.project_workspace.Project.get", return_value=project),
            patch.object(project_ui, "load"),
            patch.object(main_window, "reload_main_window"),
        ):
            assert project_ui._reload_after_structure_change(
                clear_search=False,
                message="Sentences merged",
            )

        assert main_window.app_context.command_manager is manager
        assert project_ui.command_manager is manager

    def test_project_ui_selected_card_is_local_to_workspace(self, main_window):
        """Selected sentence card should be workspace-local, not app context."""
        project_ui = main_window.project_ui
        mock_card = MagicMock()

        project_ui.set_selected_sentence_card(mock_card)

        assert project_ui.get_selected_sentence_card() is mock_card
        assert main_window.action_service._selected_sentence_card() is mock_card

        project_ui.clear_selected_sentence_card()

        assert project_ui.get_selected_sentence_card() is None


class TestMainWindowHelp:
    """Test help-center wiring on the main window."""

    @patch("oeapp.ui.main_window.HelpCenterDialog")
    def test_show_help_opens_help_center_dialog(self, mock_help_dialog, main_window):
        """show_help should instantiate and show the QtHelp dialog."""
        main_window.show_help(topic="Keybindings")

        mock_help_dialog.assert_called_once_with(topic="Keybindings", parent=main_window)
        mock_help_dialog.return_value.show.assert_called_once()

    @patch("oeapp.ui.main_window.HelpCenterDialog")
    def test_show_help_reuses_existing_visible_dialog(
        self, mock_help_dialog, main_window
    ):
        """show_help should reuse and focus existing non-modal dialog."""
        existing_dialog = MagicMock()
        existing_dialog.isVisible.return_value = True
        main_window._help_dialog = existing_dialog

        main_window.show_help(topic="Keybindings")

        mock_help_dialog.assert_not_called()
        existing_dialog.show_topic.assert_called_once_with("Keybindings")
        existing_dialog.raise_.assert_called_once()
        existing_dialog.activateWindow.assert_called_once()


class TestMainWindowStartupDialogs:
    """Test cases for startup dialog logic."""

    @patch("oeapp.ui.main_window.Project.first")
    @patch("oeapp.ui.main_window.OpenProjectDialog")
    @patch("oeapp.ui.main_window.NewProjectDialog")
    def test_show_startup_dialog_with_projects(
        self, mock_new_dlg, mock_open_dlg, mock_project_first, main_window
    ):
        """Test that OpenProjectDialog is shown if projects exist."""
        mock_project_first.return_value = MagicMock()

        main_window._show_startup_dialog()

        mock_open_dlg.assert_called_once_with(main_window)
        mock_open_dlg.return_value.execute.assert_called_once()
        mock_new_dlg.assert_not_called()

    @patch("oeapp.ui.main_window.Project.first")
    @patch("oeapp.ui.main_window.OpenProjectDialog")
    @patch("oeapp.ui.main_window.NewProjectDialog")
    def test_show_startup_dialog_no_projects(
        self, mock_new_dlg, mock_open_dlg, mock_project_first, main_window
    ):
        """Test that NewProjectDialog is shown if no projects exist."""
        mock_project_first.return_value = None

        main_window._show_startup_dialog()

        mock_new_dlg.assert_called_once_with(main_window)
        mock_new_dlg.return_value.execute.assert_called_once()
        mock_open_dlg.assert_not_called()


class TestMainWindowOptimizeHooks:
    """Test startup and shutdown optimize hooks."""

    def test_startup_runs_pragma_optimize(self, qapp, db_session, mock_services):
        """MainWindow should run PRAGMA optimize after migration handling."""
        with patch("oeapp.ui.main_window.run_pragma_optimize") as mock_optimize:
            window = MainWindow(app_context=AppContext(session=db_session))
            assert mock_optimize.call_count == 1
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_close_event_swallows_optimize_errors(self, qapp, db_session, mock_services):
        """Close should not fail even if optimize unexpectedly raises."""
        with patch(
            "oeapp.ui.main_window.run_pragma_optimize",
            side_effect=[True, RuntimeError("boom")],
        ):
            window = MainWindow(app_context=AppContext(session=db_session))
            event = QCloseEvent()
            window.closeEvent(event)
        window.deleteLater()
        qapp.processEvents()


class TestMessagesSeverity:
    """Test cases for error/warning message severity."""

    def test_show_error_uses_critical_severity(self, db_session, mock_main_window, qapp):
        """show_error renders with the critical icon, not the warning icon."""
        messages = Messages(mock_main_window)

        with (
            patch("oeapp.ui.main_window.QMessageBox.critical") as mock_critical,
            patch("oeapp.ui.main_window.QMessageBox.warning") as mock_warning,
        ):
            messages.show_error("disk on fire")

        mock_critical.assert_called_once()
        mock_warning.assert_not_called()


class TestEmptyStateStyling:
    """Test cases for the welcome/empty-state label styling."""

    def test_welcome_label_stylesheet_uses_valid_palette_function(self):
        """The empty-state stylesheet uses palette(), not the misspelled pallete()."""
        import oeapp.ui.main_window as main_window_module

        source = Path(main_window_module.__file__).read_text(encoding="utf-8")

        assert "pallete(" not in source


class TestNavigationButtonAffordances:
    """Test cases for chapter/section navigation button discoverability."""

    def test_navigation_buttons_have_tooltips_and_accessible_names(self, main_window):
        """Every glyph-only nav button exposes a tooltip and an accessible name."""
        expected = {
            "chapter_prev_button": "Previous chapter",
            "chapter_next_button": "Next chapter",
            "section_prev_button": "Previous section",
            "section_next_button": "Next section",
        }

        for attribute, label in expected.items():
            button = getattr(main_window, attribute)
            assert button.toolTip() == label
            assert button.accessibleName() == label


class TestSidebarResizing:
    """Test cases for the resizable token details sidebar."""

    def test_sidebar_lives_in_a_splitter(self, main_window):
        """The sidebar and content column share a user-draggable splitter."""
        assert isinstance(main_window.main_splitter, QSplitter)
        assert main_window.main_splitter.count() == 2

    def test_sidebar_is_not_fixed_width(self, main_window):
        """The sidebar can be resized: its min and max widths are not pinned equal."""
        sidebar = main_window.token_details_sidebar

        assert sidebar.minimumWidth() != sidebar.maximumWidth()

    def test_splitter_panes_are_not_collapsible(self, main_window):
        """Neither splitter pane can be dragged to zero width.

        ``QSplitter.childrenCollapsible()`` defaults to ``True``, which lets a
        drag push a pane straight past its minimum width to zero even though
        a ``setMinimumWidth()`` is set. There is no View-menu toggle to bring
        a collapsed pane back, and the content column hosts the search and
        navigation toolbars, so collapsing it would hide the entire working
        surface with no way to recover it.
        """
        assert main_window.main_splitter.childrenCollapsible() is False

    def test_sidebar_starts_at_default_width(self, main_window, qapp):
        """The sidebar still opens at its established default width.

        ``QSplitter.sizes()`` only reflects a requested ``setSizes()`` call
        once the widget has actually been laid out on screen; on a
        never-shown widget Qt reports the sidebar's minimum width (200)
        instead of the requested 350, which would make a literal
        ``sizes()[1] == SIDEBAR_WIDTH`` assertion pass or fail based on
        window visibility rather than on the code under test. Showing the
        window and pumping the event loop forces a real layout pass, so
        this genuinely verifies the sidebar opens at its default width
        rather than at its bare minimum.
        """
        main_window.show()
        qapp.processEvents()

        sizes = main_window.main_splitter.sizes()

        assert len(sizes) == 2
        assert sizes[1] == MainWindow.SIDEBAR_WIDTH


class TestThemeRefreshReachesStaleSites:
    """Regression tests for D5's "no visibly stale panel" acceptance criterion.

    ``ThemeMixin.reddish`` is not the only value baked from the palette at
    construction time: verse card backgrounds, paragraph separators, and
    active per-card highlighting commands all compute a concrete color from
    the palette once and never update on their own. A live theme switch must
    re-render all of them, not just the help dialog.
    """

    def test_refresh_theme_dependent_widgets_rerenders_open_project(
        self, main_window, qapp
    ):
        """The theme refresh hook must re-render loaded sentence cards and
        paragraph separators, not just call the help dialog's refresh.

        Against the pre-fix code, ``refresh_theme_dependent_widgets`` never
        touches the project at all, so ``set_tokens``/``refresh_theme`` are
        never called and the separator's stylesheet is never recomputed.
        """
        main_window.app_context.current_project_id = 1

        mock_card = MagicMock()
        mock_card.sentence.id = 1
        main_window.project_ui.sentence_cards = [mock_card]

        separator = QWidget()
        style_spy = MagicMock(wraps=separator.setStyleSheet)
        separator.setStyleSheet = style_spy
        main_window.project_ui.paragraph_separators = [separator]

        main_window.refresh_theme_dependent_widgets()

        mock_card.set_tokens.assert_called_once()
        mock_card.refresh_theme.assert_called_once()
        style_spy.assert_called_once()
