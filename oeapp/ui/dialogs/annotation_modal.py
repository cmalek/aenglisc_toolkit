"""Annotation modal dialog."""

from typing import TYPE_CHECKING, ClassVar, Final, cast

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
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
from oeapp.ui.dialogs.annotation_preset_management import (
    CLEAR_SENTINEL,
    AnnotationPresetManagementDialog,
)
from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.models.token import Token
    from oeapp.types import PresetPos


class PartOfSpeechFieldsBase(AnnotationLookupsMixin):
    """
    The base class for the Part of Speech set of fields.

    This must be subclassed to provide the fields for the particular Part of
    Speech.

    Args:
        parent: The parent widget

    """

    #: The Part of Speech Name
    PART_OF_SPEECH: str

    def __init__(self, layout: QFormLayout, parent_widget: QWidget) -> None:
        """
        Initialize the Part of Speech form.
        """
        #: The layout to add the fields to
        self.layout = layout
        #: The parent widget for the fields
        self.parent_widget = parent_widget
        #: The fields for the Part of Speech form
        self.fields: dict[str, QComboBox] = {}
        #: The lookup map for the fields
        self.lookup_map: dict[str, dict[str | None, str]] = {}
        #: The code to combo index map for the fields
        self.code_to_index_map: dict[str, dict[str | None, int]] = {}
        #: The index to code map for the fields
        self.index_to_code_map: dict[str, dict[int, str | None]] = {}

    def add_combo(
        self,
        attr: str,
        label: str,
        lookup_map: dict[str | None, str],
    ) -> None:
        """
        Add a combo box to the Part of Speech form.

        Args:
            attr: The attribute name for the field
            label: The label for the combo box
            lookup_map: The lookup map for the combo box.  This should be one of
                the lookup maps from
                :class:`~oeapp.ui.mixins.AnnotationLookupsMixin`. like
                :attr:`~oeapp.ui.mixins.AnnotationLookupsMixin.ARTICLE_TYPE_MAP`.

        """
        combo = QComboBox(self.parent_widget)
        combo.addItems(list(lookup_map.values()))
        self.lookup_map[attr] = lookup_map
        self.code_to_index_map[attr] = {k: i for i, k in enumerate(lookup_map.keys())}
        self.index_to_code_map[attr] = {
            i: k for k, i in self.code_to_index_map[attr].items()
        }
        self.add_field(attr, label, combo)

    def clear(self) -> None:
        """
        Reset the Part of Speech form.

        - Clears the fields dictionary
        - Clears the lookup map
        - Clears the code to index map
        - Clears the index to code map
        """
        self.fields.clear()
        self.lookup_map.clear()
        self.code_to_index_map.clear()
        self.index_to_code_map.clear()

    def reset(self) -> None:
        """
        Reset the fields to their default values, meaning index 0 (empty selection).
        """
        for field in self.fields.values():
            field.setCurrentIndex(0)

    def add_field(self, attr: str, label: str, field: QComboBox) -> None:
        """
        Add a field to the Part of Speech form.

        Side effect:
            The field will be added to the fields dictionary and to the
            :class:`~PySide6.QtWidgets.QFormLayout` as a row.

        Args:
            attr: The attribute name for the field on :class:`~oeapp.models.Annotation`
            label: The label for the field
            field: The field to add

        """
        self.fields[attr] = field
        self.layout.addRow(label, field)

    def build(self) -> None:
        """
        Build the Part of Speech form.
        """
        msg = "Subclasses must implement this method"
        raise NotImplementedError(msg)

    def load_from_indices(self, indices: dict[str, int]) -> None:
        """
        Load the values from the indices into the Part of Speech form.

        Side effect:
            For each attribute in the indices, if the attribute is in the lookup
            map, the field will be set to the value.  If the index is not in the
            lookup map, that index is ignored.

        Args:
            indices: The indices to load the values from


        """
        for attr, index in indices.items():
            if attr in self.fields:
                self.fields[attr].blockSignals(True)  # noqa: FBT003
                self.fields[attr].setCurrentIndex(index)
                self.fields[attr].blockSignals(False)  # noqa: FBT003

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        """
        Load the values from the preset into the Part of Speech form.

        Side effect:
            For each attribute in the preset, if the attribute is in the lookup
            map, the field will be set to the value.  If the value is
            :data:`~oeapp.ui.dialogs.annotation_preset_management.CLEAR_SENTINEL`,
            the field will be set to empty selection (index 0).
            If the value is None, the field will be left unchanged.

            If the preset has a value that is not in the lookup map,
            the field will be set to empty selection (index 0).


        Args:
            preset: The preset to load the values from

        """
        for attr, value in preset.to_json().items():
            if attr in self.lookup_map:
                if value == CLEAR_SENTINEL:
                    # "Clear" was selected - set to empty selection (index 0)
                    self.fields[attr].setCurrentIndex(0)
                    continue
                if value is None:
                    # Empty was selected - don't change this field, skip it
                    continue
                # Actually set the value
                index = self.code_to_index_map[attr].get(value)
                if index is not None:
                    self.fields[attr].blockSignals(True)  # noqa: FBT003
                    self.fields[attr].setCurrentIndex(index)
                    self.fields[attr].blockSignals(False)  # noqa: FBT003

    def load_from_annotation(self, annotation: Annotation) -> None:
        """
        Load the annotation into the Part of Speech form.

        Side effect:
            For each attribute in the annotation, if the attribute is in the lookup map,
            the field will be set to the value.

            If the annotation has a value that is not in the lookup map,
            the field will be set to empty selection (index 0).

        Args:
            annotation: The annotation to load the values from

        """
        for attr, value in annotation.to_json().items():
            if attr in self.lookup_map:
                index = self.code_to_index_map[attr].get(value)
                if index is not None:
                    self.fields[attr].blockSignals(True)  # noqa: FBT003
                    self.fields[attr].setCurrentIndex(index)
                    self.fields[attr].blockSignals(False)  # noqa: FBT003

    def extract_indices(self) -> dict[str, int]:
        """
        Extract the indices from the Part of Speech form into a dict
        where the keys are the attribute names and the values are the indices.

        Returns:
            A dictionary of the indices from the Part of Speech form

        """
        return {attr: self.fields[attr].currentIndex() for attr in self.fields}

    def extract_values(self) -> dict[str, str | None]:
        """
        Extract the values from the form and return them as a dictionary where
        the keys are the attribute names and the values are the values from the
        combo box (the codes).  If the field is empty, the value will be None.

        Returns:
            A dictionary of the values from the Part of Speech form

        """
        return {
            attr: self.index_to_code_map[attr].get(self.fields[attr].currentIndex())
            for attr in self.fields
        }

    def update_annotation(self, annotation: Annotation) -> None:
        """
        Extract the values from the form and save them to the annotation.

        Args:
            annotation: The annotation to save the values to

        Keyword Args:
            commit: Whether to commit the changes to the database

        Raises:
            AttributeError: If the attribute we we think is associated with an
                combo box is not a valid Annotation attribute

        """
        valid_fields = {column.name for column in Annotation.__table__.columns}
        values = self.extract_values()
        for attr, value in values.items():
            if attr not in valid_fields:
                msg = f"Invalid Annotation attribute: {attr}"
                raise AttributeError(msg)
            setattr(annotation, attr, value)


class NounFields(PartOfSpeechFieldsBase):
    """
    The fields for the Noun form.
    """

    PART_OF_SPEECH: str = "Noun"

    def build(self) -> None:
        """
        Build the Noun form.

        - Adds the gender combo box
        - Adds the number combo box
        - Adds the case combo box
        - Adds the declension combo box
        """
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)
        self.add_combo("declension", "Declension", self.DECLENSION_MAP)


class VerbFields(PartOfSpeechFieldsBase):
    """
    The fields for the Verb form.
    """

    PART_OF_SPEECH: str = "Verb"

    def build(self) -> None:
        """
        Build the Verb form.

        - Adds the verb class combo box
        - Adds the verb tense combo box
        - Adds the verb mood combo box
        - Adds the verb person combo box
        - Adds the verb number combo box
        - Adds the verb aspect combo box
        - Adds the verb form combo box
        """
        self.add_combo("verb_class", "Class", self.VERB_CLASS_MAP)
        self.add_combo("verb_tense", "Tense", self.VERB_TENSE_MAP)
        self.add_combo("verb_mood", "Mood", self.VERB_MOOD_MAP)
        self.add_combo("verb_person", "Person", self.VERB_PERSON_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("verb_aspect", "Aspect", self.VERB_ASPECT_MAP)
        self.add_combo("verb_form", "Form", self.VERB_FORM_MAP)


class PronounFields(PartOfSpeechFieldsBase):
    """
    The fields for the Pronoun form.
    """

    PART_OF_SPEECH: str = "Pronoun"

    def build(self) -> None:
        """
        Build the Pronoun form.

        - Adds the pronoun type combo box
        - Adds the pronoun gender combo box
        - Adds the pronoun number combo box
        - Adds the pronoun case combo box
        """
        self.add_combo("pronoun_type", "Type", self.PRONOUN_TYPE_MAP)
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("pronoun_number", "Number", self.PRONOUN_NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)


class PrepositionFields(PartOfSpeechFieldsBase):
    """
    The fields for the Preposition form.
    """

    PART_OF_SPEECH: str = "Preposition"

    def build(self) -> None:
        """
        Build the Preposition form.

        - Adds the preposition case combo box
        """
        self.add_combo("prep_case", "Governed Case", self.PREPOSITION_CASE_MAP)


class AdjectiveFields(PartOfSpeechFieldsBase):
    """
    The fields for the Adjective form.
    """

    PART_OF_SPEECH: str = "Adjective"

    def build(self) -> None:
        """
        Build the Adjective form.

        - Adds the adjective degree combo box
        - Adds the adjective inflection combo box
        """
        self.add_combo("adjective_degree", "Degree", self.ADJECTIVE_DEGREE_MAP)
        self.add_combo(
            "adjective_inflection",
            "Inflection",
            self.ADJECTIVE_INFLECTION_MAP,
        )
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)


class ArticleFields(PartOfSpeechFieldsBase):
    """
    The fields for the Article form.
    """

    PART_OF_SPEECH: str = "Article"

    def build(self) -> None:
        """
        Build the Article form.
        """
        self.add_combo("article_type", "Type", self.ARTICLE_TYPE_MAP)
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)


class AdverbFields(PartOfSpeechFieldsBase):
    """
    The fields for the Adverb form.
    """

    PART_OF_SPEECH: str = "Adverb"

    def build(self) -> None:
        """
        Build the Adverb form.

        - Adds the adverb degree combo box
        """
        self.add_combo("adverb_degree", "Degree", self.ADVERB_DEGREE_MAP)


class ConjunctionFields(PartOfSpeechFieldsBase):
    """
    The fields for the Conjunction form.
    """

    PART_OF_SPEECH: str = "Conjunction"

    def build(self) -> None:
        """
        Build the Conjunction form.
        """
        self.add_combo("conjunction_type", "Type", self.CONJUNCTION_TYPE_MAP)


class InterjectionFields(PartOfSpeechFieldsBase):
    """
    The fields for the Interjection form.  There are no fields for Interjection.
    """

    PART_OF_SPEECH: str = "Interjection"

    def build(self) -> None:
        """
        Build the Interjection form.
        """


class NumberFields(PartOfSpeechFieldsBase):
    """
    The fields for the Number form.  There are no fields for Number.
    """

    PART_OF_SPEECH: str = "Number"

    def build(self) -> None:
        """
        Build the Number form.
        """


class NoneFields(PartOfSpeechFieldsBase):
    """
    The fields for the None form.  There are no fields for None.
    """

    PART_OF_SPEECH: str = "N/A"

    def build(self) -> None:
        """
        Build the None form.
        """


class PartOfSpeechFormManager:
    """
    Manager for the Part of Speech form."""

    #: Mapping of Part of Speech codes to the corresponding
    #: :class:`PartOfSpeechFieldsBase` subclass.
    PARTS_OF_SPEECH: ClassVar[dict[str | None, type[PartOfSpeechFieldsBase]]] = {
        "N": NounFields,
        "V": VerbFields,
        "A": AdjectiveFields,
        "D": ArticleFields,
        "R": PronounFields,
        "E": PrepositionFields,
        "B": AdverbFields,
        "C": ConjunctionFields,
        "I": InterjectionFields,
        "L": NumberFields,
        None: NoneFields,
    }

    def __init__(self, container_layout: QVBoxLayout, parent_widget: QWidget) -> None:
        """
        Initialize the Part of Speech form manager.

        Args:
            container_layout: The layout to add the Part of Speech widgets to
            parent_widget: The widget that will be the parent of the container
                widgets created for each Part of Speech.

        """
        #: The layout to add the Part of Speech widgets to
        self.container_layout = container_layout
        #: The widget that will be the parent of the container widgets created
        #: for each Part of Speech.
        self.parent_widget = parent_widget
        #: The current Part of Speech fields
        self.current: PartOfSpeechFieldsBase | None = None

        # Start with NoneFields
        self.select(None)

    def select(self, pos: str | None) -> None:
        """
        Set the current Part of Speech fields.

        Args:
            pos: The Part of Speech code to set the fields for, like "N", "V",
                "A", "R", "D", "E", "B", "C", "I"

        Raises:
            ValueError: If the Part of Speech is invalid

        """
        if pos not in self.PARTS_OF_SPEECH:
            msg = f"Invalid Part of Speech: {pos}"
            raise ValueError(msg)

        # 1. Clean up old items from the container layout
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                widget = cast("QWidget", item.widget())
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                # Recursively clear sub-layouts
                self._clear_layout(item.layout())

        # 2. Create new form layout and add it to container
        new_layout = QFormLayout()
        self.container_layout.addLayout(new_layout)

        # 3. Create the fields instance with the NEW layout
        self.current = self.PARTS_OF_SPEECH[pos](new_layout, self.parent_widget)
        self.current.build()

    def _clear_layout(self, layout: QLayout) -> None:
        """
        Helper to clear a layout and its sub-layouts/widgets.

        This is a recursive function that iterates recursively through the
        layout and hides and deletes all widgets.

        Args:
            layout: The layout to clear

        """
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = cast("QWidget", item.widget())
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def reset(self) -> None:
        """
        Reset the Part of Speech form.
        """
        if self.current:
            self.current.reset()

    def load_from_indices(self, indices: dict[str, int]) -> None:
        """
        Load the values from the indices into the Part of Speech form.

        If there is no current Part of Speech fields, do nothing.

        Args:
            indices: A dictionary of the attribute names and the indices to load
                the values from.  The keys are the attribute names and the values
                are the indices to set the fields to.

        """
        if self.current:
            self.current.load_from_indices(indices)

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        """
        Load the values from the preset into the Part of Speech form.
        """
        if self.current:
            self.current.load_from_preset(preset)

    def load_from_annotation(self, annotation: Annotation) -> None:
        """
        Load the annotation into the Part of Speech form.

        Args:
            annotation: The annotation to load the values from

        Raises:
            AssertionError: If the current Part of Speech fields are not set

        """
        assert self.current is not None, (  # noqa: S101
            "load_from_annotation called without a selected Part of Speech"
        )
        if self.current:
            self.current.load_from_annotation(annotation)

    def extract_indices(self) -> dict[str, int]:
        """
        Extract the indices from the Part of Speech form.
        """
        if self.current:
            return self.current.extract_indices()
        return {}

    def extract_values(self) -> dict[str, str | None]:
        """
        Extract the values from the Part of Speech form.

        Returns:
            A dictionary of the values from the Part of Speech form

        Raises:
            AssertionError: If the current Part of Speech fields are not set

        """
        assert self.current is not None, (  # noqa: S101
            "extract_values called without a selected Part of Speech"
        )
        return self.current.extract_values()

    def update_annotation(self, annotation: Annotation) -> None:
        """
        Update the annotation with the values from the Part of Speech form.

        Args:
            annotation: The annotation to update

        Raises:
            AssertionError: If the current Part of Speech fields are not set

        """
        assert self.current is not None, (  # noqa: S101
            "update_annotation called without a selected Part of Speech"
        )
        self.current.update_annotation(annotation)


class AnnotationModal(AnnotationLookupsMixin, QDialog):
    """Modal dialog for annotating tokens with prompt-based entry."""

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
        token: Token | None = None,
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
        parent = self.parent()
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
        Set up the modern English edit.

        This is where :attr:`modern_english_edit` is set up.

        Args:
            container: Container layout to add the modern English edit to

        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Modern English Meaning:", self))
        self.modern_english_edit = QLineEdit(self)
        self.modern_english_edit.setPlaceholderText("e.g., time, season")
        layout.addWidget(self.modern_english_edit)
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
        """Populate preset dropdown based on current POS selection."""
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
        """Refresh preset dropdown from database."""
        self._update_preset_dropdown()

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def _on_preset_apply(self) -> None:
        """
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

    def _on_token_link_clicked(self, token: Token) -> None:
        """
        Handle clicking a token link in an idiom modal.

        Args:
            token: Token to open the annotation modal for

        """
        # Close current modal and open a new one for the token
        self.accept()
        parent = self.parent()
        if hasattr(parent, "_open_token_modal"):
            parent._open_token_modal(token)

    def _select_pos_by_key(self, pos_key: str):
        """
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
        prev_pos = self.annotation.pos

        # If switching between actual POS types (not from/to empty),
        # clear the lexical fields to prevent cross-token corruption
        if pos and prev_pos and pos != prev_pos:
            self.root_edit.clear()
            self.modern_english_edit.clear()

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
        Open preset management dialog in save mode with current form values
        preloaded.
        """
        # We need this here to avoid circular import
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
        Clear all fields.

        - Set the POS combo box to index 0 (empty/None selection)
        - Clear the Part of Speech form
        - Clear the metadata fields:

            - Confidence slider to 100
            - Todo check to False
            - Modern English edit to empty string
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
        self.root_edit.clear()
