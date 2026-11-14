"""Build the Glossary for one project's exported Full Translation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from oeapp.mixins import AnnotationTextualMixin
from oeapp.models.glossary import GlossaryEntry
from oeapp.utils import normalize_old_english

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.project import Project
    from oeapp.models.token import Token


class Glossary(AnnotationTextualMixin):
    """
    Aggregates one project's Glossary.

    One entry covers a Root under its Normalized Form and part of speech.
    A preposition is also split by the case it governs. Nouns that differ
    only in gender share an entry.

    """

    #: The order of OE alphabet characters, for sorting glossary entries.
    #: Sorting by normal alphabetical order is not sufficient because
    #: æ, þ, ð, ġ and ċ are not handled correctly by the default sorting.
    _OE_ALPHA_ORDER: Final[dict[str, int]] = {
        "a": 0,
        "æ": 1,
        "b": 2,
        "c": 3,
        "d": 4,
        "e": 5,
        "f": 6,
        "g": 7,
        "h": 8,
        "i": 9,
        "j": 10,
        "k": 11,
        "l": 12,
        "m": 13,
        "n": 14,
        "o": 15,
        "p": 16,
        "r": 17,
        "s": 18,
        "t": 19,
        "þ": 20,
        "u": 21,
        "v": 22,
        "w": 23,
        "x": 24,
        "y": 25,
        "z": 26,
    }

    def entries(self, project: Project) -> list[GlossaryEntry]:
        """
        Aggregate and sort glossary entries with Old English collation rules.

        Args:
            project: The project to build glossary entries for.

        Returns:
            A list of glossary entries.

        """
        entries: dict[tuple[str, str, str | None], GlossaryEntry] = {}
        meaning_seen: dict[tuple[str, str, str | None], set[str]] = {}
        example_seen: dict[
            tuple[str, str, str | None], set[tuple[str, str, str | None]]
        ] = {}

        for sentence in project.sentences:
            for token in sorted(sentence.tokens, key=lambda t: t.order_index):
                annotation = token.annotation
                if not annotation or not annotation.root or not annotation.pos:
                    continue
                root = annotation.root.strip()
                root_normalized = annotation.root_normalized or normalize_old_english(
                    root
                )
                pos = annotation.pos.strip()
                if not root or not root_normalized or not pos:
                    continue

                prep_case = annotation.prep_case if pos == "E" else None
                key = (root_normalized, pos, prep_case)
                if key not in entries:
                    entries[key] = GlossaryEntry(
                        root=root,
                        normalized_root=root_normalized,
                        pos=pos,
                        classification=self._classification(annotation),
                        prep_case=prep_case,
                        sort_key=self.sort_key(root_normalized, pos),
                        root_variants=[],
                        verb_class_label=self._verb_class_label(annotation),
                        verb_direct_object_case=annotation.verb_direct_object_case,
                        verb_requires_infinitive=bool(
                            annotation.verb_requires_infinitive
                        ),
                        verb_impersonal=bool(annotation.verb_impersonal),
                        verb_intransitive=(
                            annotation.verb_transitivity == "intransitive"
                        ),
                    )
                    meaning_seen[key] = set()
                    example_seen[key] = set()
                self._merge_root_variant(entries[key], root)
                self._accumulate_glossary_entry(
                    entry=entries[key],
                    annotation=annotation,
                    token=token,
                    seen_meanings=meaning_seen[key],
                    seen_examples=example_seen[key],
                )

        return sorted(
            entries.values(),
            key=lambda item: (
                item.sort_key,
                item.pos,
                item.prep_case or "",
                item.normalized_root,
            ),
        )

    def _accumulate_glossary_entry(
        self,
        entry: GlossaryEntry,
        annotation: Annotation,
        token: Token,
        seen_meanings: set[str],
        seen_examples: set[tuple[str, str, str | None]],
    ) -> None:
        """
        Merge one attestation into an existing glossary entry.

        Args:
            entry: Glossary entry to update.
            annotation: Annotation source data.
            token: Token source data.
            seen_meanings: Dedup tracker for meanings.
            seen_examples: Dedup tracker for examples.

        """
        for meaning in self._split_meanings(annotation.modern_english_meaning):
            norm = meaning.casefold()
            if norm not in seen_meanings:
                entry.meanings.append(meaning)
                seen_meanings.add(norm)

        code = (
            "" if annotation.pos in ("C", "E") else self._attested_form_code(annotation)
        )
        sense = annotation.sense.strip() if annotation.sense else None
        example = (token.surface.lower(), code, sense)
        example_norm = (
            token.surface.lower(),
            code,
            sense.casefold() if sense else None,
        )
        if example_norm not in seen_examples:
            entry.examples.append(example)
            seen_examples.add(example_norm)
        if annotation.gender:
            entry.used_genders.add(annotation.gender)
        if annotation.case:
            entry.used_cases.add(annotation.case)
        if annotation.prep_case:
            entry.used_cases.add(annotation.prep_case)
        if annotation.verb_direct_object_case:
            entry.used_cases.add(annotation.verb_direct_object_case)
        if annotation.pos == "V":
            if entry.verb_class_label is None:
                entry.verb_class_label = self._verb_class_label(annotation)
            if (
                entry.verb_direct_object_case is None
                and annotation.verb_direct_object_case
            ):
                entry.verb_direct_object_case = annotation.verb_direct_object_case
            entry.verb_requires_infinitive = entry.verb_requires_infinitive or bool(
                annotation.verb_requires_infinitive
            )
            entry.verb_impersonal = entry.verb_impersonal or bool(
                annotation.verb_impersonal
            )
            entry.verb_intransitive = entry.verb_intransitive or (
                annotation.verb_transitivity == "intransitive"
            )

    def _merge_root_variant(self, entry: GlossaryEntry, root: str) -> None:
        """
        Merge a new root spelling into an existing glossary entry.

        Args:
            entry: Existing glossary entry.
            root: Incoming root spelling from annotation data.

        """
        if root == entry.root or root in entry.root_variants:
            return
        if self._root_display_score(root) > self._root_display_score(entry.root):
            entry.root_variants.append(entry.root)
            entry.root = root
            return
        entry.root_variants.append(root)
        entry.root_variants = sorted(set(entry.root_variants), key=str.casefold)

    def _root_display_score(self, root: str) -> tuple[int, int]:
        """
        Score a root form for display preference.

        Higher values win and favor richer diacritics and internal dashes.

        Args:
            root: The root form to score.

        Returns:
            Tuple score for comparison.

        """
        diacritics = sum(1 for ch in root if ch in "āēīōūȳǣċġ")
        dashes = sum(1 for ch in root if ch in "-–—")  # noqa: RUF001
        return diacritics + dashes, len(root)

    def _classification(self, annotation: Annotation) -> str:  # noqa: PLR0911
        """
        Render classification text for glossary entries.

        Args:
            annotation: The annotation to render the classification for.

        Returns:
            The rendered classification text.

        """
        if annotation.pos == "N":
            declension = (
                self.DECLENSION_MAP.get(annotation.declension, annotation.declension)
                if annotation.declension
                else None
            )
            parts = [part for part in (annotation.gender, declension) if part]
            return " ".join(parts)
        if annotation.pos == "V":
            verb_class = "?"
            if annotation.verb_class:
                verb_class = self.VERB_CLASS_MAP.get(
                    annotation.verb_class, annotation.verb_class
                )
            parts = [verb_class]
            if (
                annotation.verb_direct_object_case
                and annotation.verb_direct_object_case != "a"
            ):
                case_name = self.CASE_MAP.get(
                    annotation.verb_direct_object_case,
                    annotation.verb_direct_object_case,
                )
                parts.append(f"(+ {case_name})")
            return " ".join(parts)
        if annotation.pos == "R":
            if annotation.pronoun_type:
                return self.PRONOUN_TYPE_MAP.get(
                    annotation.pronoun_type, annotation.pronoun_type
                )
            return ""
        if annotation.pos == "E":
            if not annotation.prep_case:
                return ""
            case_name = self.CASE_MAP.get(annotation.prep_case, annotation.prep_case)
            return f"(+{case_name})"
        return ""

    def _attested_form_code(self, annotation: Annotation) -> str:  # noqa: PLR0911
        """
        Render compact DB-code annotations for attested forms.

        Args:
            annotation: The annotation to render the attested form code for.

        Returns:
            The rendered attested form code.

        """
        if annotation.pos == "N":
            return self._dot_join(annotation.case, annotation.number)

        if annotation.pos == "V":
            tense_code = self._verb_tense_code(annotation.verb_tense)
            if annotation.verb_form == "p":
                return self._dot_join("p", tense_code)
            if annotation.verb_form == "i":
                return "i"
            if annotation.verb_form == "ii":
                return "ii"
            return self._dot_join(
                tense_code,
                annotation.verb_mood,
                annotation.verb_person,
                annotation.number,
            )

        if annotation.pos == "R":
            return self._dot_join(
                annotation.pronoun_type, annotation.pronoun_number, annotation.case
            )
        if annotation.pos == "D":
            return self._dot_join(
                annotation.article_type, annotation.case, annotation.number
            )
        if annotation.pos == "A":
            return self._dot_join(
                annotation.adjective_degree,
                annotation.adjective_inflection,
                annotation.gender,
                annotation.case,
                annotation.number,
            )
        if annotation.pos == "B":
            return self._dot_join(annotation.adverb_degree)
        if annotation.pos == "L":
            return self._dot_join(annotation.case, annotation.number)
        return self._dot_join(annotation.case, annotation.number)

    def _verb_class_label(self, annotation: Annotation) -> str | None:
        """
        Resolve human-readable verb class label from annotation.

        Args:
            annotation: Source annotation.

        Returns:
            Verb class label or ``None``.

        """
        if not annotation.verb_class:
            return None
        return self.VERB_CLASS_MAP.get(annotation.verb_class, annotation.verb_class)

    def sort_key(self, root: str, pos: str) -> tuple[int, ...]:
        """
        Return a sort key using Old English collation and ``ġe``-prefix rule.

        Args:
            root: The root of the entry.
            pos: The part-of-speech of the entry.

        Returns:
            A sort key using Old English collation and ``ġe``-prefix rule.

        """
        original = root.casefold()
        if pos in {"N", "V"} and original.startswith("ġe"):
            original = original[2:]

        normalized = self._normalize_oe_for_sort(original)
        key: list[int] = []
        for ch in normalized:
            if ch in self._OE_ALPHA_ORDER:
                key.append(self._OE_ALPHA_ORDER[ch])
                continue
            if ch.isalpha():
                key.extend((999, ord(ch)))
        return tuple(key)

    def _normalize_oe_for_sort(self, text: str) -> str:
        """
        Normalize text for OE glossary collation.

        Args:
            text: Text.

        Returns:
            The computed value.

        """
        translations = str.maketrans(
            {
                "ā": "a",
                "ē": "e",
                "ī": "i",
                "ō": "o",
                "ū": "u",
                "ȳ": "y",
                "ǣ": "æ",
                "ċ": "c",
                "ġ": "g",
                "ð": "þ",
            }
        )
        normalized = text.translate(translations)
        normalized = normalized.lstrip("-–— ")  # noqa: RUF001
        return re.sub(r"[^a-zæþ]", "", normalized)

    def _split_meanings(self, modern_meaning: str | None) -> list[str]:
        """
        Split and dedupe senses on semicolon/comma boundaries.

        Args:
            modern_meaning: The modern meaning to split.

        Returns:
            A list of split and deduped senses.

        """
        if not modern_meaning:
            return []
        parts = [
            part.strip() for part in re.split(r"[;,]", modern_meaning) if part.strip()
        ]
        deduped: list[str] = []
        seen: set[str] = set()
        for part in parts:
            norm = part.casefold()
            if norm not in seen:
                deduped.append(part)
                seen.add(norm)
        return deduped

    def _dot_join(self, *parts: str | None) -> str:
        """
        Join non-empty code segments without separators.

        Args:
            *parts: The parts to join.

        Returns:
            A string of the joined parts.

        """
        filtered = [part for part in parts if part]
        return "".join(filtered) if filtered else "-"

    def _verb_tense_code(self, tense: str | None) -> str | None:
        """
        Render concise verb tense codes without POS ambiguity.

        Args:
            tense: The tense to render the code for.

        Returns:
            The rendered tense code.

        """
        if tense == "n":
            return "pr"
        if tense == "p":
            return "pa"
        return tense
