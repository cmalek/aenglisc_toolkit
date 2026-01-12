"""Annotation preset management dialog."""

# Sentinel value to represent "Clear" selection in presets
# This distinguishes "Clear" (explicitly clear field) from None (don't change field)
CLEAR_SENTINEL = "__CLEAR__"

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

    def __init__(
        self,
        save_mode: bool = False,  # noqa: FBT001, FBT002
        initial_pos: PresetPos | None = None,
        initial_field_values: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize preset management dialog.
        """
        super().__init__(parent)
        self.session = self._get_session()
        self.preset_service = AnnotationPresetService()
        self.save_mode = save_mode
        self.initial_pos = initial_pos
        self.initial_field_values = initial_field_values or {}
        self.current_preset_id: int | None = None
        self.current_pos: PresetPos | None = initial_pos
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
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
        Set up UI for save mode (no tabs, just form).

        Args:
            layout: Layout to add the UI to

        """
        if not self.initial_pos:
            return

        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter preset name")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Form fields for POS
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

        # Buttons
        button_box = QDialogButtonBox(self)
        save_button = button_box.addButton(
            "Save", QDialogButtonBox.ButtonRole.AcceptRole
        )
        save_button.clicked.connect(self._save_preset)
        button_box.addButton(
            "Cancel", QDialogButtonBox.ButtonRole.RejectRole
        ).clicked.connect(self.reject)
        layout.addWidget(button_box)

        # Focus on name field
        self.name_edit.setFocus()

    def _setup_full_ui(self, layout: QVBoxLayout) -> None:
        """
        Set up full UI with tabs.

        Args:
            layout: Layout to add the UI to

        """
        # Tabs for each POS
        self.tab_widget = QTabWidget()
        self.tabs: dict[str, QWidget] = {}

        for pos_code in ("N", "V", "A", "R", "D"):
            tab = self._create_pos_tab(pos_code)
            self.tabs[pos_code] = tab
            pos_name = self.PART_OF_SPEECH_MAP.get(pos_code, pos_code)
            self.tab_widget.addTab(tab, cast("str", pos_name))
            # Load presets now that tab is in self.tabs
            self._load_presets_for_pos(pos_code)

        # Connect tab change signal to clear preset ID when manually switching tabs
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tab_widget)

        # Switch to initial POS tab if provided
        if self.initial_pos and self.initial_pos in self.tabs:
            self._switch_to_pos_tab(self.initial_pos)

        # Buttons
        button_box = QDialogButtonBox(self)
        button_box.addButton(
            "Close", QDialogButtonBox.ButtonRole.AcceptRole
        ).clicked.connect(self.accept)
        layout.addWidget(button_box)

    def _create_pos_tab(self, pos: PresetPos) -> QWidget:  # noqa: PLR0915
        """
        Create a tab for a specific POS.

        Args:
            pos: POS code (N, V, A, R, D)

        Returns:
            Widget containing the POS tab

        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # List of presets
        list_group = QGroupBox("Presets")
        list_layout = QVBoxLayout()
        preset_list = QListWidget()
        preset_list.setObjectName(f"preset_list_{pos}")
        preset_list.itemSelectionChanged.connect(self._on_preset_selected)
        list_layout.addWidget(preset_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Buttons
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

        # Form fields
        form_group = QGroupBox("Preset Details")
        form_layout = QFormLayout()
        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setObjectName(f"form_widget_{pos}")
        form_group.setLayout(QVBoxLayout())
        cast("QLayout", form_group.layout()).addWidget(form_widget)

        # Add Clear and Save buttons inside the Preset Details box
        button_container = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.setObjectName(f"clear_button_{pos}")
        clear_button.clicked.connect(lambda: self._clear_preset_form(pos))
        button_container.addWidget(clear_button)

        save_button = QPushButton("Save")
        save_button.setObjectName(f"save_button_{pos}")
        save_button.clicked.connect(self._save_preset)
        button_container.addWidget(save_button)

        button_container.addStretch()  # Push buttons to the left
        cast("QLayout", form_group.layout()).addLayout(button_container)  # type: ignore[attr-defined]

        layout.addWidget(form_group)

        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_edit.setObjectName(f"name_edit_{pos}")
        name_edit.setPlaceholderText("Enter preset name")
        name_layout.addWidget(name_edit)
        form_layout.addRow(name_layout)

        # Populate form fields for this POS
        self._populate_form_fields_for_tab(pos, form_layout)

        # Store reference to preset_list for later loading
        # (can't load yet because tab isn't in self.tabs until after creation)

        return widget

    def _populate_form_fields_for_tab(
        self, pos: PresetPos, form_layout: QFormLayout
    ) -> None:
        """
        Populate form fields for a POS tab, for supported Parts of Speech.

        Supported Parts of Speech are: Noun, Verb, Adjective, Pronoun, Article.

        Note:
            We're purposely only supporting Parts of Speech that have many
            fields.  Adverbs (1 field), Prepositions (1 field), Conjunctions (1
            field), Interjections (no fields), and Numbers (no fields) are not
            supported, because the user would have to do more clicks to select
            and apply the preset than just selecting the POS and then selecting
            one or zero fields.

        Args:
            pos: POS code (N, V, A, R, D)
            form_layout: Layout to add the form fields to

        """
        # Store original form_layout and temporarily set it
        original_layout = self.form_layout if hasattr(self, "form_layout") else None
        self.form_layout = form_layout

        # Populate fields based on POS
        if pos == "N":
            self._add_noun_fields_to_form()
        elif pos == "V":
            self._add_verb_fields_to_form()
        elif pos == "A":
            self._add_adjective_fields_to_form()
        elif pos == "R":
            self._add_pronoun_fields_to_form()
        elif pos == "D":
            self._add_article_fields_to_form()

        # Restore original layout if it existed
        if original_layout:
            self.form_layout = original_layout

    def _populate_form_fields(self, pos: PresetPos) -> None:
        """
        Show relevant form fields for POS.

        Args:
            pos: POS code (N, V, A, R, D)

        """
        # Clear existing fields
        while self.form_layout.rowCount() > 0:
            cast("QFormLayout", self.form_layout).removeRow(0)

        if pos == "N":
            self._add_noun_fields_to_form()
        elif pos == "V":
            self._add_verb_fields_to_form()
        elif pos == "A":
            self._add_adjective_fields_to_form()
        elif pos == "R":
            self._add_pronoun_fields_to_form()
        elif pos == "D":
            self._add_article_fields_to_form()

    def _add_noun_fields_to_form(self) -> None:
        """Add noun fields to form."""
        self.gender_combo = self._create_combo(
            "Gender:", cast("list[str]", list(self.GENDER_MAP.values())), "gender_combo"
        )
        self.number_combo = self._create_combo(
            "Number:", cast("list[str]", list(self.NUMBER_MAP.values())), "number_combo"
        )
        self.case_combo = self._create_combo(
            "Case:", cast("list[str]", list(self.CASE_MAP.values())), "case_combo"
        )
        self.declension_combo = self._create_editable_combo(
            "Declension:",
            cast("list[str]", list(self.DECLENSION_MAP.values())),
            "declension_combo",
        )

    def _add_verb_fields_to_form(self) -> None:
        """Add verb fields to form."""
        self.verb_class_combo = self._create_editable_combo(
            "Class:",
            cast("list[str]", list(self.VERB_CLASS_MAP.values())),
            "verb_class_combo",
        )
        self.verb_tense_combo = self._create_combo(
            "Tense:",
            cast("list[str]", list(self.VERB_TENSE_MAP.values())),
            "verb_tense_combo",
        )
        self.verb_mood_combo = self._create_combo(
            "Mood:",
            cast("list[str]", list(self.VERB_MOOD_MAP.values())),
            "verb_mood_combo",
        )
        self.verb_person_combo = self._create_combo(
            "Person:",
            cast("list[str]", list(self.VERB_PERSON_MAP.values())),
            "verb_person_combo",
        )
        self.verb_number_combo = self._create_combo(
            "Number:",
            cast("list[str]", list(self.NUMBER_MAP.values())),
            "verb_number_combo",
        )
        self.verb_aspect_combo = self._create_combo(
            "Aspect:",
            cast("list[str]", list(self.VERB_ASPECT_MAP.values())),
            "verb_aspect_combo",
        )
        self.verb_form_combo = self._create_combo(
            "Form:",
            cast("list[str]", list(self.VERB_FORM_MAP.values())),
            "verb_form_combo",
        )

    def _add_adjective_fields_to_form(self) -> None:
        """Add adjective fields to form."""
        self.adj_degree_combo = self._create_combo(
            "Degree:",
            cast("list[str]", list(self.ADJECTIVE_DEGREE_MAP.values())),
            "adj_degree_combo",
        )
        self.adj_inflection_combo = self._create_combo(
            "Inflection:",
            cast("list[str]", list(self.ADJECTIVE_INFLECTION_MAP.values())),
            "adj_inflection_combo",
        )
        self.adj_gender_combo = self._create_combo(
            "Gender:",
            cast("list[str]", list(self.GENDER_MAP.values())),
            "adj_gender_combo",
        )
        self.adj_number_combo = self._create_combo(
            "Number:",
            cast("list[str]", list(self.NUMBER_MAP.values())),
            "adj_number_combo",
        )
        self.adj_case_combo = self._create_combo(
            "Case:", cast("list[str]", list(self.CASE_MAP.values())), "adj_case_combo"
        )

    def _add_pronoun_fields_to_form(self) -> None:
        """Add pronoun fields to form."""
        self.pro_type_combo = self._create_combo(
            "Type:",
            cast("list[str]", list(self.PRONOUN_TYPE_MAP.values())),
            "pro_type_combo",
        )
        self.pro_gender_combo = self._create_combo(
            "Gender:",
            cast("list[str]", list(self.GENDER_MAP.values())),
            "pro_gender_combo",
        )
        self.pro_number_combo = self._create_combo(
            "Number:",
            cast("list[str]", list(self.PRONOUN_NUMBER_MAP.values())),
            "pro_number_combo",
        )
        self.pro_case_combo = self._create_combo(
            "Case:", cast("list[str]", list(self.CASE_MAP.values())), "pro_case_combo"
        )

    def _add_article_fields_to_form(self) -> None:
        """Add article fields to form."""
        self.article_type_combo = self._create_combo(
            "Type:",
            cast("list[str]", list(self.ARTICLE_TYPE_MAP.values())),
            "article_type_combo",
        )
        self.article_gender_combo = self._create_combo(
            "Gender:",
            cast("list[str]", list(self.GENDER_MAP.values())),
            "article_gender_combo",
        )
        self.article_number_combo = self._create_combo(
            "Number:",
            cast("list[str]", list(self.NUMBER_MAP.values())),
            "article_number_combo",
        )
        self.article_case_combo = self._create_combo(
            "Case:",
            cast("list[str]", list(self.CASE_MAP.values())),
            "article_case_combo",
        )

    def _create_combo(
        self, label: str, items: list[str], object_name: str | None = None
    ) -> QComboBox:
        """
        Create a combo box and add it to the form.

        The combo box will have an empty string as the first item and "Clear" as the
        second item. The actual items will be added after these two.

        If the user sets the QComboBox to "Clear", the value will be set to
        :var:`CLEAR_SENTINEL`, which, when applied to an annotation, will clear the
        field.

        If the user sets the QComboBox to an empty string, the value will be set to
        :data:`None`, which, when applied to an annotation, will leave the field
        unchanged.

        Args:
            label: Label for the combo box
            items: List of items for the combo box
            object_name: Object name for the combo box

        Returns:
            Combo box

        """
        combo = QComboBox()
        if object_name:
            combo.setObjectName(object_name)
        # Add empty string first (index 0), then "Clear" (index 1), then actual items
        # Skip the first item from items list since it's already an empty string
        combo.addItem("")  # Empty (index 0)
        combo.addItem("Clear")  # Clear (index 1)
        if items and items[0] == "":  # Skip the empty string if it's the first item
            combo.addItems(items[1:])  # Actual values start at index 2
        else:
            combo.addItems(items)  # If no empty at start, add all items
        self.form_layout.addRow(label, combo)
        return combo

    def _create_editable_combo(
        self, label: str, items: list[str], object_name: str | None = None
    ) -> QComboBox:
        """
        Create an editable combo box and add it to the form.

        Args:
            label: Label for the combo box
            items: List of items for the combo box
            object_name: Object name for the combo box

        Returns:
            Combo box

        """
        combo = QComboBox()
        combo.setEditable(True)
        if object_name:
            combo.setObjectName(object_name)
        combo.addItems(items)
        self.form_layout.addRow(label, combo)
        return combo

    def _load_presets_for_pos(self, pos: PresetPos) -> None:
        """
        Load presets into list widget for a POS.

        Args:
            pos: POS code (N, V, A, R, D)

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
                item.setData(256, preset.id)  # Qt.ItemDataRole.UserRole

    def _find_preset_list(self, pos: PresetPos) -> QListWidget | None:
        """
        Find the preset list widget for a POS.

        Args:
            pos: POS code (N, V, A, R, D)

        Returns:
            Preset list widget

        """
        if self.save_mode:
            return None
        tab = self.tabs.get(pos)
        if not tab:
            return None
        return tab.findChild(QListWidget, f"preset_list_{pos}")

    def _on_new_preset(self, pos: PresetPos) -> None:
        """
        Clear form and prepare for new preset creation.

        Args:
            pos: POS code (N, V, A, R, D)

        """
        self.current_preset_id = None
        self.current_pos = pos
        self._clear_form()
        self._switch_to_pos_tab(pos)

    def _on_edit_preset(self) -> None:
        """Load selected preset into form for editing."""
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        pos_codes = ["N", "V", "A", "R", "D"]
        if current_tab_index >= len(pos_codes):
            return

        pos = pos_codes[current_tab_index]
        preset_list = self._find_preset_list(cast("PresetPos", pos))
        if not preset_list:
            return

        current_item = preset_list.currentItem()
        if not current_item:
            return

        preset_id = current_item.data(256)  # Qt.ItemDataRole.UserRole
        if not preset_id:
            return

        preset = AnnotationPreset.get(preset_id)
        if not preset:
            return

        self.current_preset_id = preset_id
        self.current_pos = cast("PresetPos", preset.pos)
        self._load_preset_into_form(preset)

    def _on_delete_preset(self) -> None:
        """Delete selected preset with confirmation dialog."""
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        pos_codes = ["N", "V", "A", "R", "D"]
        if current_tab_index >= len(pos_codes):
            return

        pos = pos_codes[current_tab_index]
        preset_list = self._find_preset_list(cast("PresetPos", pos))
        if not preset_list:
            return

        current_item = preset_list.currentItem()
        if not current_item:
            return

        preset_id = current_item.data(256)  # Qt.ItemDataRole.UserRole
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
            self._load_presets_for_pos(cast("PresetPos", pos))
            self._clear_form()

    def _on_preset_selected(self) -> None:
        """Handle preset selection change."""
        # Enable/disable edit and delete buttons based on selection
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        pos_codes = ["N", "V", "A", "R", "D"]
        if current_tab_index >= len(pos_codes):
            return

        pos = pos_codes[current_tab_index]
        preset_list = self._find_preset_list(cast("PresetPos", pos))
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
        Load preset values into form widgets.

        Args:
            preset: Preset to load

        """
        # Switch to the correct tab
        self._switch_to_pos_tab(cast("PresetPos", preset.pos))
        self.current_pos = cast("PresetPos", preset.pos)
        self.current_preset_id = preset.id

        # Set name
        name_edit = self._find_name_edit(cast("PresetPos", preset.pos))
        if name_edit:
            name_edit.setText(preset.name)

        # Load field values
        field_values = {
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
            "adjective_inflection": preset.adjective_inflection,
            "adjective_degree": preset.adjective_degree,
        }
        self._load_field_values(field_values)

    def _find_name_edit(self, pos: PresetPos) -> QLineEdit | None:
        """
        Find the name edit widget for a POS.

        Args:
            pos: POS code (N, V, A, R, D)

        Returns:
            Name edit widget

        """
        if self.save_mode:
            return self.name_edit
        tab = self.tabs.get(pos)
        if not tab:
            return None
        return tab.findChild(QLineEdit, f"name_edit_{pos}")

    def _load_field_values(self, field_values: dict[str, str | None]) -> None:
        """
        Load field values into form widgets.

        Args:
            field_values: Dictionary of field values to load

        """
        # This needs to be implemented based on current POS and form structure
        # For save mode, widgets are direct attributes
        # For full mode, need to find widgets in current tab
        if self.save_mode:
            self._load_field_values_save_mode(field_values)
        else:
            self._load_field_values_full_mode(field_values)

    def _load_field_values_save_mode(self, field_values: dict[str, str | None]) -> None:  # noqa: PLR0912, PLR0915
        """
        Load field values in save mode.

        Args:
            field_values: Dictionary of field values to load

        """
        pos = self.current_pos or self.initial_pos
        if not pos:
            return

        if pos == "N":
            if "gender" in field_values and hasattr(self, "gender_combo"):
                self._set_combo_value(
                    self.gender_combo, field_values["gender"], self.GENDER_REVERSE_MAP
                )
            if "number" in field_values and hasattr(self, "number_combo"):
                self._set_combo_value(
                    self.number_combo, field_values["number"], self.NUMBER_REVERSE_MAP
                )
            if "case" in field_values and hasattr(self, "case_combo"):
                self._set_combo_value(
                    self.case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
            if "declension" in field_values and hasattr(self, "declension_combo"):
                if field_values["declension"]:
                    self.declension_combo.setCurrentText(field_values["declension"])
        elif pos == "V":
            if "verb_class" in field_values and hasattr(self, "verb_class_combo"):
                if field_values["verb_class"]:
                    self.verb_class_combo.setCurrentText(field_values["verb_class"])
            if "verb_tense" in field_values and hasattr(self, "verb_tense_combo"):
                self._set_combo_value(
                    self.verb_tense_combo,
                    field_values["verb_tense"],
                    self.VERB_TENSE_REVERSE_MAP,
                )
            if "verb_mood" in field_values and hasattr(self, "verb_mood_combo"):
                self._set_combo_value(
                    self.verb_mood_combo,
                    field_values["verb_mood"],
                    self.VERB_MOOD_REVERSE_MAP,
                )
            if "verb_person" in field_values and hasattr(self, "verb_person_combo"):
                self._set_combo_value(
                    self.verb_person_combo,
                    field_values["verb_person"],
                    self.VERB_PERSON_REVERSE_MAP,
                )
            if "number" in field_values and hasattr(self, "verb_number_combo"):
                self._set_combo_value(
                    self.verb_number_combo,
                    field_values["number"],
                    self.NUMBER_REVERSE_MAP,
                )
            if "verb_aspect" in field_values and hasattr(self, "verb_aspect_combo"):
                self._set_combo_value(
                    self.verb_aspect_combo,
                    field_values["verb_aspect"],
                    self.VERB_ASPECT_REVERSE_MAP,
                )
            if "verb_form" in field_values and hasattr(self, "verb_form_combo"):
                self._set_combo_value(
                    self.verb_form_combo,
                    field_values["verb_form"],
                    self.VERB_FORM_REVERSE_MAP,
                )
        elif pos == "A":
            if "adjective_degree" in field_values and hasattr(self, "adj_degree_combo"):
                self._set_combo_value(
                    self.adj_degree_combo,
                    field_values["adjective_degree"],
                    self.ADJECTIVE_DEGREE_REVERSE_MAP,
                )
            if "adjective_inflection" in field_values and hasattr(
                self, "adj_inflection_combo"
            ):
                self._set_combo_value(
                    self.adj_inflection_combo,
                    field_values["adjective_inflection"],
                    self.ADJECTIVE_INFLECTION_REVERSE_MAP,
                )
            if "gender" in field_values and hasattr(self, "adj_gender_combo"):
                self._set_combo_value(
                    self.adj_gender_combo,
                    field_values["gender"],
                    self.GENDER_REVERSE_MAP,
                )
            if "number" in field_values and hasattr(self, "adj_number_combo"):
                self._set_combo_value(
                    self.adj_number_combo,
                    field_values["number"],
                    self.NUMBER_REVERSE_MAP,
                )
            if "case" in field_values and hasattr(self, "adj_case_combo"):
                self._set_combo_value(
                    self.adj_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
        elif pos == "R":
            if "pronoun_type" in field_values and hasattr(self, "pro_type_combo"):
                self._set_combo_value(
                    self.pro_type_combo,
                    field_values["pronoun_type"],
                    self.PRONOUN_TYPE_REVERSE_MAP,
                )
            if "gender" in field_values and hasattr(self, "pro_gender_combo"):
                self._set_combo_value(
                    self.pro_gender_combo,
                    field_values["gender"],
                    self.GENDER_REVERSE_MAP,
                )
            if "pronoun_number" in field_values and hasattr(self, "pro_number_combo"):
                self._set_combo_value(
                    self.pro_number_combo,
                    field_values["pronoun_number"],
                    self.PRONOUN_NUMBER_REVERSE_MAP,
                )
            if "case" in field_values and hasattr(self, "pro_case_combo"):
                self._set_combo_value(
                    self.pro_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
        elif pos == "D":
            if "article_type" in field_values and hasattr(self, "article_type_combo"):
                self._set_combo_value(
                    self.article_type_combo,
                    field_values["article_type"],
                    self.ARTICLE_TYPE_REVERSE_MAP,
                )
            if "gender" in field_values and hasattr(self, "article_gender_combo"):
                self._set_combo_value(
                    self.article_gender_combo,
                    field_values["gender"],
                    self.GENDER_REVERSE_MAP,
                )
            if "number" in field_values and hasattr(self, "article_number_combo"):
                self._set_combo_value(
                    self.article_number_combo,
                    field_values["number"],
                    self.NUMBER_REVERSE_MAP,
                )
            if "case" in field_values and hasattr(self, "article_case_combo"):
                self._set_combo_value(
                    self.article_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )

    def _load_field_values_full_mode(self, field_values: dict[str, str | None]) -> None:  # noqa: PLR0912, PLR0915
        """
        Load field values in full mode.

        Args:
            field_values: Dictionary of field values to load

        """
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < 0:
            return

        pos_codes = ["N", "V", "A", "R", "D"]
        if current_tab_index >= len(pos_codes):
            return

        pos = pos_codes[current_tab_index]
        tab = self.tabs.get(pos)
        if not tab:
            return

        form_widget = tab.findChild(QWidget, f"form_widget_{pos}")
        if not form_widget:
            return

        # Load values into widgets found in the tab
        if pos == "N":
            gender_combo = form_widget.findChild(QComboBox, "gender_combo")
            if gender_combo and "gender" in field_values:
                self._set_combo_value(
                    gender_combo, field_values["gender"], self.GENDER_REVERSE_MAP
                )
            number_combo = form_widget.findChild(QComboBox, "number_combo")
            if number_combo and "number" in field_values:
                self._set_combo_value(
                    number_combo, field_values["number"], self.NUMBER_REVERSE_MAP
                )
            case_combo = form_widget.findChild(QComboBox, "case_combo")
            if case_combo and "case" in field_values:
                self._set_combo_value(
                    case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
            declension_combo = form_widget.findChild(QComboBox, "declension_combo")
            if (
                declension_combo
                and "declension" in field_values
                and field_values["declension"]
            ):
                declension_combo.setCurrentText(field_values["declension"])
        elif pos == "V":
            verb_class_combo = form_widget.findChild(QComboBox, "verb_class_combo")
            if (
                verb_class_combo
                and "verb_class" in field_values
                and field_values["verb_class"]
            ):
                verb_class_combo.setCurrentText(field_values["verb_class"])
            verb_tense_combo = form_widget.findChild(QComboBox, "verb_tense_combo")
            if verb_tense_combo and "verb_tense" in field_values:
                self._set_combo_value(
                    verb_tense_combo,
                    field_values["verb_tense"],
                    self.VERB_TENSE_REVERSE_MAP,
                )
            verb_mood_combo = form_widget.findChild(QComboBox, "verb_mood_combo")
            if verb_mood_combo and "verb_mood" in field_values:
                self._set_combo_value(
                    verb_mood_combo,
                    field_values["verb_mood"],
                    self.VERB_MOOD_REVERSE_MAP,
                )
            verb_person_combo = form_widget.findChild(QComboBox, "verb_person_combo")
            if verb_person_combo and "verb_person" in field_values:
                self._set_combo_value(
                    verb_person_combo,
                    field_values["verb_person"],
                    self.VERB_PERSON_REVERSE_MAP,
                )
            verb_number_combo = form_widget.findChild(QComboBox, "verb_number_combo")
            if verb_number_combo and "number" in field_values:
                self._set_combo_value(
                    verb_number_combo, field_values["number"], self.NUMBER_REVERSE_MAP
                )
            verb_aspect_combo = form_widget.findChild(QComboBox, "verb_aspect_combo")
            if verb_aspect_combo and "verb_aspect" in field_values:
                self._set_combo_value(
                    verb_aspect_combo,
                    field_values["verb_aspect"],
                    self.VERB_ASPECT_REVERSE_MAP,
                )
            verb_form_combo = form_widget.findChild(QComboBox, "verb_form_combo")
            if verb_form_combo and "verb_form" in field_values:
                self._set_combo_value(
                    verb_form_combo,
                    field_values["verb_form"],
                    self.VERB_FORM_REVERSE_MAP,
                )
        elif pos == "A":
            adj_degree_combo = form_widget.findChild(QComboBox, "adj_degree_combo")
            if adj_degree_combo and "adjective_degree" in field_values:
                self._set_combo_value(
                    adj_degree_combo,
                    field_values["adjective_degree"],
                    self.ADJECTIVE_DEGREE_REVERSE_MAP,
                )
            adj_inflection_combo = form_widget.findChild(
                QComboBox, "adj_inflection_combo"
            )
            if adj_inflection_combo and "adjective_inflection" in field_values:
                self._set_combo_value(
                    adj_inflection_combo,
                    field_values["adjective_inflection"],
                    self.ADJECTIVE_INFLECTION_REVERSE_MAP,
                )
            adj_gender_combo = form_widget.findChild(QComboBox, "adj_gender_combo")
            if adj_gender_combo and "gender" in field_values:
                self._set_combo_value(
                    adj_gender_combo, field_values["gender"], self.GENDER_REVERSE_MAP
                )
            adj_number_combo = form_widget.findChild(QComboBox, "adj_number_combo")
            if adj_number_combo and "number" in field_values:
                self._set_combo_value(
                    adj_number_combo, field_values["number"], self.NUMBER_REVERSE_MAP
                )
            adj_case_combo = form_widget.findChild(QComboBox, "adj_case_combo")
            if adj_case_combo and "case" in field_values:
                self._set_combo_value(
                    adj_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
        elif pos == "R":
            pro_type_combo = form_widget.findChild(QComboBox, "pro_type_combo")
            if pro_type_combo and "pronoun_type" in field_values:
                self._set_combo_value(
                    pro_type_combo,
                    field_values["pronoun_type"],
                    self.PRONOUN_TYPE_REVERSE_MAP,
                )
            pro_gender_combo = form_widget.findChild(QComboBox, "pro_gender_combo")
            if pro_gender_combo and "gender" in field_values:
                self._set_combo_value(
                    pro_gender_combo, field_values["gender"], self.GENDER_REVERSE_MAP
                )
            pro_number_combo = form_widget.findChild(QComboBox, "pro_number_combo")
            if pro_number_combo and "pronoun_number" in field_values:
                self._set_combo_value(
                    pro_number_combo,
                    field_values["pronoun_number"],
                    self.PRONOUN_NUMBER_REVERSE_MAP,
                )
            pro_case_combo = form_widget.findChild(QComboBox, "pro_case_combo")
            if pro_case_combo and "case" in field_values:
                self._set_combo_value(
                    pro_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )
        elif pos == "D":
            article_type_combo = form_widget.findChild(QComboBox, "article_type_combo")
            if article_type_combo and "article_type" in field_values:
                self._set_combo_value(
                    article_type_combo,
                    field_values["article_type"],
                    self.ARTICLE_TYPE_REVERSE_MAP,
                )
            article_gender_combo = form_widget.findChild(
                QComboBox, "article_gender_combo"
            )
            if article_gender_combo and "gender" in field_values:
                self._set_combo_value(
                    article_gender_combo,
                    field_values["gender"],
                    self.GENDER_REVERSE_MAP,
                )
            article_number_combo = form_widget.findChild(
                QComboBox, "article_number_combo"
            )
            if article_number_combo and "number" in field_values:
                self._set_combo_value(
                    article_number_combo,
                    field_values["number"],
                    self.NUMBER_REVERSE_MAP,
                )
            article_case_combo = form_widget.findChild(QComboBox, "article_case_combo")
            if article_case_combo and "case" in field_values:
                self._set_combo_value(
                    article_case_combo, field_values["case"], self.CASE_REVERSE_MAP
                )

    def _extract_combo_value(self, idx: int, reverse_map: dict) -> str | None:
        """
        Extract value from combo box index.

        Args:
            idx: Combo box current index
            reverse_map: Reverse map to convert index to code

        Returns:
            None if empty (don't change), CLEAR_SENTINEL if Clear (clear field),
            or the actual code value

        """
        if idx == 0:
            return None  # Empty - don't change
        if idx == 1:
            return CLEAR_SENTINEL  # Clear - explicitly clear field
        return reverse_map.get(idx - 1)

    def _set_combo_value(
        self, combo: QComboBox, value: str | None, reverse_map: dict[int, str]
    ) -> None:
        """
        Set combo box value using reverse map.

        Args:
            combo: Combo box to set the value for
            value: Value to set
            reverse_map: Reverse map to convert index to code

        """
        if value is None:
            # Set to empty (index 0), not "Clear" (index 1)
            # "Clear" is for explicitly clearing a field when applying a preset
            # Empty (index 0) represents an unset field in the preset itself
            combo.setCurrentIndex(0)
            return
        if value == CLEAR_SENTINEL:
            # Set to "Clear" (index 1)
            combo.setCurrentIndex(1)
            return
        # Find the code in REVERSE_MAP to get its original index
        # value is a valid code (not None, not CLEAR_SENTINEL)
        #
        # REVERSE_MAP maps original combo index to code: {1: "m", 2: "f", ...}
        #
        # Original combo (from MAP.values()): [0: "", 1: "Masculine", 2:
        # "Feminine", ...]
        #
        # New combo: [0: "", 1: "Clear", 2: "Masculine", 3: "Feminine", ...]
        #
        # REVERSE_MAP key 1 means original combo index 1, which is now at new
        # combo index 2
        # Formula: new_index = REVERSE_MAP_key + 1 (to account for "Clear" at index 1)
        code_to_original_index = {v: k for k, v in reverse_map.items()}
        original_index = code_to_original_index.get(value)
        if original_index is not None:
            # Add 1 to account for "Clear" at index 1 (empty at 0 is already
            # accounted for)
            combo.setCurrentIndex(original_index + 1)
        else:
            # Code not found, default to empty (index 0)
            combo.setCurrentIndex(0)

    def _clear_preset_form(self, pos: str) -> None:
        """
        Clear form fields for a specific POS tab (name and all dropdowns).

        Args:
            pos: POS code (N, V, A, R, D)

        """
        # Clear name field
        name_edit = self._find_name_edit(cast("PresetPos", pos))
        if name_edit:
            name_edit.clear()

        # Clear all combo boxes in the form widget for this POS
        tab = self.tabs.get(pos)
        if tab:
            form_widget = tab.findChild(QWidget, f"form_widget_{pos}")
            if form_widget:
                # Find all combo boxes in the form widget
                combos = form_widget.findChildren(QComboBox)
                for combo in combos:
                    combo.setCurrentIndex(0)  # Set to empty (index 0)

        # Clear current preset ID since we're clearing the form
        self.current_preset_id = None

    def _clear_form(self) -> None:
        """Clear form fields and reset to default state."""
        if self.save_mode:
            if hasattr(self, "name_edit"):
                self.name_edit.clear()
            # Clear all combo boxes
            for attr_name in dir(self):
                if attr_name.endswith("_combo"):
                    combo = getattr(self, attr_name, None)
                    if isinstance(combo, QComboBox):
                        combo.setCurrentIndex(0)
        else:
            # Clear form in current tab
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index >= 0:
                pos_codes = ["N", "V", "A", "R", "D"]
                if current_tab_index < len(pos_codes):
                    pos = pos_codes[current_tab_index]
                    name_edit = self._find_name_edit(cast("PresetPos", pos))
                    if name_edit:
                        name_edit.clear()

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change - clear preset ID if switching tabs manually."""
        # Only clear if this is a manual tab change (not programmatic)
        # We can detect this by checking if current_preset_id is set but doesn't match
        # the POS of the new tab
        if self.current_preset_id is not None:
            pos_codes = ["N", "V", "A", "R", "D"]
            if 0 <= index < len(pos_codes):
                new_pos = pos_codes[index]
                # If we have a preset ID but it's for a different POS, clear it
                # This handles the case where user manually switches tabs
                if self.current_pos != new_pos:
                    self.current_preset_id = None
                    self.current_pos = cast("PresetPos", new_pos)
                    self._clear_form()

    def _switch_to_pos_tab(self, pos: PresetPos) -> None:
        """
        Switch to the tab for the specified POS.

        Args:
            pos: POS code (N, V, A, R, D)

        """
        if not hasattr(self, "tab_widget"):
            return
        pos_codes = ["N", "V", "A", "R", "D"]
        if pos in pos_codes:
            index = pos_codes.index(pos)
            # Temporarily disconnect signal to avoid clearing preset ID during
            # programmatic switch
            with suppress(TypeError):
                self.tab_widget.currentChanged.disconnect(self._on_tab_changed)
            self.tab_widget.setCurrentIndex(index)
            # Reconnect signal
            self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _validate_preset(self) -> tuple[bool, str]:  # noqa: PLR0911
        """
        Validate preset name.

        Returns:
            Tuple of (is_valid, error_message)

        """
        if self.save_mode:
            name = self.name_edit.text().strip()
            pos = self.initial_pos
        else:
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                return False, "No POS selected"
            pos_codes = ["N", "V", "A", "R", "D"]
            if current_tab_index >= len(pos_codes):
                return False, "Invalid POS"
            pos = cast("PresetPos", pos_codes[current_tab_index])
            name_edit = self._find_name_edit(cast("PresetPos", pos))
            if not name_edit:
                return False, "Name field not found"
            name = name_edit.text().strip()

        if not name:
            return False, "Preset name is required"

        # Check for duplicate name per POS
        if not pos:
            return False, "POS is required"

        existing_presets = self.preset_service.get_presets_for_pos(pos)
        for preset in existing_presets:
            if (
                preset.id != self.current_preset_id
                and preset.name.lower() == name.lower()
            ):
                return False, f"Preset '{name}' already exists for this part of speech"

        return True, ""

    def _save_preset(self) -> None:  # noqa: PLR0912
        """Save preset (create or update) with validation."""
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
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index < 0:
                return
            pos_codes = ["N", "V", "A", "R", "D"]
            if current_tab_index >= len(pos_codes):
                return
            pos = cast("PresetPos", pos_codes[current_tab_index])
            name_edit = self._find_name_edit(cast("PresetPos", pos))
            if not name_edit:
                return
            name = name_edit.text().strip()
            field_values = self._extract_field_values_for_tab(cast("PresetPos", pos))

        try:
            # Only update if we have a preset ID AND it matches the current POS
            # This prevents updating a preset from a different POS tab
            if self.current_preset_id:
                # Verify the preset still exists and matches the current POS
                preset = AnnotationPreset.get(self.current_preset_id)
                if preset and preset.pos == pos:
                    self.preset_service.update_preset(
                        self.current_preset_id, name, field_values
                    )
                else:
                    # Preset doesn't exist or POS doesn't match - create new instead
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
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:  # noqa: BLE001
            if isinstance(e, IntegrityError):
                QMessageBox.warning(
                    self,
                    "Error",
                    "A preset with this name already exists for this part of speech.",
                )
            else:
                QMessageBox.critical(self, "Error", f"Failed to save preset: {e}")

    def _extract_field_values(self) -> dict[str, str | None]:  # noqa: PLR0912, PLR0915
        """Extract field values from form in save mode."""
        pos = self.initial_pos
        if not pos:
            return {}

        field_values = {}
        if pos == "N":
            if hasattr(self, "gender_combo"):
                idx = self.gender_combo.currentIndex()
                # Index 0 = "" (empty) = None, index 1 = "Clear" = None, index
                # 2+ = actual values
                #
                # REVERSE_MAP indices start at 1 (skipping the empty at index 0
                # in original)
                #
                # Original combo: [0: "", 1: "Masculine", 2: "Feminine", ...]
                #
                # REVERSE_MAP: {1: "m", 2: "f", ...} where key is original combo index
                #
                # New combo: [0: "", 1: "Clear", 2: "Masculine", 3: "Feminine", ...]
                #
                # So combo index 2 maps to REVERSE_MAP[1], combo index 3 maps to
                # REVERSE_MAP[2], etc.
                #
                # Formula: REVERSE_MAP.get(idx - 1) because idx-1 gives us the
                # original index
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            if hasattr(self, "number_combo"):
                idx = self.number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            if hasattr(self, "case_combo"):
                idx = self.case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
            if hasattr(self, "declension_combo"):
                text = self.declension_combo.currentText().strip()
                field_values["declension"] = text if text else None
        elif pos == "V":
            if hasattr(self, "verb_class_combo"):
                text = self.verb_class_combo.currentText().strip()
                field_values["verb_class"] = text if text else None
            if hasattr(self, "verb_tense_combo"):
                idx = self.verb_tense_combo.currentIndex()
                field_values["verb_tense"] = self._extract_combo_value(
                    idx, self.VERB_TENSE_REVERSE_MAP
                )
            if hasattr(self, "verb_mood_combo"):
                idx = self.verb_mood_combo.currentIndex()
                field_values["verb_mood"] = self._extract_combo_value(
                    idx, self.VERB_MOOD_REVERSE_MAP
                )
            if hasattr(self, "verb_person_combo"):
                idx = self.verb_person_combo.currentIndex()
                field_values["verb_person"] = self._extract_combo_value(
                    idx, self.VERB_PERSON_REVERSE_MAP
                )
            if hasattr(self, "verb_number_combo"):
                idx = self.verb_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            if hasattr(self, "verb_aspect_combo"):
                idx = self.verb_aspect_combo.currentIndex()
                field_values["verb_aspect"] = self._extract_combo_value(
                    idx, self.VERB_ASPECT_REVERSE_MAP
                )
            if hasattr(self, "verb_form_combo"):
                idx = self.verb_form_combo.currentIndex()
                field_values["verb_form"] = self._extract_combo_value(
                    idx, self.VERB_FORM_REVERSE_MAP
                )
        elif pos == "A":
            if hasattr(self, "adj_degree_combo"):
                idx = self.adj_degree_combo.currentIndex()
                field_values["adjective_degree"] = self._extract_combo_value(
                    idx, self.ADJECTIVE_DEGREE_REVERSE_MAP
                )
            if hasattr(self, "adj_inflection_combo"):
                idx = self.adj_inflection_combo.currentIndex()
                field_values["adjective_inflection"] = self._extract_combo_value(
                    idx, self.ADJECTIVE_INFLECTION_REVERSE_MAP
                )
            if hasattr(self, "adj_gender_combo"):
                idx = self.adj_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            if hasattr(self, "adj_number_combo"):
                idx = self.adj_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            if hasattr(self, "adj_case_combo"):
                idx = self.adj_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
        elif pos == "R":
            if hasattr(self, "pro_type_combo"):
                idx = self.pro_type_combo.currentIndex()
                field_values["pronoun_type"] = self._extract_combo_value(
                    idx, self.PRONOUN_TYPE_REVERSE_MAP
                )
            if hasattr(self, "pro_gender_combo"):
                idx = self.pro_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            if hasattr(self, "pro_number_combo"):
                idx = self.pro_number_combo.currentIndex()
                field_values["pronoun_number"] = self._extract_combo_value(
                    idx, self.PRONOUN_NUMBER_REVERSE_MAP
                )
            if hasattr(self, "pro_case_combo"):
                idx = self.pro_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
        elif pos == "D":
            if hasattr(self, "article_type_combo"):
                idx = self.article_type_combo.currentIndex()
                field_values["article_type"] = self._extract_combo_value(
                    idx, self.ARTICLE_TYPE_REVERSE_MAP
                )
            if hasattr(self, "article_gender_combo"):
                idx = self.article_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            if hasattr(self, "article_number_combo"):
                idx = self.article_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            if hasattr(self, "article_case_combo"):
                idx = self.article_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
        return field_values

    def _extract_field_values_for_tab(self, pos: PresetPos) -> dict[str, str | None]:  # noqa: PLR0912, PLR0915
        """
        Extract field values from form in full mode.

        Args:
            pos: POS code (N, V, A, R, D)

        Returns:
            Dictionary of field values

        """
        tab = self.tabs.get(pos)
        if not tab:
            return {}

        field_values = {}
        form_widget = tab.findChild(QWidget, f"form_widget_{pos}")
        if not form_widget:
            return {}

        # Find combo boxes by object name
        if pos == "N":
            gender_combo = form_widget.findChild(QComboBox, "gender_combo")
            if gender_combo:
                idx = gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            number_combo = form_widget.findChild(QComboBox, "number_combo")
            if number_combo:
                idx = number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            case_combo = form_widget.findChild(QComboBox, "case_combo")
            if case_combo:
                idx = case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
            declension_combo = form_widget.findChild(QComboBox, "declension_combo")
            if declension_combo:
                text = declension_combo.currentText().strip()
                field_values["declension"] = text if text else None
        elif pos == "V":
            verb_class_combo = form_widget.findChild(QComboBox, "verb_class_combo")
            if verb_class_combo:
                text = verb_class_combo.currentText().strip()
                field_values["verb_class"] = text if text else None
            verb_tense_combo = form_widget.findChild(QComboBox, "verb_tense_combo")
            if verb_tense_combo:
                idx = verb_tense_combo.currentIndex()
                field_values["verb_tense"] = self._extract_combo_value(
                    idx, self.VERB_TENSE_REVERSE_MAP
                )
            verb_mood_combo = form_widget.findChild(QComboBox, "verb_mood_combo")
            if verb_mood_combo:
                idx = verb_mood_combo.currentIndex()
                field_values["verb_mood"] = self._extract_combo_value(
                    idx, self.VERB_MOOD_REVERSE_MAP
                )
            verb_person_combo = form_widget.findChild(QComboBox, "verb_person_combo")
            if verb_person_combo:
                idx = verb_person_combo.currentIndex()
                field_values["verb_person"] = self._extract_combo_value(
                    idx, self.VERB_PERSON_REVERSE_MAP
                )
            verb_number_combo = form_widget.findChild(QComboBox, "verb_number_combo")
            if verb_number_combo:
                idx = verb_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            verb_aspect_combo = form_widget.findChild(QComboBox, "verb_aspect_combo")
            if verb_aspect_combo:
                idx = verb_aspect_combo.currentIndex()
                field_values["verb_aspect"] = self._extract_combo_value(
                    idx, self.VERB_ASPECT_REVERSE_MAP
                )
            verb_form_combo = form_widget.findChild(QComboBox, "verb_form_combo")
            if verb_form_combo:
                idx = verb_form_combo.currentIndex()
                field_values["verb_form"] = self._extract_combo_value(
                    idx, self.VERB_FORM_REVERSE_MAP
                )
        elif pos == "A":
            adj_degree_combo = form_widget.findChild(QComboBox, "adj_degree_combo")
            if adj_degree_combo:
                idx = adj_degree_combo.currentIndex()
                field_values["adjective_degree"] = self._extract_combo_value(
                    idx, self.ADJECTIVE_DEGREE_REVERSE_MAP
                )
            adj_inflection_combo = form_widget.findChild(
                QComboBox, "adj_inflection_combo"
            )
            if adj_inflection_combo:
                idx = adj_inflection_combo.currentIndex()
                field_values["adjective_inflection"] = self._extract_combo_value(
                    idx, self.ADJECTIVE_INFLECTION_REVERSE_MAP
                )
            adj_gender_combo = form_widget.findChild(QComboBox, "adj_gender_combo")
            if adj_gender_combo:
                idx = adj_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            adj_number_combo = form_widget.findChild(QComboBox, "adj_number_combo")
            if adj_number_combo:
                idx = adj_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            adj_case_combo = form_widget.findChild(QComboBox, "adj_case_combo")
            if adj_case_combo:
                idx = adj_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
        elif pos == "R":
            pro_type_combo = form_widget.findChild(QComboBox, "pro_type_combo")
            if pro_type_combo:
                idx = pro_type_combo.currentIndex()
                field_values["pronoun_type"] = self._extract_combo_value(
                    idx, self.PRONOUN_TYPE_REVERSE_MAP
                )
            pro_gender_combo = form_widget.findChild(QComboBox, "pro_gender_combo")
            if pro_gender_combo:
                idx = pro_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            pro_number_combo = form_widget.findChild(QComboBox, "pro_number_combo")
            if pro_number_combo:
                idx = pro_number_combo.currentIndex()
                field_values["pronoun_number"] = self._extract_combo_value(
                    idx, self.PRONOUN_NUMBER_REVERSE_MAP
                )
            pro_case_combo = form_widget.findChild(QComboBox, "pro_case_combo")
            if pro_case_combo:
                idx = pro_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )
        elif pos == "D":
            article_type_combo = form_widget.findChild(QComboBox, "article_type_combo")
            if article_type_combo:
                idx = article_type_combo.currentIndex()
                field_values["article_type"] = self._extract_combo_value(
                    idx, self.ARTICLE_TYPE_REVERSE_MAP
                )
            article_gender_combo = form_widget.findChild(
                QComboBox, "article_gender_combo"
            )
            if article_gender_combo:
                idx = article_gender_combo.currentIndex()
                field_values["gender"] = self._extract_combo_value(
                    idx, self.GENDER_REVERSE_MAP
                )
            article_number_combo = form_widget.findChild(
                QComboBox, "article_number_combo"
            )
            if article_number_combo:
                idx = article_number_combo.currentIndex()
                field_values["number"] = self._extract_combo_value(
                    idx, self.NUMBER_REVERSE_MAP
                )
            article_case_combo = form_widget.findChild(QComboBox, "article_case_combo")
            if article_case_combo:
                idx = article_case_combo.currentIndex()
                field_values["case"] = self._extract_combo_value(
                    idx, self.CASE_REVERSE_MAP
                )

        return field_values
