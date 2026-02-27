"""Annotation preset management dialog."""

from contextlib import suppress
from typing import TYPE_CHECKING, Final, cast

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError

from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.models.mixins import SessionMixin
from oeapp.services.annotation_preset_service import AnnotationPresetService
from oeapp.ui.dialogs.pos_form_system import CLEAR_SENTINEL, PresetPosFormManager
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from oeapp.types import PresetPos


class AnnotationPresetManagementDialog(AnnotationLookupsMixin, SessionMixin, QDialog):
    """
     Dialog for managing annotation presets.

    Supported Parts of Speech are: Noun, Verb, Adjective, Pronoun, Article.

    Note:
        We're purposely only supporting Parts of Speech that have many
        fields.  Adverbs (1 field), Prepositions (1 field), Conjunctions (1
        field), Interjections (no fields), and Numbers (no fields) are not
        supported, because the user would have to do more clicks to select
        and apply the preset than just selecting the POS and then selecting
        one or zero fields.

    Keyword Args:
        save_mode: If True, hide tabs and show only save form
        initial_pos: POS to pre-select (required if save_mode=True)
        initial_field_values: Dictionary of field values to preload
        parent: Parent widget

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500
    #: Supported Parts of Speech
    SUPPORTED_POS: Final[tuple[str, ...]] = ("N", "V", "A", "R", "D")

    def __init__(
        self,
        save_mode: bool = False,
        initial_pos: "PresetPos | None" = None,
        initial_field_values: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        #: THe SQLAlchemy session
        self.session = self._get_session()
        #: The preset service
        self.preset_service = AnnotationPresetService()
        #: Whether the dialog is in save mode
        self.save_mode = save_mode
        #: The initial POS to pre-select
        self.initial_pos = initial_pos
        #: The initial field values to pre-load
        self.initial_field_values = initial_field_values or {}
        #: The current preset ID
        self.current_preset_id: int | None = None
        #: The current POS
        self.current_pos: PresetPos | None = initial_pos
        #: The save mode manager
        self.save_mode_manager: PresetPosFormManager | None = None
        #: The tab form managers: keyed by POS code
        self.tab_form_managers: dict[str, PresetPosFormManager] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the base dialog UI shell."""
        self.setWindowTitle("POS Presets")
        self.setModal(True)
        self.resize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)

        layout = QVBoxLayout(self)
        if self.save_mode:
            self._setup_save_mode_ui(layout)
        else:
            self._setup_full_ui(layout)

    def _setup_save_mode_ui(self, layout: QVBoxLayout) -> None:
        """
        Set up save mode (single POS form, no tabs).

        Side Effects:
            - Creates the name edit widget
            - Creates the form group box
            - Populates the form fields for the POS
            - Creates the "Save" and "Cancel" buttons
            - Connects the "Save" button's clicked signal to the
              :meth:`_save_preset` method
            - Connects the "Cancel" button's clicked signal to the
              :meth:`QDialog.reject` method
            - Sets the focus to the name edit widget

        Args:
            layout: Layout to add the UI elements to

        """
        if not self.initial_pos:
            return

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter preset name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        form_group = QGroupBox(
            f"Preset Fields ({self.PART_OF_SPEECH_MAP.get(self.initial_pos)})"
        )
        self.form_layout = QFormLayout()
        self.form_widget = QWidget()
        self.form_widget.setLayout(self.form_layout)
        form_group.setLayout(QVBoxLayout())
        cast("QLayout", form_group.layout()).addWidget(self.form_widget)
        layout.addWidget(form_group)

        self._populate_form_fields(self.initial_pos)
        if self.initial_field_values:
            self._load_field_values(self.initial_field_values)

        button_box = QDialogButtonBox(self)
        save_button = button_box.addButton(
            "Save", QDialogButtonBox.ButtonRole.AcceptRole
        )
        save_button.clicked.connect(self._save_preset)
        button_box.addButton(
            "Cancel", QDialogButtonBox.ButtonRole.RejectRole
        ).clicked.connect(self.reject)
        layout.addWidget(button_box)

        self.name_edit.setFocus()

    def _setup_full_ui(self, layout: QVBoxLayout) -> None:
        """
        Set up full mode with one tab per supported POS.

        Side Effects:
            - Creates the tab widget
            - Creates the tabs for each supported POS
            - Loads the presets for each supported POS
            - Connects the tab widget's currentChanged signal to the
              :meth:`_on_tab_changed` method

        """
        self.tab_widget = QTabWidget()
        self.tabs: dict[str, QWidget] = {}

        for pos_code in self.SUPPORTED_POS:
            tab = self._create_pos_tab(cast("PresetPos", pos_code))
            self.tabs[pos_code] = tab
            pos_name = self.PART_OF_SPEECH_MAP.get(pos_code, pos_code)
            self.tab_widget.addTab(tab, cast("str", pos_name))
            self._load_presets_for_pos(cast("PresetPos", pos_code))

        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget)

        if self.initial_pos and self.initial_pos in self.tabs:
            self._switch_to_pos_tab(self.initial_pos)

        button_box = QDialogButtonBox(self)
        button_box.addButton(
            "Close", QDialogButtonBox.ButtonRole.AcceptRole
        ).clicked.connect(self.accept)
        layout.addWidget(button_box)

    def _create_pos_tab(self, pos: "PresetPos") -> QWidget:  # noqa: PLR0915
        """
        Create a full-mode tab for one POS.

        Args:
            pos: POS to create the tab for

        Returns:
            QWidget: The created tab widget

        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        list_group = QGroupBox("Presets")
        list_layout = QVBoxLayout()
        preset_list = QListWidget()
        preset_list.setObjectName(f"preset_list_{pos}")
        preset_list.itemSelectionChanged.connect(self._on_preset_selected)
        list_layout.addWidget(preset_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        button_layout = QHBoxLayout()
        new_button = QPushButton("New")
        new_button.clicked.connect(lambda: self._on_new_preset(pos))
        button_layout.addWidget(new_button)

        edit_button = QPushButton("Edit")
        edit_button.setObjectName(f"edit_button_{pos}")
        edit_button.clicked.connect(self._on_edit_preset)
        button_layout.addWidget(edit_button)

        delete_button = QPushButton("Delete")
        delete_button.setObjectName(f"delete_button_{pos}")
        delete_button.clicked.connect(self._on_delete_preset)
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        form_group = QGroupBox("Preset Details")
        form_layout = QFormLayout()
        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setObjectName(f"form_widget_{pos}")
        form_group.setLayout(QVBoxLayout())
        cast("QLayout", form_group.layout()).addWidget(form_widget)

        action_layout = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.setObjectName(f"clear_button_{pos}")
        clear_button.clicked.connect(lambda: self._clear_preset_form(pos))
        action_layout.addWidget(clear_button)

        save_button = QPushButton("Save")
        save_button.setObjectName(f"save_button_{pos}")
        save_button.clicked.connect(self._save_preset)
        action_layout.addWidget(save_button)

        action_layout.addStretch()
        cast("QLayout", form_group.layout()).addLayout(action_layout)  # type: ignore[attr-defined]

        layout.addWidget(form_group)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_edit.setObjectName(f"name_edit_{pos}")
        name_edit.setPlaceholderText("Enter preset name")
        name_layout.addWidget(name_edit)
        form_layout.addRow(name_layout)

        self._populate_form_fields_for_tab(pos, form_layout, form_widget)
        return widget

    def _populate_form_fields_for_tab(
        self,
        pos: "PresetPos",
        form_layout: QFormLayout,
        parent_widget: QWidget,
    ) -> None:
        """
        Render and register managed fields for one POS tab.

        Side Effects:
            - Creates a new preset pos form manager for the POS
            - Stores the preset pos form manager in :attr:`tab_form_managers`

        Args:
            pos: POS to populate the form fields for
            form_layout: Layout to add the form fields to
            parent_widget: Widget to add the form fields to

        """
        manager = PresetPosFormManager(pos, form_layout, parent_widget)
        self.tab_form_managers[pos] = manager

    def _populate_form_fields(self, pos: "PresetPos") -> None:
        """
        Render and register managed fields in save mode.

        Side Effects:
            - Creates a new preset pos form manager for the POS
            - Stores the preset pos form manager in :attr:`save_mode_manager`
            - Binds the dialog attributes to the preset pos form manager

        Args:
            pos: POS to populate the form fields for

        """
        while self.form_layout.rowCount() > 0:
            cast("QFormLayout", self.form_layout).removeRow(0)

        self.save_mode_manager = PresetPosFormManager(
            pos, self.form_layout, self.form_widget
        )
        self.save_mode_manager.bind_dialog_attributes(self)

    def _load_presets_for_pos(self, pos: "PresetPos") -> None:
        """
        Load presets into the list widget for a POS tab.

        Args:
            pos: POS to load the presets for

        """
        preset_list = self._find_preset_list(pos)
        if not preset_list:
            return

        preset_list.clear()
        presets = self.preset_service.get_presets_for_pos(pos)
        for preset in presets:
            preset_list.addItem(preset.name)
            item = preset_list.item(preset_list.count() - 1)
            if item:
                item.setData(256, preset.id)

    def _find_preset_list(self, pos: "PresetPos") -> QListWidget | None:
        """
        Find the list widget for a POS tab.

        Args:
            pos: POS to find the list widget for

        Returns:
            The list widget for the POS, if found

        """
        if self.save_mode:
            return None
        tab = self.tabs.get(pos)
        if not tab:
            return None
        return tab.findChild(QListWidget, f"preset_list_{pos}")

    def _current_tab_pos(self) -> "PresetPos | None":
        """
        Return the current tab's POS code.

        Side Effects:
            - Returns the current tab's POS code
            - Switches to the POS tab for the current tab if not in save mode

        """
        if self.save_mode:
            return self.initial_pos
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0 or current_tab_index >= len(self.SUPPORTED_POS):
            return None
        return cast("PresetPos", self.SUPPORTED_POS[current_tab_index])

    def _on_new_preset(self, pos: "PresetPos") -> None:
        """
        Signal callback for the ``clicked`` signal on the new button.

        Prepare a new preset form for the selected POS.

        Side Effects:
            - Sets the current preset ID and POS to None
            - Clears the current preset form
            - Switches to the POS tab for the new preset

        Args:
            pos: POS to prepare the new preset form for

        """
        self.current_preset_id = None
        self.current_pos = pos
        self._clear_form()
        self._switch_to_pos_tab(pos)

    def _on_edit_preset(self) -> None:
        """
        Signal callback for the ``clicked`` signal on the edit button.

        Load selected preset into form for editing.

        Side Effects:
            - Clears the current preset form
            - Loads the selected preset into the form
            - Switches to the POS tab for the selected preset

        """
        pos = self._current_tab_pos()
        if not pos:
            return

        preset_list = self._find_preset_list(pos)
        if not preset_list or not preset_list.currentItem():
            return

        preset_id = preset_list.currentItem().data(256)
        if not preset_id:
            return

        preset = AnnotationPreset.get(preset_id)
        if not preset:
            return

        self.current_preset_id = preset_id
        self.current_pos = cast("PresetPos", preset.pos)
        self._load_preset_into_form(preset)

    def _on_delete_preset(self) -> None:
        """
        Signal callback for the ``clicked`` signal on the delete button.

        Delete selected preset with confirmation.

        Side Effects:
            - Deletes the selected preset
            - Loads the presets for the POS
            - Clears the current preset form

        """
        pos = self._current_tab_pos()
        if not pos:
            return

        preset_list = self._find_preset_list(pos)
        if not preset_list or not preset_list.currentItem():
            return

        preset_id = preset_list.currentItem().data(256)
        if not preset_id:
            return

        preset = AnnotationPreset.get(preset_id)
        if not preset:
            return

        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Delete Preset",
            f"Are you sure you want to delete preset '{preset.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self.preset_service.delete_preset(preset_id)
            self._load_presets_for_pos(pos)
            self._clear_form()

    def _on_preset_selected(self) -> None:
        """
        Signal callback for the ``itemSelectionChanged`` signal on the preset list.

        Enable/disable edit/delete buttons based on list selection.

        Side Effects:
            - Enables/disables the edit/delete buttons based on the list selection

        """
        pos = self._current_tab_pos()
        if not pos:
            return

        preset_list = self._find_preset_list(pos)
        if not preset_list:
            return

        has_selection = preset_list.currentItem() is not None
        edit_button = self.tabs[pos].findChild(QPushButton, f"edit_button_{pos}")
        delete_button = self.tabs[pos].findChild(QPushButton, f"delete_button_{pos}")
        if edit_button:
            edit_button.setEnabled(has_selection)
        if delete_button:
            delete_button.setEnabled(has_selection)

    def _load_preset_into_form(self, preset: AnnotationPreset) -> None:
        """
        Load one preset's values into whichever form context is active.

        Side Effects:
            - Switches to the POS tab for the preset
            - Sets the current preset ID and POS
            - Loads the preset's values into the form

        """
        self._switch_to_pos_tab(cast("PresetPos", preset.pos))
        self.current_pos = cast("PresetPos", preset.pos)
        self.current_preset_id = preset.id

        name_edit = self._find_name_edit(cast("PresetPos", preset.pos))
        if name_edit:
            name_edit.setText(preset.name)

        field_values: dict[str, str | bool | None] = {
            "gender": preset.gender,
            "number": preset.number,
            "case": preset.case,
            "declension": preset.declension,
            "article_type": preset.article_type,
            "pronoun_type": preset.pronoun_type,
            "pronoun_number": preset.pronoun_number,
            "verb_class": preset.verb_class,
            "verb_tense": preset.verb_tense,
            "verb_person": preset.verb_person,
            "verb_mood": preset.verb_mood,
            "verb_aspect": preset.verb_aspect,
            "verb_form": preset.verb_form,
            "verb_direct_object_case": preset.verb_direct_object_case,
            "verb_requires_infinitive": preset.verb_requires_infinitive,
            "verb_impersonal": preset.verb_impersonal,
            "verb_transitivity": preset.verb_transitivity,
            "adjective_inflection": preset.adjective_inflection,
            "adjective_degree": preset.adjective_degree,
        }
        self._load_field_values(field_values)

    def _find_name_edit(self, pos: "PresetPos") -> QLineEdit | None:
        """
        Find name-edit widget for save mode or tab mode.

        Args:
            pos: POS to find the name-edit widget for

        Returns:
            The name-edit widget for the POS, if found

        """
        if self.save_mode:
            return self.name_edit
        tab = self.tabs.get(pos)
        if not tab:
            return None
        return tab.findChild(QLineEdit, f"name_edit_{pos}")

    def _load_field_values(self, field_values: dict[str, str | bool | None]) -> None:
        """
        Load values into the active managed form.

        Side Effects:
            - Loads the field values into the save mode manager or the tab form manager

        Args:
            field_values: Dictionary of field values to load

        """
        if self.save_mode:
            self._load_field_values_save_mode(field_values)
        else:
            self._load_field_values_full_mode(field_values)

    def _load_field_values_save_mode(
        self,
        field_values: dict[str, str | bool | None],
    ) -> None:
        """
        Signal callback for the ``annotation_applied`` signal.

        Load field values in save mode using managed fields.

        Side Effects:
            - Loads the field values into the save mode manager

        Args:
            field_values: Dictionary of field values to load

        """
        if self.save_mode_manager:
            self.save_mode_manager.load_from_values(field_values)

    def _load_field_values_full_mode(
        self,
        field_values: dict[str, str | bool | None],
    ) -> None:
        """
        Load field values in full mode using the active tab manager.

        Side Effects:
            - Loads the field values into the tab form manager

        Args:
            field_values: Dictionary of field values to load

        """
        pos = self._current_tab_pos()
        if not pos:
            return
        manager = self.tab_form_managers.get(pos)
        if manager:
            manager.load_from_values(field_values)

    def _extract_combo_value(self, idx: int, reverse_map: dict) -> str | bool | None:
        """
        Compatibility helper retained for direct unit tests.

        Args:
            idx: Index to extract the value from
            reverse_map: Dictionary to map the index to the value

        Returns:
            The value for the index, if found

        """
        if idx == 0:
            return None
        if idx == 1:
            return CLEAR_SENTINEL
        return reverse_map.get(idx - 1)

    def _set_combo_value(
        self,
        combo: QComboBox,
        value: str | bool | None,
        reverse_map: dict[int, str | bool],
    ) -> None:
        """Compatibility helper retained for direct unit tests."""
        if value is None:
            combo.setCurrentIndex(0)
            return
        if value == CLEAR_SENTINEL:
            combo.setCurrentIndex(1)
            return

        code_to_original_index = {v: k for k, v in reverse_map.items()}
        original_index = code_to_original_index.get(value)
        if original_index is not None:
            combo.setCurrentIndex(original_index + 1)
        else:
            combo.setCurrentIndex(0)

    def _clear_preset_form(self, pos: str) -> None:
        """
        Clear one tab form (name and managed combo fields).

        Side Effects:
            - Clears the name edit
            - Clears the managed combo fields

        Args:
            pos: POS code to clear the form for

        """
        name_edit = self._find_name_edit(cast("PresetPos", pos))
        if name_edit:
            name_edit.clear()

        manager = self.tab_form_managers.get(pos)
        if manager:
            manager.reset()
        else:
            tab = self.tabs.get(pos)
            if tab:
                form_widget = tab.findChild(QWidget, f"form_widget_{pos}")
                if form_widget:
                    for combo in form_widget.findChildren(QComboBox):
                        combo.setCurrentIndex(0)

        self.current_preset_id = None

    def _clear_form(self) -> None:
        """
        Clear currently active form and reset preset editing state.

        Side Effects:
            - Clears the name edit if in save mode
            - Clears the save mode manager if in save mode
            - Clears the tab form manager if in full mode
            - Clears the managed combo fields if in full mode

        """
        if self.save_mode:
            if hasattr(self, "name_edit"):
                self.name_edit.clear()
            if self.save_mode_manager:
                self.save_mode_manager.reset()
            else:
                for attr_name in dir(self):
                    if attr_name.endswith("_combo"):
                        combo = getattr(self, attr_name, None)
                        if isinstance(combo, QComboBox):
                            combo.setCurrentIndex(0)
            return

        pos = self._current_tab_pos()
        if pos:
            name_edit = self._find_name_edit(pos)
            if name_edit:
                name_edit.clear()
            manager = self.tab_form_managers.get(pos)
            if manager:
                manager.reset()
            else:
                for combo in self.findChildren(QComboBox):
                    combo.setCurrentIndex(0)

    def _on_tab_changed(self, index: int) -> None:
        """
        Signal callback for the ``currentChanged`` signal on the tab widget.

        Clear selected preset context when user manually switches tabs.

        Args:
            index: Index of the tab that was changed

        """
        if self.current_preset_id is None:
            return

        if 0 <= index < len(self.SUPPORTED_POS):
            new_pos = self.SUPPORTED_POS[index]
            if self.current_pos != new_pos:
                self.current_preset_id = None
                self.current_pos = cast("PresetPos", new_pos)
                self._clear_form()

    def _switch_to_pos_tab(self, pos: "PresetPos") -> None:
        """
        Programmatically switch to tab for the target POS.

        Side Effects:
            - Clears the selected preset context
            - Switches to the POS tab for the target POS

        Args:
            pos: POS to switch to

        """
        if not hasattr(self, "tab_widget"):
            return
        if pos in self.SUPPORTED_POS:
            index = self.SUPPORTED_POS.index(pos)
            with suppress(TypeError):
                self.tab_widget.currentChanged.disconnect(self._on_tab_changed)
            self.tab_widget.setCurrentIndex(index)
            self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _validate_preset(self) -> tuple[bool, str]:
        """
        Validate current preset form values before save.

        Side Effects:
            - Validates the preset name:
                - Must be present
                - Must be unique for the POS
            - Validates the POS:
                - Must be present
                - Must be in the supported POS list

        Returns:
            Tuple of (bool, str):
                - First element: True if the preset is valid, False otherwise
                - Second element: Error message if the preset is not valid

        """
        if self.save_mode:
            name = self.name_edit.text().strip()
            pos = self.initial_pos
        else:
            pos = self._current_tab_pos()
            if not pos:
                return False, "No POS selected"
            name_edit = self._find_name_edit(pos)
            if not name_edit:
                return False, "Name field not found"
            name = name_edit.text().strip()

        if not name:
            return False, "Preset name is required"

        if not pos:
            return False, "POS is required"

        for preset in self.preset_service.get_presets_for_pos(pos):
            if (
                preset.id != self.current_preset_id
                and preset.name.lower() == name.lower()
            ):
                return False, f"Preset '{name}' already exists for this part of speech"

        return True, ""

    def _save_preset(self) -> None:  # noqa: PLR0912
        """
        Signal callback for the ``clicked`` signal on the "Save" button.

        Save (create/update) the preset currently in the form.

        Side Effects:
            - Validates the preset via :meth:`_validate_preset`
            - Saves the preset
            - Shows a message box if the preset is not valid
            - Switches to the POS tab for the saved preset
            - Clears the current preset form

        """
        is_valid, error_msg = self._validate_preset()
        if not is_valid:
            msg_box = QMessageBox(
                QMessageBox.Icon.Warning,
                "Validation Error",
                error_msg,
                QMessageBox.StandardButton.Ok,
                self,
            )
            logo_pixmap = get_logo_pixmap(75)
            if logo_pixmap:
                msg_box.setIconPixmap(logo_pixmap)
            msg_box.exec()
            return

        if self.save_mode:
            name = self.name_edit.text().strip()
            pos = self.initial_pos
            field_values = self._extract_field_values()
        else:
            pos = self._current_tab_pos()
            if not pos:
                return
            name_edit = self._find_name_edit(pos)
            if not name_edit:
                return
            name = name_edit.text().strip()
            field_values = self._extract_field_values_for_tab(pos)

        if pos == "V":
            field_values = self._normalize_verb_metadata_fields(field_values)

        try:
            if self.current_preset_id:
                preset = AnnotationPreset.get(self.current_preset_id)
                if preset and preset.pos == pos:
                    self.preset_service.update_preset(
                        self.current_preset_id,
                        name,
                        field_values,
                    )
                else:
                    self.current_preset_id = None
                    self.preset_service.create_preset(
                        name, cast("str", pos), field_values
                    )
            else:
                self.preset_service.create_preset(name, cast("str", pos), field_values)

            if self.save_mode:
                self.accept()
            else:
                self._load_presets_for_pos(cast("PresetPos", pos))
                self._clear_form()
                msg_box = QMessageBox(
                    QMessageBox.Icon.Information,
                    "Success",
                    "Preset saved successfully",
                    QMessageBox.StandardButton.Ok,
                    self,
                )
                logo_pixmap = get_logo_pixmap(75)
                if logo_pixmap:
                    msg_box.setIconPixmap(logo_pixmap)
                msg_box.exec()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, IntegrityError):
                QMessageBox.warning(
                    self,
                    "Error",
                    "A preset with this name already exists for this part of speech.",
                )
            else:
                QMessageBox.critical(self, "Error", f"Failed to save preset: {exc}")

    def _normalize_verb_metadata_fields(
        self,
        field_values: dict[str, str | bool | None],
    ) -> dict[str, str | bool | None]:
        """
        Apply default values to optional verb metadata fields.

        Args:
            field_values: Dictionary of field values to normalize

        Returns:
            Dictionary of normalized field values

        """
        defaults: dict[str, str | bool] = {
            "verb_requires_infinitive": False,
            "verb_impersonal": False,
            "verb_transitivity": "transitive",
        }
        normalized = dict(field_values)
        for key, default_value in defaults.items():
            value = normalized.get(key)
            if value in (None, CLEAR_SENTINEL):
                normalized[key] = default_value
        return normalized

    def _extract_field_values(self) -> dict[str, str | bool | None]:
        """
        Extract save-mode field values from managed form fields.

        Returns:
            Dictionary of field values

        """
        if not self.save_mode_manager:
            return {}
        return self.save_mode_manager.extract_values()

    def _extract_field_values_for_tab(
        self,
        pos: "PresetPos",
    ) -> dict[str, str | bool | None]:
        """
        Extract full-mode field values from a specific tab's manager.

        Args:
            pos: POS to extract the field values for

        Returns:
            Dictionary of field values

        """
        manager = self.tab_form_managers.get(pos)
        if not manager:
            return {}
        return manager.extract_values()
