"""Shared part-of-speech form classes for annotation and preset dialogs."""

from __future__ import annotations

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
from oeapp.ui.pos_field_catalog import PosField, PosFieldCatalog

if TYPE_CHECKING:
    from collections.abc import Mapping

    from oeapp.models.annotation_preset import AnnotationPreset

#: Sentinel value to represent an explicit "Clear" field selection in presets.
CLEAR_SENTINEL = "__CLEAR__"


class PartOfSpeechFieldsBase(AnnotationLookupsMixin):
    """
    Base class for annotation-modal POS field groups.

    Args:
        layout: Layout.
        parent_widget: Parent widget.

    """

    #: The Part of Speech Name
    PART_OF_SPEECH: str
    #: One-letter POS code used to look fields up in the POS field catalog.
    POS_CODE: str | None = None

    def __init__(self, layout: QFormLayout, parent_widget: QWidget) -> None:
        """
        Initialize the instance.

        Args:
            layout: Layout.
            parent_widget: Parent widget.

        """
        #: Layout.
        self.layout = layout
        #: Parent widget.
        self.parent_widget = parent_widget
        #: Fields.
        self.fields: dict[str, QComboBox] = {}
        #: Lookup map.
        self.lookup_map: dict[str, Mapping[Any, str]] = {}
        #: Code to index map.
        self.code_to_index_map: dict[str, dict[Any, int]] = {}
        #: Index to code map.
        self.index_to_code_map: dict[str, dict[int, Any]] = {}

    def add_combo(
        self,
        attr: str,
        label: str,
        lookup_map: Mapping[Any, str],
    ) -> None:
        """
        Add a combo box field with lookup/index maps.

        Args:
            attr: Attr.
            label: Label.
            lookup_map: Lookup map.

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
        """
        Register and render a combo field.

        Args:
            attr: Attr.
            label: Label.
            field: Field.

        """
        self.fields[attr] = field
        self.layout.addRow(label, field)

    def build(self) -> None:
        """Build one combo per field in the POS field catalog."""
        for field in PosFieldCatalog.fields(self.POS_CODE):
            self.add_combo(field.attr, field.label, field.lookup_map)

    def load_from_indices(self, indices: dict[str, int]) -> None:
        """
        Set combo indices from cached values.

        Args:
            indices: Indices.

        """
        for attr, index in indices.items():
            if attr in self.fields:
                self.fields[attr].blockSignals(True)  # noqa: FBT003
                self.fields[attr].setCurrentIndex(index)
                self.fields[attr].blockSignals(False)  # noqa: FBT003

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        """
        Load values from an AnnotationPreset object.

        Args:
            preset: Preset.

        """
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
        """
        Load values from an Annotation object.

        Args:
            annotation: Annotation.

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
        Extract current combo indices.

        Returns:
            The computed value.

        """
        return {attr: self.fields[attr].currentIndex() for attr in self.fields}

    def extract_values(self) -> dict[str, Any]:
        """
        Extract current combo code values.

        Returns:
            The computed value.

        """
        return {
            attr: self.index_to_code_map[attr].get(self.fields[attr].currentIndex())
            for attr in self.fields
        }

    def update_annotation(self, annotation: Annotation) -> None:
        """
        Apply current extracted values onto an annotation model.

        Args:
            annotation: Annotation.

        """
        valid_fields = {column.name for column in Annotation.__table__.columns}
        values = self.extract_values()
        for attr, value in values.items():
            if attr not in valid_fields:
                msg = f"Invalid Annotation attribute: {attr}"
                raise AttributeError(msg)
            setattr(annotation, attr, value)


class NounFields(PartOfSpeechFieldsBase):
    """Fields for noun annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Noun"
    #: Catalog code.
    POS_CODE = "N"


class VerbFields(PartOfSpeechFieldsBase):
    """Fields for verb annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Verb"
    #: Catalog code.
    POS_CODE = "V"

    def build(self) -> None:
        """Build the verb fields and wire the class-change rule."""
        super().build()
        self.fields["verb_class"].currentIndexChanged.connect(self._on_class_changed)

    def _on_class_changed(self, _index: int) -> None:
        """
        Auto-set requires infinitive for preterite-present verbs.

        Args:
            _index: Index.

        """
        verb_class = self.extract_values().get("verb_class")
        if verb_class != "pp":
            return
        requires_inf = self.code_to_index_map["verb_requires_infinitive"].get(True)
        if requires_inf is not None:
            self.fields["verb_requires_infinitive"].setCurrentIndex(requires_inf)


class PronounFields(PartOfSpeechFieldsBase):
    """Fields for pronoun annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Pronoun"
    #: Catalog code.
    POS_CODE = "R"


class PrepositionFields(PartOfSpeechFieldsBase):
    """Fields for preposition annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Preposition"
    #: Catalog code.
    POS_CODE = "E"


class AdjectiveFields(PartOfSpeechFieldsBase):
    """Fields for adjective annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Adjective"
    #: Catalog code.
    POS_CODE = "A"


class ArticleFields(PartOfSpeechFieldsBase):
    """Fields for article annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Article"
    #: Catalog code.
    POS_CODE = "D"


class AdverbFields(PartOfSpeechFieldsBase):
    """Fields for adverb annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Adverb"
    #: Catalog code.
    POS_CODE = "B"


class ConjunctionFields(PartOfSpeechFieldsBase):
    """Fields for conjunction annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Conjunction"
    #: Catalog code.
    POS_CODE = "C"


class InterjectionFields(PartOfSpeechFieldsBase):
    """Fields for interjection annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Interjection"
    #: Catalog code.
    POS_CODE = "I"


class NumberFields(PartOfSpeechFieldsBase):
    """Fields for number annotations."""

    #: Part of speech.
    PART_OF_SPEECH: str = "Number"
    #: Catalog code.
    POS_CODE = "L"


class NoneFields(PartOfSpeechFieldsBase):
    """Fields for empty POS state."""

    #: Part of speech.
    PART_OF_SPEECH: str = "N/A"
    #: Catalog code.
    POS_CODE = None


class AnnotationPosFormManager:
    """
    Manager for annotation-modal POS forms.

    Args:
        container_layout: Container layout.
        parent_widget: Parent widget.

    """

    #: Parts of speech.
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
        Initialize the instance.

        Args:
            container_layout: Container layout.
            parent_widget: Parent widget.

        """
        #: Container layout.
        self.container_layout = container_layout
        #: Parent widget.
        self.parent_widget = parent_widget
        #: Current.
        self.current: PartOfSpeechFieldsBase | None = None
        self.select(None)

    def select(self, pos: str | None) -> None:
        """
        Select and render POS-specific fields.

        Args:
            pos: Pos.

        """
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
        """
        Clear layout.

        Args:
            layout: Layout.

        """
        while layout.count():
            item = cast("QLayoutItem", layout.takeAt(0))
            if item.widget():
                widget = cast("QWidget", item.widget())
                widget.hide()
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def reset(self) -> None:
        """
        Reset.
        """
        if self.current:
            self.current.reset()

    def load_from_indices(self, indices: dict[str, int]) -> None:
        """
        Load from indices.

        Args:
            indices: Indices.

        """
        if self.current:
            self.current.load_from_indices(indices)

    def load_from_preset(self, preset: AnnotationPreset) -> None:
        """
        Load from preset.

        Args:
            preset: Preset.

        """
        if self.current:
            self.current.load_from_preset(preset)

    def load_from_annotation(self, annotation: Annotation) -> None:
        """
        Load from annotation.

        Args:
            annotation: Annotation.

        """
        assert self.current is not None, (  # noqa: S101
            "load_from_annotation called without a selected Part of Speech"
        )
        self.current.load_from_annotation(annotation)

    def extract_indices(self) -> dict[str, int]:
        """
        Extract indices.

        Returns:
            The computed value.

        """
        if self.current:
            return self.current.extract_indices()
        return {}

    def extract_values(self) -> dict[str, str | bool | None]:
        """
        Extract values.

        Returns:
            The computed value.

        """
        assert self.current is not None, (  # noqa: S101
            "extract_values called without a selected Part of Speech"
        )
        return self.current.extract_values()

    def update_annotation(self, annotation: Annotation) -> None:
        """
        Update annotation.

        Args:
            annotation: Annotation.

        """
        assert self.current is not None, (  # noqa: S101
            "update_annotation called without a selected Part of Speech"
        )
        self.current.update_annotation(annotation)


class PresetPartOfSpeechFieldsBase(AnnotationLookupsMixin):
    """
    Preset-dialog POS field group built from the POS field catalog.

    Args:
        layout: Layout.
        parent_widget: Parent widget.
        pos: Part of speech code.

    """

    def __init__(self, layout: QFormLayout, parent_widget: QWidget, pos: str) -> None:
        """
        Initialize the instance.

        Args:
            layout: Layout.
            parent_widget: Parent widget.
            pos: Part of speech code.

        """
        #: Layout.
        self.layout = layout
        #: Parent widget.
        self.parent_widget = parent_widget
        #: Part of speech code.
        self.pos = pos
        #: Fields.
        self.fields: dict[str, QComboBox] = {}
        #: Specs by attr.
        self._specs_by_attr: dict[str, PosField] = {}
        #: Code to index map.
        self.code_to_index_map: dict[str, dict[Any, int]] = {}
        #: Index to code map.
        self.index_to_code_map: dict[str, dict[int, Any]] = {}

    def build(self) -> None:
        """Build one combo per catalog field for this preset POS."""
        for field in PosFieldCatalog.fields(self.pos):
            self._specs_by_attr[field.attr] = field
            self._add_field(field)

    def _add_field(self, field: PosField) -> None:
        """
        Add one code-mapped combo for a catalog field.

        Args:
            field: The catalog field to render.

        """
        combo = QComboBox(self.parent_widget)
        combo.setObjectName(f"{self.pos.lower()}_{field.attr}_combo")
        combo.addItem("")
        offset = 1
        if field.preset_clear_mode:
            combo.addItem("Clear")
            offset = 2

        codes = list(field.lookup_map.keys())
        values = list(field.lookup_map.values())
        if values and values[0] == "":
            codes = codes[1:]
            values = values[1:]

        combo.addItems([str(value) for value in values])
        self.code_to_index_map[field.attr] = {
            code: index for index, code in enumerate(codes, start=offset)
        }
        self.index_to_code_map[field.attr] = {
            index: code for code, index in self.code_to_index_map[field.attr].items()
        }
        self.fields[field.attr] = combo
        self.layout.addRow(f"{field.label}:", combo)

    def reset(self) -> None:
        """Reset rendered preset combos to empty."""
        for combo in self.fields.values():
            combo.setCurrentIndex(0)

    def load_from_values(self, field_values: Mapping[str, str | bool | None]) -> None:
        """
        Load preset field values into rendered widgets.

        Args:
            field_values: Field values.

        """
        for attr, value in field_values.items():
            spec = self._specs_by_attr.get(attr)
            combo = self.fields.get(attr)
            if not spec or not combo:
                continue
            if value is None:
                combo.setCurrentIndex(0)
            elif spec.preset_clear_mode and value == CLEAR_SENTINEL:
                combo.setCurrentIndex(1)
            else:
                combo.setCurrentIndex(self.code_to_index_map[attr].get(value, 0))

    def extract_values(self) -> dict[str, str | bool | None]:
        """
        Extract preset values with empty/clear semantics.

        Returns:
            Field values keyed by attribute; ``None`` for blank.

        """
        extracted: dict[str, str | bool | None] = {}
        for attr, spec in self._specs_by_attr.items():
            index = self.fields[attr].currentIndex()
            if index == 0:
                extracted[attr] = None
            elif spec.preset_clear_mode and index == 1:
                extracted[attr] = CLEAR_SENTINEL
            else:
                extracted[attr] = self.index_to_code_map[attr].get(index)
        return extracted


class PresetPosFormManager:
    """
    Manager for preset-dialog POS forms.

    Args:
        pos: Pos.
        form_layout: Form layout.
        parent_widget: Parent widget.

    """

    def __init__(
        self,
        pos: str,
        form_layout: QFormLayout,
        parent_widget: QWidget,
    ) -> None:
        """
        Initialize the instance.

        Args:
            pos: Pos.
            form_layout: Form layout.
            parent_widget: Parent widget.

        """
        if not PosFieldCatalog.preset_supported(pos):
            msg = f"Unsupported preset Part of Speech: {pos}"
            raise ValueError(msg)
        #: Pos.
        self.pos = pos
        #: Form layout.
        self.form_layout = form_layout
        #: Parent widget.
        self.parent_widget = parent_widget
        #: Current.
        self.current = PresetPartOfSpeechFieldsBase(form_layout, parent_widget, pos)
        self.current.build()

    def reset(self) -> None:
        """Reset rendered fields."""
        self.current.reset()

    def field(self, attr: str) -> QComboBox | None:
        """
        Return one managed combo widget by field attribute.

        Args:
            attr: Field attribute name.

        Returns:
            Managed combo box, or ``None`` if the field is not rendered.

        """
        return self.current.fields.get(attr)

    def load_from_values(self, field_values: Mapping[str, str | bool | None]) -> None:
        """
        Load values into managed fields.

        Args:
            field_values: Field values.

        """
        self.current.load_from_values(field_values)

    def extract_values(self) -> dict[str, str | bool | None]:
        """
        Extract values from managed fields.

        Returns:
            The computed value.

        """
        return self.current.extract_values()
