"""Glossary entries for one project's exported Full Translation."""

from dataclasses import dataclass, field


@dataclass
class GlossaryEntry:
    """
    One Glossary entry for a normalized root, part of speech, and preposition case.
    """

    #: The root word of the glossary entry.
    root: str
    #: The normalized root used for deduping forms.
    normalized_root: str
    #: The part of speech of the glossary entry.
    pos: str
    #: The classification of the glossary entry.
    classification: str
    #: The prep case of the glossary entry.
    prep_case: str | None = None
    #: The sort key of the glossary entry.
    sort_key: tuple[int, ...] = field(default_factory=tuple)
    #: The genders used in the glossary entry.
    used_genders: set[str] = field(default_factory=set)
    #: The cases used in the glossary entry.  Used to ensure that all the
    #: we only list a single instance of each case.
    used_cases: set[str] = field(default_factory=set)
    #: The modern English meanings of the glossary entry.
    meanings: list[str] = field(default_factory=list)
    #: The attested forms of the glossary entry from the text.
    examples: list[tuple[str, str, str | None]] = field(default_factory=list)
    #: Other root spellings that normalize to the same root.
    root_variants: list[str] = field(default_factory=list)
    #: Verb class label for verb entries.
    verb_class_label: str | None = None
    #: Verb direct object case for verb entries.
    verb_direct_object_case: str | None = None
    #: Whether any entry requires an infinitive complement.
    verb_requires_infinitive: bool = False
    #: Whether any entry is impersonal.
    verb_impersonal: bool = False
    #: Whether any entry is intransitive.
    verb_intransitive: bool = False
