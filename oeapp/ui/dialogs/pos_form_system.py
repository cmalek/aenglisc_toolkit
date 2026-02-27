"""Shared part-of-speech form classes for annotation and preset dialogs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, cast

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLayout,
    QLayoutItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.models import Annotation
from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from collections.abc import Mapping

    from oeapp.models.annotation_preset import AnnotationPreset

# Sentinel value to represent an explicit "Clear" field selection in presets.
CLEAR_SENTINEL = "__CLEAR__"


@dataclass(frozen=True)
class PosFieldSpec:
    """Describe one rendered POS field."""

    attr: str
    label: str
    lookup_map: Mapping[Any, str] | None = None
    editable: bool = False
    object_name: str | None = None
    preset_clear_mode: bool = True


class PartOfSpeechFieldsBase(AnnotationLookupsMixin):
    """Base class for annotation-modal POS field groups."""

    #: The Part of Speech Name
    PART_OF_SPEECH: str

    def __init__(self, layout: QFormLayout, parent_widget: QWidget) -> None:
        self.layout = layout
        self.parent_widget = parent_widget
        self.fields: dict[str, QComboBox] = {}
        self.lookup_map: dict[str, Mapping[Any, str]] = {}
        self.code_to_index_map: dict[str, dict[Any, int]] = {}
        self.index_to_code_map: dict[str, dict[int, Any]] = {}

    def add_combo(
        self,
        attr: str,
        label: str,
        lookup_map: Mapping[Any, str],
    ) -> None:
        """Add a combo box field with lookup/index maps."""
        combo = QComboBox(self.parent_widget)
        combo.addItems(list(lookup_map.values()))
        self.lookup_map[attr] = lookup_map
        self.code_to_index_map[attr] = {k: i for i, k in enumerate(lookup_map.keys())}
        self.index_to_code_map[attr] = {
            i: k for k, i in self.code_to_index_map[attr].items()
        }
        self.add_field(attr, label, combo)

    def clear(self) -> None:
        """Clear cached combo metadata."""
        self.fields.clear()
        self.lookup_map.clear()
        self.code_to_index_map.clear()
        self.index_to_code_map.clear()

    def reset(self) -> None:
        """Reset all combo boxes to index 0."""
        for field in self.fields.values():
            field.setCurrentIndex(0)

    def add_field(self, attr: str, label: str, field: QComboBox) -> None:
        """Register and render a combo field."""
        self.fields[attr] = field
        self.layout.addRow(label, field)

    def build(self) -> None:
        """Build the POS form."""
        msg = "Subclasses must implement this method"
        raise NotImplementedError(msg)

    def load_from_indices(self, indices: dict[str, int]) -> None:
        """Set combo indices from cached values."""
        for attr, index in indices.items():
            if attr in self.fields:
                self.fields[attr].blockSignals(True)  # noqa: FBT003
                self.fields[attr].setCurrentIndex(index)
                self.fields[attr].blockSignals(False)  # noqa: FBT003

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        """Load values from an AnnotationPreset object."""
        for attr, value in preset.to_json().items():
            if attr in self.lookup_map:
                if value == CLEAR_SENTINEL:
                    self.fields[attr].setCurrentIndex(0)
                    continue
                if value is None:
                    continue
                index = self.code_to_index_map[attr].get(value)
                if index is not None:
                    self.fields[attr].blockSignals(True)  # noqa: FBT003
                    self.fields[attr].setCurrentIndex(index)
                    self.fields[attr].blockSignals(False)  # noqa: FBT003

    def load_from_annotation(self, annotation: Annotation) -> None:
        """Load values from an Annotation object."""
        for attr, value in annotation.to_json().items():
            if attr in self.lookup_map:
                index = self.code_to_index_map[attr].get(value)
                if index is not None:
                    self.fields[attr].blockSignals(True)  # noqa: FBT003
                    self.fields[attr].setCurrentIndex(index)
                    self.fields[attr].blockSignals(False)  # noqa: FBT003

    def extract_indices(self) -> dict[str, int]:
        """Extract current combo indices."""
        return {attr: self.fields[attr].currentIndex() for attr in self.fields}

    def extract_values(self) -> dict[str, Any]:
        """Extract current combo code values."""
        return {
            attr: self.index_to_code_map[attr].get(self.fields[attr].currentIndex())
            for attr in self.fields
        }

    def update_annotation(self, annotation: Annotation) -> None:
        """Apply current extracted values onto an annotation model."""
        valid_fields = {column.name for column in Annotation.__table__.columns}
        values = self.extract_values()
        for attr, value in values.items():
            if attr not in valid_fields:
                msg = f"Invalid Annotation attribute: {attr}"
                raise AttributeError(msg)
            setattr(annotation, attr, value)


class NounFields(PartOfSpeechFieldsBase):
    """Fields for noun annotations."""

    PART_OF_SPEECH: str = "Noun"

    def build(self) -> None:
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)
        self.add_combo("declension", "Declension", self.DECLENSION_MAP)


class VerbFields(PartOfSpeechFieldsBase):
    """Fields for verb annotations."""

    PART_OF_SPEECH: str = "Verb"
    VERB_REQUIRES_INF_MAP: ClassVar[dict[bool, str]] = {False: "No", True: "Yes"}
    VERB_IMPERSONAL_MAP: ClassVar[dict[bool, str]] = {False: "No", True: "Yes"}

    def build(self) -> None:
        self.add_combo("verb_class", "Class", self.VERB_CLASS_MAP)
        self.add_combo("verb_tense", "Tense", self.VERB_TENSE_MAP)
        self.add_combo("verb_mood", "Mood", self.VERB_MOOD_MAP)
        self.add_combo("verb_person", "Person", self.VERB_PERSON_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("verb_aspect", "Aspect", self.VERB_ASPECT_MAP)
        self.add_combo(
            "verb_direct_object_case",
            "Direct Object Case",
            self.VERB_DIRECT_OBJECT_CASE_MAP,
        )
        self.add_combo("verb_form", "Form", self.VERB_FORM_MAP)
        self.add_combo(
            "verb_requires_infinitive",
            "Requires Infinitive",
            self.VERB_REQUIRES_INF_MAP,
        )
        self.add_combo("verb_impersonal", "Impersonal", self.VERB_IMPERSONAL_MAP)
        self.add_combo("verb_transitivity", "Transitivity", self.VERB_TRANSITIVITY_MAP)
        self.fields["verb_class"].currentIndexChanged.connect(self._on_class_changed)

    def _on_class_changed(self, _index: int) -> None:
        """Auto-set requires infinitive for preterite-present verbs."""
        verb_class = self.extract_values().get("verb_class")
        if verb_class != "pp":
            return
        requires_inf = self.code_to_index_map["verb_requires_infinitive"].get(True)
        if requires_inf is not None:
            self.fields["verb_requires_infinitive"].setCurrentIndex(requires_inf)


class PronounFields(PartOfSpeechFieldsBase):
    """Fields for pronoun annotations."""

    PART_OF_SPEECH: str = "Pronoun"

    def build(self) -> None:
        self.add_combo("pronoun_type", "Type", self.PRONOUN_TYPE_MAP)
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("pronoun_number", "Number", self.PRONOUN_NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)


class PrepositionFields(PartOfSpeechFieldsBase):
    """Fields for preposition annotations."""

    PART_OF_SPEECH: str = "Preposition"

    def build(self) -> None:
        self.add_combo("prep_case", "Governed Case", self.PREPOSITION_CASE_MAP)


class AdjectiveFields(PartOfSpeechFieldsBase):
    """Fields for adjective annotations."""

    PART_OF_SPEECH: str = "Adjective"

    def build(self) -> None:
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
    """Fields for article annotations."""

    PART_OF_SPEECH: str = "Article"

    def build(self) -> None:
        self.add_combo("article_type", "Type", self.ARTICLE_TYPE_MAP)
        self.add_combo("gender", "Gender", self.GENDER_MAP)
        self.add_combo("number", "Number", self.NUMBER_MAP)
        self.add_combo("case", "Case", self.CASE_MAP)


class AdverbFields(PartOfSpeechFieldsBase):
    """Fields for adverb annotations."""

    PART_OF_SPEECH: str = "Adverb"

    def build(self) -> None:
        self.add_combo("adverb_degree", "Degree", self.ADVERB_DEGREE_MAP)


class ConjunctionFields(PartOfSpeechFieldsBase):
    """Fields for conjunction annotations."""

    PART_OF_SPEECH: str = "Conjunction"

    def build(self) -> None:
        self.add_combo("conjunction_type", "Type", self.CONJUNCTION_TYPE_MAP)


class InterjectionFields(PartOfSpeechFieldsBase):
    """Fields for interjection annotations."""

    PART_OF_SPEECH: str = "Interjection"

    def build(self) -> None:
        return


class NumberFields(PartOfSpeechFieldsBase):
    """Fields for number annotations."""

    PART_OF_SPEECH: str = "Number"

    def build(self) -> None:
        return


class NoneFields(PartOfSpeechFieldsBase):
    """Fields for empty POS state."""

    PART_OF_SPEECH: str = "N/A"

    def build(self) -> None:
        return


class AnnotationPosFormManager:
    """Manager for annotation-modal POS forms."""

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
        self.container_layout = container_layout
        self.parent_widget = parent_widget
        self.current: PartOfSpeechFieldsBase | None = None
        self.select(None)

    def select(self, pos: str | None) -> None:
        """Select and render POS-specific fields."""
        if pos not in self.PARTS_OF_SPEECH:
            msg = f"Invalid Part of Speech: {pos}"
            raise ValueError(msg)

        while self.container_layout.count():
            item = cast("QLayoutItem", self.container_layout.takeAt(0))
            if item.widget():
                widget = cast("QWidget", item.widget())
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        new_layout = QFormLayout()
        self.container_layout.addLayout(new_layout)

        self.current = self.PARTS_OF_SPEECH[pos](new_layout, self.parent_widget)
        self.current.build()

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = cast("QLayoutItem", layout.takeAt(0))
            if item.widget():
                widget = cast("QWidget", item.widget())
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def reset(self) -> None:
        if self.current:
            self.current.reset()

    def load_from_indices(self, indices: dict[str, int]) -> None:
        if self.current:
            self.current.load_from_indices(indices)

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        if self.current:
            self.current.load_from_preset(preset)

    def load_from_annotation(self, annotation: Annotation) -> None:
        assert self.current is not None, (  # noqa: S101
            "load_from_annotation called without a selected Part of Speech"
        )
        self.current.load_from_annotation(annotation)

    def extract_indices(self) -> dict[str, int]:
        if self.current:
            return self.current.extract_indices()
        return {}

    def extract_values(self) -> dict[str, str | bool | None]:
        assert self.current is not None, (  # noqa: S101
            "extract_values called without a selected Part of Speech"
        )
        return self.current.extract_values()

    def update_annotation(self, annotation: Annotation) -> None:
        assert self.current is not None, (  # noqa: S101
            "update_annotation called without a selected Part of Speech"
        )
        self.current.update_annotation(annotation)


class PresetPartOfSpeechFieldsBase(AnnotationLookupsMixin):
    """Base class for preset-dialog POS field groups."""

    PART_OF_SPEECH: str = ""
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = ()
    PRESET_VERB_BOOLEAN_MAP: ClassVar[dict[bool | None, str]] = {
        None: "",
        False: "No",
        True: "Yes",
    }
    PRESET_VERB_TRANSITIVITY_MAP: ClassVar[dict[str | None, str]] = {
        None: "",
        "transitive": "Transitive",
        "intransitive": "Intransitive",
    }

    def __init__(self, layout: QFormLayout, parent_widget: QWidget) -> None:
        self.layout = layout
        self.parent_widget = parent_widget
        self.fields: dict[str, QComboBox] = {}
        self._specs_by_attr: dict[str, PosFieldSpec] = {}
        self.code_to_index_map: dict[str, dict[Any, int]] = {}
        self.index_to_code_map: dict[str, dict[int, Any]] = {}

    def build(self) -> None:
        """Build all configured preset fields."""
        for spec in self.FIELD_SPECS:
            self._specs_by_attr[spec.attr] = spec
            self._add_field(spec)

    def _add_field(self, spec: PosFieldSpec) -> None:
        combo = QComboBox(self.parent_widget)
        if spec.object_name:
            combo.setObjectName(spec.object_name)

        if spec.editable:
            combo.setEditable(True)
            values = list(spec.lookup_map.values()) if spec.lookup_map else [""]
            combo.addItems([str(value) for value in values])
        else:
            combo.addItem("")
            if spec.preset_clear_mode:
                combo.addItem("Clear")
                offset = 2
            else:
                offset = 1

            if not spec.lookup_map:
                msg = f"Field '{spec.attr}' is missing lookup_map"
                raise ValueError(msg)

            codes = list(spec.lookup_map.keys())
            values = list(spec.lookup_map.values())
            if values and values[0] == "":
                codes = codes[1:]
                values = values[1:]

            combo.addItems([str(value) for value in values])
            self.code_to_index_map[spec.attr] = {
                code: index for index, code in enumerate(codes, start=offset)
            }
            self.index_to_code_map[spec.attr] = {
                index: code for code, index in self.code_to_index_map[spec.attr].items()
            }

        self.fields[spec.attr] = combo
        self.layout.addRow(spec.label, combo)

    def reset(self) -> None:
        """Reset rendered preset combos to empty."""
        for combo in self.fields.values():
            combo.setCurrentIndex(0)

    def bind_dialog_attributes(self, dialog: object) -> None:
        """Bind object-name combos as attributes on the dialog for compatibility."""
        for spec in self.FIELD_SPECS:
            if spec.object_name and spec.attr in self.fields:
                setattr(dialog, spec.object_name, self.fields[spec.attr])

    def load_from_values(self, field_values: Mapping[str, str | bool | None]) -> None:
        """Load preset field values into rendered widgets."""
        for attr, value in field_values.items():
            spec = self._specs_by_attr.get(attr)
            combo = self.fields.get(attr)
            if not spec or not combo:
                continue

            if spec.editable:
                combo.setCurrentText(str(value) if value else "")
                continue

            if value is None:
                combo.setCurrentIndex(0)
                continue

            if spec.preset_clear_mode and value == CLEAR_SENTINEL:
                combo.setCurrentIndex(1)
                continue

            combo.setCurrentIndex(self.code_to_index_map[attr].get(value, 0))

    def extract_values(self) -> dict[str, str | bool | None]:
        """Extract preset values with empty/clear semantics."""
        extracted: dict[str, str | bool | None] = {}
        for attr, spec in self._specs_by_attr.items():
            combo = self.fields[attr]
            if spec.editable:
                text = combo.currentText().strip()
                extracted[attr] = text or None
                continue

            index = combo.currentIndex()
            if index == 0:
                extracted[attr] = None
                continue
            if spec.preset_clear_mode and index == 1:
                extracted[attr] = CLEAR_SENTINEL
                continue
            extracted[attr] = self.index_to_code_map[attr].get(index)

        return extracted


class PresetNounFields(PresetPartOfSpeechFieldsBase):
    """Preset fields for noun POS."""

    PART_OF_SPEECH = "N"
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = (
        PosFieldSpec(
            "gender",
            "Gender:",
            PresetPartOfSpeechFieldsBase.GENDER_MAP,
            object_name="gender_combo",
        ),
        PosFieldSpec(
            "number",
            "Number:",
            PresetPartOfSpeechFieldsBase.NUMBER_MAP,
            object_name="number_combo",
        ),
        PosFieldSpec(
            "case",
            "Case:",
            PresetPartOfSpeechFieldsBase.CASE_MAP,
            object_name="case_combo",
        ),
        PosFieldSpec(
            "declension",
            "Declension:",
            PresetPartOfSpeechFieldsBase.DECLENSION_MAP,
            editable=True,
            object_name="declension_combo",
            preset_clear_mode=False,
        ),
    )


class PresetVerbFields(PresetPartOfSpeechFieldsBase):
    """Preset fields for verb POS."""

    PART_OF_SPEECH = "V"
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = (
        PosFieldSpec(
            "verb_class",
            "Class:",
            PresetPartOfSpeechFieldsBase.VERB_CLASS_MAP,
            editable=True,
            object_name="verb_class_combo",
            preset_clear_mode=False,
        ),
        PosFieldSpec(
            "verb_tense",
            "Tense:",
            PresetPartOfSpeechFieldsBase.VERB_TENSE_MAP,
            object_name="verb_tense_combo",
        ),
        PosFieldSpec(
            "verb_mood",
            "Mood:",
            PresetPartOfSpeechFieldsBase.VERB_MOOD_MAP,
            object_name="verb_mood_combo",
        ),
        PosFieldSpec(
            "verb_person",
            "Person:",
            PresetPartOfSpeechFieldsBase.VERB_PERSON_MAP,
            object_name="verb_person_combo",
        ),
        PosFieldSpec(
            "number",
            "Number:",
            PresetPartOfSpeechFieldsBase.NUMBER_MAP,
            object_name="verb_number_combo",
        ),
        PosFieldSpec(
            "verb_aspect",
            "Aspect:",
            PresetPartOfSpeechFieldsBase.VERB_ASPECT_MAP,
            object_name="verb_aspect_combo",
        ),
        PosFieldSpec(
            "verb_form",
            "Form:",
            PresetPartOfSpeechFieldsBase.VERB_FORM_MAP,
            object_name="verb_form_combo",
        ),
        PosFieldSpec(
            "verb_direct_object_case",
            "Direct Object Case:",
            PresetPartOfSpeechFieldsBase.VERB_DIRECT_OBJECT_CASE_MAP,
            object_name="verb_direct_object_case_combo",
        ),
        PosFieldSpec(
            "verb_requires_infinitive",
            "Requires Infinitive:",
            PresetPartOfSpeechFieldsBase.PRESET_VERB_BOOLEAN_MAP,
            object_name="verb_requires_infinitive_combo",
        ),
        PosFieldSpec(
            "verb_impersonal",
            "Impersonal:",
            PresetPartOfSpeechFieldsBase.PRESET_VERB_BOOLEAN_MAP,
            object_name="verb_impersonal_combo",
        ),
        PosFieldSpec(
            "verb_transitivity",
            "Transitivity:",
            PresetPartOfSpeechFieldsBase.PRESET_VERB_TRANSITIVITY_MAP,
            object_name="verb_transitivity_combo",
        ),
    )


class PresetAdjectiveFields(PresetPartOfSpeechFieldsBase):
    """Preset fields for adjective POS."""

    PART_OF_SPEECH = "A"
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = (
        PosFieldSpec(
            "adjective_degree",
            "Degree:",
            PresetPartOfSpeechFieldsBase.ADJECTIVE_DEGREE_MAP,
            object_name="adj_degree_combo",
        ),
        PosFieldSpec(
            "adjective_inflection",
            "Inflection:",
            PresetPartOfSpeechFieldsBase.ADJECTIVE_INFLECTION_MAP,
            object_name="adj_inflection_combo",
        ),
        PosFieldSpec(
            "gender",
            "Gender:",
            PresetPartOfSpeechFieldsBase.GENDER_MAP,
            object_name="adj_gender_combo",
        ),
        PosFieldSpec(
            "number",
            "Number:",
            PresetPartOfSpeechFieldsBase.NUMBER_MAP,
            object_name="adj_number_combo",
        ),
        PosFieldSpec(
            "case",
            "Case:",
            PresetPartOfSpeechFieldsBase.CASE_MAP,
            object_name="adj_case_combo",
        ),
    )


class PresetPronounFields(PresetPartOfSpeechFieldsBase):
    """Preset fields for pronoun POS."""

    PART_OF_SPEECH = "R"
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = (
        PosFieldSpec(
            "pronoun_type",
            "Type:",
            PresetPartOfSpeechFieldsBase.PRONOUN_TYPE_MAP,
            object_name="pro_type_combo",
        ),
        PosFieldSpec(
            "gender",
            "Gender:",
            PresetPartOfSpeechFieldsBase.GENDER_MAP,
            object_name="pro_gender_combo",
        ),
        PosFieldSpec(
            "pronoun_number",
            "Number:",
            PresetPartOfSpeechFieldsBase.PRONOUN_NUMBER_MAP,
            object_name="pro_number_combo",
        ),
        PosFieldSpec(
            "case",
            "Case:",
            PresetPartOfSpeechFieldsBase.CASE_MAP,
            object_name="pro_case_combo",
        ),
    )


class PresetArticleFields(PresetPartOfSpeechFieldsBase):
    """Preset fields for article POS."""

    PART_OF_SPEECH = "D"
    FIELD_SPECS: ClassVar[tuple[PosFieldSpec, ...]] = (
        PosFieldSpec(
            "article_type",
            "Type:",
            PresetPartOfSpeechFieldsBase.ARTICLE_TYPE_MAP,
            object_name="article_type_combo",
        ),
        PosFieldSpec(
            "gender",
            "Gender:",
            PresetPartOfSpeechFieldsBase.GENDER_MAP,
            object_name="article_gender_combo",
        ),
        PosFieldSpec(
            "number",
            "Number:",
            PresetPartOfSpeechFieldsBase.NUMBER_MAP,
            object_name="article_number_combo",
        ),
        PosFieldSpec(
            "case",
            "Case:",
            PresetPartOfSpeechFieldsBase.CASE_MAP,
            object_name="article_case_combo",
        ),
    )


class PresetPosFormManager:
    """Manager for preset-dialog POS forms."""

    POS_FIELD_CLASSES: ClassVar[dict[str, type[PresetPartOfSpeechFieldsBase]]] = {
        "N": PresetNounFields,
        "V": PresetVerbFields,
        "A": PresetAdjectiveFields,
        "R": PresetPronounFields,
        "D": PresetArticleFields,
    }

    def __init__(
        self,
        pos: str,
        form_layout: QFormLayout,
        parent_widget: QWidget,
    ) -> None:
        if pos not in self.POS_FIELD_CLASSES:
            msg = f"Unsupported preset Part of Speech: {pos}"
            raise ValueError(msg)
        self.pos = pos
        self.form_layout = form_layout
        self.parent_widget = parent_widget
        self.current = self.POS_FIELD_CLASSES[pos](form_layout, parent_widget)
        self.current.build()

    def reset(self) -> None:
        """Reset rendered fields."""
        self.current.reset()

    def bind_dialog_attributes(self, dialog: object) -> None:
        """Expose combo attributes on the dialog for compatibility."""
        self.current.bind_dialog_attributes(dialog)

    def load_from_values(self, field_values: Mapping[str, str | bool | None]) -> None:
        """Load values into managed fields."""
        self.current.load_from_values(field_values)

    def extract_values(self) -> dict[str, str | bool | None]:
        """Extract values from managed fields."""
        return self.current.extract_values()
