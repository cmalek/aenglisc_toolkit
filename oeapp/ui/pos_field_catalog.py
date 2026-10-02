"""Single definition of the annotation fields shown for each part of speech."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final

from oeapp.ui.mixins import AnnotationLookupsMixin as Maps

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class PosField:
    """One annotation field as presented on every surface."""

    #: Annotation column name.
    attr: str
    #: Canonical label, without punctuation.
    label: str
    #: Code-to-label map for the field's combo box.
    lookup_map: Mapping[Any, str]
    #: Whether presets offer an explicit "Clear" choice for this field.
    preset_clear_mode: bool = True


@dataclass(frozen=True)
class _PosEntry:
    """The ordered fields for one part of speech."""

    #: Fields in display order.
    fields: tuple[PosField, ...]


#: Fields shared by several parts of speech.
_GENDER: Final = PosField("gender", "Gender", Maps.GENDER_MAP)
#: Number for non-pronoun parts of speech.
_NUMBER: Final = PosField("number", "Number", Maps.NUMBER_MAP)
#: Grammatical case.
_CASE: Final = PosField("case", "Case", Maps.CASE_MAP)


class PosFieldCatalog:
    """
    Which annotation fields each part of speech has, and how they read.

    The annotation modal, the preset dialog and the token details sidebar all
    iterate this catalog, so a field is added in one place. The catalog holds
    data only; widgets stay in the surfaces that consume it.
    """

    #: Part-of-speech codes the preset dialog supports.
    PRESET_POS: ClassVar[frozenset[str]] = frozenset({"N", "V", "A", "R", "D"})

    #: Entries keyed by one-letter POS code.
    _ENTRIES: ClassVar[dict[str | None, _PosEntry]] = {
        "N": _PosEntry(
            (
                _GENDER,
                _NUMBER,
                _CASE,
                PosField(
                    "declension",
                    "Declension",
                    Maps.DECLENSION_MAP,
                    preset_clear_mode=False,
                ),
            )
        ),
        "V": _PosEntry(
            (
                PosField(
                    "verb_class", "Class", Maps.VERB_CLASS_MAP, preset_clear_mode=False
                ),
                PosField("verb_tense", "Tense", Maps.VERB_TENSE_MAP),
                PosField("verb_mood", "Mood", Maps.VERB_MOOD_MAP),
                PosField("verb_person", "Person", Maps.VERB_PERSON_MAP),
                _NUMBER,
                PosField("verb_aspect", "Aspect", Maps.VERB_ASPECT_MAP),
                PosField(
                    "verb_direct_object_case",
                    "Direct Object Case",
                    Maps.VERB_DIRECT_OBJECT_CASE_MAP,
                ),
                PosField("verb_form", "Form", Maps.VERB_FORM_MAP),
                PosField(
                    "verb_requires_infinitive",
                    "Requires Infinitive",
                    Maps.VERB_BOOLEAN_MAP,
                ),
                PosField("verb_impersonal", "Impersonal", Maps.VERB_BOOLEAN_MAP),
                PosField(
                    "verb_transitivity", "Transitivity", Maps.VERB_TRANSITIVITY_MAP
                ),
            )
        ),
        "A": _PosEntry(
            (
                PosField("adjective_degree", "Degree", Maps.ADJECTIVE_DEGREE_MAP),
                PosField(
                    "adjective_inflection", "Inflection", Maps.ADJECTIVE_INFLECTION_MAP
                ),
                _GENDER,
                _NUMBER,
                _CASE,
            )
        ),
        "R": _PosEntry(
            (
                PosField("pronoun_type", "Type", Maps.PRONOUN_TYPE_MAP),
                _GENDER,
                PosField("pronoun_number", "Number", Maps.PRONOUN_NUMBER_MAP),
                _CASE,
            )
        ),
        "D": _PosEntry(
            (
                PosField("article_type", "Type", Maps.ARTICLE_TYPE_MAP),
                _GENDER,
                _NUMBER,
                _CASE,
            )
        ),
        "E": _PosEntry(
            (PosField("prep_case", "Governed Case", Maps.PREPOSITION_CASE_MAP),)
        ),
        "B": _PosEntry((PosField("adverb_degree", "Degree", Maps.ADVERB_DEGREE_MAP),)),
        "C": _PosEntry(
            (PosField("conjunction_type", "Type", Maps.CONJUNCTION_TYPE_MAP),)
        ),
    }

    @classmethod
    def fields(cls, pos: str | None) -> tuple[PosField, ...]:
        """
        Return the ordered fields for a part of speech.

        Args:
            pos: One-letter POS code, or ``None`` for the empty POS state.

        Returns:
            The fields in display order; empty for field-less or unknown POS.

        """
        entry = cls._ENTRIES.get(pos)
        return entry.fields if entry else ()

    @classmethod
    def preset_supported(cls, pos: str | None) -> bool:
        """
        Return whether the preset dialog supports a part of speech.

        Args:
            pos: One-letter POS code, or ``None``.

        Returns:
            ``True`` for N, V, A, R and D.

        """
        return pos in cls.PRESET_POS
