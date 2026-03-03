"""Annotation modal dialog."""

from typing import TYPE_CHECKING, ClassVar, Final, cast

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from oeapp.models import Annotation, Idiom
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.services.annotation_preset_service import AnnotationPresetService
from oeapp.ui.dialogs.pos_form_system import (
    CLEAR_SENTINEL,
    AdjectiveFields,
    AdverbFields,
    AnnotationPosFormManager,
    ArticleFields,
    ConjunctionFields,
    InterjectionFields,
    NoneFields,
    NounFields,
    NumberFields,
    PartOfSpeechFieldsBase,
    PrepositionFields,
    PronounFields,
    VerbFields,
)
from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.models.token import Token
    from oeapp.types import PresetPos


# Backward-compatible alias expected by existing tests/importers.
PartOfSpeechFormManager = AnnotationPosFormManager

__all__ = [
    "CLEAR_SENTINEL",
    "AdjectiveFields",
    "AdverbFields",
    "AnnotationModal",
    "ArticleFields",
    "ConjunctionFields",
    "InterjectionFields",
    "NoneFields",
    "NounFields",
    "NumberFields",
    "PartOfSpeechFieldsBase",
    "PartOfSpeechFormManager",
    "PrepositionFields",
    "PronounFields",
    "VerbFields",
]


class AnnotationModal(AnnotationLookupsMixin, QDialog):
    """
    Modal dialog for annotating tokens with prompt-based entry.

    Args:
        token: Token to annotate (exclusive with idiom)
        idiom: Idiom to annotate (exclusive with token)
        annotation: Existing annotation (if any)
        parent: Parent widget

    """

    # -------------------------------------------------------------------------
    # Signals
    # -------------------------------------------------------------------------

    # Signal emitted when annotation is applied
    annotation_applied = Signal(Annotation)

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 500
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 600

    # -------------------------------------------------------------------------
    # Class-level state
    # -------------------------------------------------------------------------

    # Class-level state to remember last used values per POS type
    _last_values: ClassVar[dict[str, dict[str, int]]] = {}

    def __init__(
        self,
        token: "Token | None" = None,
        idiom: Idiom | None = None,
        annotation: Annotation | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize annotation modal.

        Args:
            token: Token to annotate (exclusive with idiom)
            idiom: Idiom to annotate (exclusive with token)

        Keyword Args:
            annotation: Existing annotation (if any)
            parent: Parent widget

        """
        # We need this here to avoid circular import
        from oeapp.ui.shortcuts import AnnotationModalShortcuts  # noqa: PLC0415

        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.token = token
        self.idiom = idiom

        if self.token:
            self._init_token_annotation(annotation)
        elif self.idiom:
            self._init_idiom_annotation(annotation)
        else:
            msg = "Neither token nor idiom was provided"
            raise ValueError(msg)

        self.preset_service = AnnotationPresetService()
        self.build()
        self.part_of_speech_manager = PartOfSpeechFormManager(
            cast("QVBoxLayout", self.fields_group.layout()), self.fields_group
        )
        AnnotationModalShortcuts(self).execute()
        self.load()

    def _init_token_annotation(self, annotation: Annotation | None) -> None:
        """
        Initialize annotation for a single token.  If we've been called,
        :attr:`token` is already set.

        Args:
            annotation: Existing annotation (if any)

        """
        # Put an assert here to help with debugging when we call this
        # method without setting :attr:`token` first.
        assert self.token is not None, (  # noqa: S101
            "_init_token_annotation called without self.token being set"
        )
        if annotation:
            self.annotation = annotation
        token = cast("Token", self.token)
        if token.annotation:
            self.annotation = token.annotation
        else:
            self.annotation = Annotation(token_id=cast("int", token.id))

    def _init_idiom_annotation(self, annotation: Annotation | None) -> None:
        """
        Initialize annotation for an idiom.  If we've been called,
        :attr:`idiom` is already set.

        Args:
            annotation: Existing annotation (if any)

        """
        # Put an assert here to help with debugging when we call this
        # method without setting :attr:`idiom` first.
        assert self.idiom is not None, (  # noqa: S101
            "_init_idiom_annotation called without self.idiom being set"
        )
        if annotation:
            self.annotation = annotation
        idiom = cast("Idiom", self.idiom)
        if idiom.annotation:
            self.annotation = idiom.annotation
        else:
            self.annotation = Annotation(idiom_id=cast("int", idiom.id))

        # Link back for creation if needed
        self.annotation.idiom = idiom

    @property
    def title_text(self) -> str:
        """
        Get the title text for the dialog.
        """
        return self.token.surface if self.token else "Idiom"

    def build(self):
        """
        Set up the UI layout.

        - Sets the window title adn window flags
        - Builds the header section
        - Builds the Part of Speech selection section
        - Builds the Part of Speech dynamic section
        - Builds the Metadata section
        - Builds the action buttons

        """
        self.setWindowTitle(f"Annotate: {self.title_text}")
        self.setModal(True)
        self.resize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)

        layout = QVBoxLayout(self)
        # Header section
        self.build_header(layout)
        layout.addSpacing(10)

        # Part of Speech Section
        self.build_pos_section(layout)

        # Dynamic fields section for specific POS types
        self.build_pos_dynamic_section(layout)

        # Metadata section
        self.build_metadata_section(layout)

        layout.addStretch()

        # Action buttons
        self.build_action_buttons(layout)

        # Keyboard shortcuts will be set up in _setup_keyboard_shortcuts()

    def build_header(self, layout: QVBoxLayout) -> None:
        """
        Set up the header area with token/idiom info.

        This is where :attr:`status_label` is set up.

        Args:
            layout: Layout to add the header to

        """
        if self.token:
            self.build_token_header(layout)
        elif self.idiom:
            self.build_idiom_header(layout)

        self.status_label = QLabel("POS: Not set", self)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

    def build_token_header(self, layout: QVBoxLayout) -> None:
        """
        Set up the token header.

        Args:
            layout: Layout to add the header to

        """
        assert self.token is not None, (  # noqa: S101
            "build_token_header called without self.token being set"
        )
        header_label = QLabel(f"Token: <b>{self.token.surface}</b>", self)
        header_label.setFont(self.font())
        layout.addWidget(header_label)

    def build_idiom_header(self, layout: QVBoxLayout) -> None:
        """
        Set up the idiom header with clickable tokens.

        Args:
            layout: Layout to add the header to

        """
        idiom = cast("Idiom", self.idiom)
        header_label = QLabel("Idiom: ", self)
        header_label.setFont(self.font())

        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(header_label)

        # Get all tokens in idiom
        start_order = idiom.start_token.order_index
        end_order = idiom.end_token.order_index

        # We need access to all tokens in the sentence
        # Assuming parent is SentenceCard
        parent = cast("QObject", self.parent())
        if hasattr(parent, "oe_text_edit"):
            for token in parent.oe_text_edit.tokens:
                if start_order <= token.order_index <= end_order:
                    btn = QPushButton(token.surface, self)
                    btn.setFlat(True)
                    btn.setStyleSheet("color: blue; text-decoration: underline;")
                    btn.clicked.connect(
                        lambda _, t=token: self._on_token_link_clicked(t)
                    )
                    tokens_layout.addWidget(btn)

        tokens_layout.addStretch()
        layout.addLayout(tokens_layout)

    def build_pos_section(self, container: QVBoxLayout) -> None:
        """
        Set up the Part of Speech section.

        Args:
            container: Container layout to add the Part of Speech section to

        """
        pos_group = QGroupBox("Part of Speech", self)
        pos_layout = QVBoxLayout()
        self.build_pos_combo(pos_layout)
        self.build_preset_selection(pos_layout)
        pos_group.setLayout(pos_layout)
        container.addWidget(pos_group)

    def build_pos_combo(self, container: QVBoxLayout) -> None:
        """
        Set up the POS selection section.

        This method adds the POS selection section to the given layout, and
        connects the currentIndexChanged signal to the _on_pos_changed method.

        This is where :attr:`pos_combo` is set up.

        Args:
            container: Container layout to add the POS selection section to

        """
        self.pos_combo = QComboBox(self)
        self.pos_combo.addItem("")  # Empty option for "no selection"
        self.pos_combo.addItems(
            cast(
                "list[str]",
                [v for v in self.PART_OF_SPEECH_MAP.values() if v is not None],
            ),
        )
        # Set initial selection to empty (index 0) and block signals to prevent
        # _on_pos_changed from firing during initialization
        self.pos_combo.blockSignals(True)  # noqa: FBT003
        self.pos_combo.setCurrentIndex(0)  # Empty selection
        self.pos_combo.blockSignals(False)  # noqa: FBT003
        self.pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        container.addWidget(self.pos_combo)

    def build_preset_selection(self, container: QVBoxLayout) -> None:
        """
        Set up the preset selection section.

        This method adds the preset selection section to the given layout, and
        connects the currentIndexChanged signal to the _on_preset_apply method.

        This is where :attr:`preset_combo` and :attr:`apply_preset_button` are set up.

        Args:
            container: Container layout to add the preset selection section to

        """
        layout = QHBoxLayout()
        self.preset_combo = QComboBox(self)
        self.preset_combo.setEnabled(False)
        layout.addWidget(QLabel("Preset:", self))
        layout.addWidget(self.preset_combo)
        self.apply_preset_button = QPushButton("Apply", self)
        self.apply_preset_button.setEnabled(False)
        self.apply_preset_button.clicked.connect(self._on_preset_apply)
        layout.addWidget(self.apply_preset_button)
        container.addLayout(layout)

    def build_pos_dynamic_section(self, container: QVBoxLayout) -> None:
        """
        Build the dynamic section for the POS.  The per-POS dynamic section
        changes based on the selected POS, and is updated by the :meth:`_on_pos_changed`
        method, which is called when :attr:`pos_combo` is changed.

        This is where :attr:`fields_group` is set up.

        Args:
            container: Container layout to add the dynamic section to

        """
        self.fields_group = QGroupBox("Annotation Fields", self)
        self.fields_group.setLayout(QVBoxLayout())
        container.addWidget(self.fields_group)

    def build_metadata_section(self, container: QVBoxLayout) -> None:
        """
        Set up the metadata section.

        Args:
            container: Container layout to add the metadata section to

        """
        group = QGroupBox("Metadata", self)
        layout = QVBoxLayout()
        self.build_confidence_slider(layout)
        self.build_todo_check(layout)
        self.build_modern_english_edit(layout)
        self.build_sense_edit(layout)
        self.build_root_edit(layout)
        group.setLayout(layout)
        container.addWidget(group)

    def build_confidence_slider(self, container: QVBoxLayout) -> None:
        """
        Set up the confidence slider.

        This is where :attr:`confidence_slider` and :attr:`confidence_label` are set up.

        Args:
            container: Container layout to add the confidence slider to

        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Confidence:", self))
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(100)
        self.confidence_label = QLabel("100%", self)
        self.confidence_slider.valueChanged.connect(
            lambda v: self.confidence_label.setText(f"{v}%")
        )
        layout.addWidget(self.confidence_slider)
        layout.addWidget(self.confidence_label)
        container.addLayout(layout)

    def build_todo_check(self, container: QVBoxLayout) -> None:
        """
        Set up the TODO check box.

        Args:
            container: Container layout to add the TODO check box to

        """
        self.todo_check = QCheckBox("TODO (needs review)", self)
        container.addWidget(self.todo_check)

    def build_modern_english_edit(self, container: QVBoxLayout) -> None:
        """
        Set up the root-word definition edit.

        This is where :attr:`modern_english_edit` is set up.

        Args:
            container: Container layout to add the definition edit to

        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Definition of root word:", self))
        self.modern_english_edit = QLineEdit(self)
        self.modern_english_edit.setPlaceholderText("e.g., time, season")
        layout.addWidget(self.modern_english_edit)
        container.addLayout(layout)

    def build_sense_edit(self, container: QVBoxLayout) -> None:
        """
        Set up the contextual sense edit.

        This is where :attr:`sense_edit` is set up.

        Args:
            container: Container layout to add the contextual sense edit to

        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Meaning/Sense in this instance:", self))
        self.sense_edit = QLineEdit(self)
        self.sense_edit.setPlaceholderText("e.g., ruler in this passage")
        layout.addWidget(self.sense_edit)
        container.addLayout(layout)

    def build_root_edit(self, container: QVBoxLayout) -> None:
        """
        Set up the root edit.

        This is where :attr:`root_edit` is set up.

        Args:
            container: Container layout to add the root edit to

        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Root:", self))
        self.root_edit = QLineEdit(self)
        self.root_edit.setPlaceholderText("e.g., bēon, hēof")
        layout.addWidget(self.root_edit)
        container.addLayout(layout)

    def build_action_buttons(self, container: QVBoxLayout) -> None:
        """
        Set up the action buttons.

        This is where :attr:`clear_button`, :attr:`save_as_preset_button`,
        :attr:`cancel_button`, and :attr:`apply_button` are set up.

        Args:
            container: Container layout to add the action buttons to

        """
        layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear All", self)
        self.clear_button.clicked.connect(self._clear_all)
        layout.addWidget(self.clear_button)

        self.save_as_preset_button = QPushButton("Save as Preset", self)
        self.save_as_preset_button.setEnabled(False)
        self.save_as_preset_button.clicked.connect(self._on_save_as_preset)
        layout.addWidget(self.save_as_preset_button)

        layout.addStretch()

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply", self)
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.save)
        layout.addWidget(self.apply_button)

        container.addLayout(layout)

    def _update_status_label(self):
        """
        Update status label with current annotation summary.

        - If the POS is not set, set the status label to "POS: Not set"
        - If the POS is set, add the POS to the summary parts
        - If the gender is set, add the gender to the summary parts
        - If the number is set, add the number to the summary parts
        - Join the summary parts with a comma and space
        - Set the status label to the summary
        """
        pos_text = self.pos_combo.currentText()
        if not pos_text:
            self.status_label.setText("POS: Not set")
            return
        summary_parts = [pos_text]
        values = self.part_of_speech_manager.extract_values()

        # Check for gender
        gender = values.get("gender")
        if gender:
            summary_parts.append(self.GENDER_MAP.get(gender, gender))

        # Check for number (could be 'number' or 'pronoun_number')
        number = values.get("number") or values.get("pronoun_number")
        if number:
            # Try PRONOUN_NUMBER_MAP first as it's more inclusive (has Dual)
            num_text = self.PRONOUN_NUMBER_MAP.get(number) or self.NUMBER_MAP.get(
                number
            )
            if num_text:
                summary_parts.append(num_text)
            else:
                summary_parts.append(number)

        parts = ", ".join(summary_parts)
        self.status_label.setText(f"POS: {parts}")

    # -------------------------------------------------------------------------
    # Annotation related methods
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """
        Load existing annotation values into the form.

        If there is a POS set on the annotation, then:

            - Build the Part of Speech form for the annotation's POS
            - Load the last used values for the POS
            - Load the preset dropdown
            - Load the annotation into the Part of Speech form
            - Load metadata

        Otherwise, set the POS combo to empty/None (index 0), clear
        the Part of Speech form, and clear the metadata.
        """
        if not self.annotation.pos:
            # No annotation exists, ensure POS combo is set to empty/None (index 0)
            # Block signals temporarily to prevent _on_pos_changed from firing
            self.pos_combo.blockSignals(True)  # noqa: FBT003
            self.pos_combo.setCurrentIndex(0)  # Empty selection
            self.pos_combo.blockSignals(False)  # noqa: FBT003
            return

        # Set POS
        # Note: Index 0 is empty string, so POS options start at index 1
        pos_index = 0
        if self.annotation.pos:
            pos_text = self.PART_OF_SPEECH_MAP.get(self.annotation.pos)
            if pos_text:
                pos_index = self.pos_combo.findText(pos_text)

        # Block signals temporarily to prevent double-triggering
        self.pos_combo.blockSignals(True)  # noqa: FBT003
        self.pos_combo.setCurrentIndex(max(0, pos_index))
        self.pos_combo.blockSignals(False)  # noqa: FBT003

        # Trigger field creation
        self._on_pos_changed()

        self.part_of_speech_manager.load_from_annotation(self.annotation)
        # Load metadata
        if self.annotation.confidence is not None:
            self.confidence_slider.setValue(self.annotation.confidence)
        if self.annotation.modern_english_meaning:
            self.modern_english_edit.setText(self.annotation.modern_english_meaning)
        if self.annotation.sense:
            self.sense_edit.setText(self.annotation.sense)
        if self.annotation.root:
            self.root_edit.setText(self.annotation.root)

    def save(self) -> None:
        """
        Save the annotation.

        - Get the current POS
        - If the POS is empty, set the annotation's POS to None
        - Otherwise, get the POS code from the POS combo box
        - Save the current values for future use
        - Update the annotation with the values from the Part of Speech form
        - Extract metadata
        - Save the annotation
        """
        # Get POS
        # Note: Index 0 is empty string, so we need to subtract 1 from the index
        # to map to the correct POS code
        combo_index = self.pos_combo.currentIndex()
        if combo_index == 0:
            # Empty selection
            self.annotation.pos = None
        else:
            self.annotation.pos = self.PART_OF_SPEECH_REVERSE_MAP.get(
                self.pos_combo.currentText()
            )

        # Save current values for future use
        if self.annotation.pos:
            self._last_values[self.annotation.pos] = (
                self.part_of_speech_manager.extract_indices()
            )
        # Update the annotation with the values from the Part of Speech form
        self.part_of_speech_manager.update_annotation(self.annotation)

        # Extract metadata
        self.annotation.confidence = self.confidence_slider.value()
        modern_english_text = self.modern_english_edit.text().strip()
        if modern_english_text:
            self.annotation.modern_english_meaning = modern_english_text
        else:
            self.annotation.modern_english_meaning = None
        sense_text = self.sense_edit.text().strip()
        if sense_text:
            self.annotation.sense = sense_text
        else:
            self.annotation.sense = None
        root_text = self.root_edit.text().strip()
        if root_text:
            self.annotation.root = root_text
        else:
            self.annotation.root = None

        self.annotation_applied.emit(self.annotation)
        self.accept()

    # -------------------------------------------------------------------------
    # Preset dropdown methods
    # -------------------------------------------------------------------------

    def _update_preset_dropdown(self) -> None:
        """
        Signal callback for the ``currentIndexChanged`` signal on the POS combo box.

        Populate preset dropdown based on current POS selection.

        Does the following:

        - If :attr:`preset_combo` or :attr:`apply_preset_button` is not set, do nothing.
        - Get the current POS text from the POS combo box
        - If the POS is not set, disable the preset dropdown and "Apply Preset" button
        - Look up the POS code from the POS display text
        - If the POS code is invalid or unsupported, disable the preset dropdown
          and apply preset button
        - Get the presets for this POS
        - Clear and populate the preset dropdown
        - If there are presets, enable the preset dropdown and apply preset button

        Args:
            None

        Returns:
            None

        """
        # Ensure we have the required widgets
        if not hasattr(self, "preset_combo") or not hasattr(
            self, "apply_preset_button"
        ):
            return

        # Get current POS text from combo box
        current_text = self.pos_combo.currentText()
        if not current_text:
            # No POS selected - disable dropdown
            self.preset_combo.clear()
            self.preset_combo.setEnabled(False)
            self.apply_preset_button.setEnabled(False)
            return

        # Look up POS code from display text
        pos = self.PART_OF_SPEECH_REVERSE_MAP.get(current_text)
        if not pos or pos not in ("N", "V", "A", "R", "D"):
            # Invalid or unsupported POS - disable dropdown
            self.preset_combo.clear()
            self.preset_combo.setEnabled(False)
            self.apply_preset_button.setEnabled(False)
            return

        # Get presets for this POS
        try:
            presets = self.preset_service.get_presets_for_pos(pos)
        except SQLAlchemyError:
            # Error getting presets - disable dropdown
            self.preset_combo.clear()
            self.preset_combo.setEnabled(False)
            self.apply_preset_button.setEnabled(False)
            return

        # Clear and populate dropdown
        self.preset_combo.clear()

        if presets:
            # Add empty option first
            self.preset_combo.addItem("")
            for preset in presets:
                self.preset_combo.addItem(preset.name, preset.id)
            self.preset_combo.setEnabled(True)
            self.apply_preset_button.setEnabled(True)
        else:
            # No presets available - disable dropdown
            self.preset_combo.setEnabled(False)
            self.apply_preset_button.setEnabled(False)

    def _refresh_preset_dropdown(self) -> None:
        """
        Refresh preset dropdown from database.
        """
        self._update_preset_dropdown()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_preset_apply(self) -> None:
        """
        Signal callback for the ``clicked`` signal on the "Apply Preset" button.

        Apply selected preset values to form fields.

        - If the preset is not selected, return
        - Get the preset ID from the preset combo box
        - Get the preset from the database, if not found, return
        - Load the preset values into the Part of Speech form
        - Update the status label based on the new preset
        """
        if self.preset_combo.currentIndex() == 0:
            # Empty selection
            return

        preset_id = self.preset_combo.currentData()
        if not preset_id:
            return

        preset = AnnotationPreset.get(preset_id)
        if not preset:
            return

        self.part_of_speech_manager.load_from_preset(preset)
        self._update_status_label()

    def _on_token_link_clicked(self, token: "Token") -> None:
        """
        Signal callback for the ``clicked`` signal on the "Open Token Modal" button.

        Handle clicking a token link in an idiom modal.

        Args:
            token: Token to open the annotation modal for

        """
        # Close current modal and open a new one for the token
        self.accept()
        parent = cast("QObject", self.parent())
        if hasattr(parent, "_open_token_modal"):
            parent._open_token_modal(token)

    def _select_pos_by_key(self, pos_key: str):
        """
        Signal callback for the keyboard shortcut for the POS key.

        Select POS by keyboard shortcut.  This is an event handler for the
        keyboard shortcuts.

        Args:
            pos_key: POS key (N, V, A, R, D, B, C, E, I)

        """
        pos_text = self.PART_OF_SPEECH_MAP.get(pos_key)  # type: ignore[attr-defined]
        if pos_text:
            index = self.pos_combo.findText(pos_text)
            if index >= 0:
                self.pos_combo.setCurrentIndex(index)
                # _on_pos_changed will be triggered by setCurrentIndex

    def _on_pos_changed(self) -> None:
        """
        Signal callback for the ``currentIndexChanged`` signal on the POS combo box.

        Handle POS selection change.

        - Get the current POS and previous POS
        - If the POS is changing and the previous POS is not None, clear the
          root and modern English edit fields
        - Clear the preset selection
        - Update the Save as Preset button state based on the POS
        - Build the Part of Speech form for the new POS
        - Load the last used values for the new POS
        - Update the status label based on the new POS
        """
        pos = self.PART_OF_SPEECH_REVERSE_MAP.get(self.pos_combo.currentText())

        # Clear preset selection when POS changes
        if hasattr(self, "preset_combo"):
            self.preset_combo.setCurrentIndex(0)
        # Update Save as Preset button state
        self.save_as_preset_button.setEnabled(pos in ("N", "V", "A", "R", "D"))

        # Build the Part of Speech form
        self.part_of_speech_manager.select(pos)
        # Load the last used values for the new POS
        if pos in self._last_values:
            self.part_of_speech_manager.load_from_indices(self._last_values[pos])

        self._update_status_label()
        # Update preset dropdown after POS change
        self._update_preset_dropdown()

    def _on_save_as_preset(self) -> None:
        """
        Signal callback for the ``clicked`` signal on the "Save as Preset" button.

        Open preset management dialog in save mode with current form values
        preloaded.
        """
        # We need these imports here to avoid circular imports
        from oeapp.ui.dialogs.annotation_preset_management import (  # noqa: PLC0415
            AnnotationPresetManagementDialog,
        )
        from oeapp.ui.main_window import MainWindow  # noqa: PLC0415

        pos = self.PART_OF_SPEECH_REVERSE_MAP.get(self.pos_combo.currentText())
        if not pos or pos not in ("N", "V", "A", "R", "D"):
            return

        field_values = self.part_of_speech_manager.extract_values()

        main_window = None
        app = QApplication.instance()
        if app:
            for _widget in QApplication.topLevelWidgets():
                if isinstance(_widget, MainWindow):
                    main_window = _widget
                    break

        if not main_window:
            # If we can't find main_window, try to get it from parent chain
            widget: QObject | None = self.parent()
            while widget:
                if hasattr(widget, "main_window"):
                    main_window = widget.main_window
                    break
                widget = (
                    cast("QObject", widget.parent())
                    if hasattr(widget, "parent")
                    else None
                )

        if not main_window:
            QMessageBox.warning(
                self,
                "Error",
                "Could not find main window. Please try again.",
            )
            return

        try:
            dialog = AnnotationPresetManagementDialog(
                save_mode=True,
                initial_pos=cast("PresetPos", pos),
                initial_field_values=field_values,
            )
            dialog.exec()
            # Refresh preset dropdown after dialog closes
            self._refresh_preset_dropdown()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open preset management dialog: {e}",
            )

    def showEvent(self, event) -> None:  # noqa: N802
        """
        Override showEvent to refresh preset dropdown when dialog is shown.
        """
        super().showEvent(event)
        # Use QTimer.singleShot to ensure the dialog is fully shown and session
        # is available
        QTimer.singleShot(0, self._refresh_preset_dropdown)

    def _clear_all(self) -> None:
        """
        Signal callback for the ``clicked`` signal on the "Clear All" button.

        Clear all fields.

        - Set the POS combo box to index 0 (empty/None selection)
        - Clear the Part of Speech form
        - Clear the metadata fields:

            - Confidence slider to 100
            - Todo check to False
            - Modern English edit to empty string
            - Sense edit to empty string
            - Root edit to empty string
        """
        # Set to index 0 (empty/None selection)
        self.pos_combo.setCurrentIndex(0)
        # Clear the Part of Speech form
        self.part_of_speech_manager.reset()
        # Clear the metadata fields
        self.confidence_slider.setValue(100)
        self.todo_check.setChecked(False)
        self.modern_english_edit.clear()
        self.sense_edit.clear()
        self.root_edit.clear()
