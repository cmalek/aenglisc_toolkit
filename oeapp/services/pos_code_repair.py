"""Tiered repair of label-form part-of-speech codes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class PosCodeRepair:
    """
    Turn a stored value into the code it was meant to be.

    Tiers, first match wins: already a code; trailing ``(code)``; normalised
    label. There is deliberately no fuzzy matching, because the labels differ
    by one character ("Strong Class 1 (s1)" against "Strong Class 2 (s2)").

    Args:
        valid_codes: The codes the column may hold.
        labels: Display label to code.

    """

    #: A trailing parenthesised code, as every label ends.
    _SUFFIX: ClassVar[re.Pattern[str]] = re.compile(r"\(([^()]+)\)\s*$")

    def __init__(self, valid_codes: Iterable[str], labels: Mapping[str, str]) -> None:
        """
        Initialize the repairer.

        Args:
            valid_codes: The codes the column may hold.
            labels: Display label to code.

        """
        #: Valid codes.
        self.valid_codes: frozenset[str] = frozenset(valid_codes)
        #: Normalised label to code.
        self._labels: dict[str, str] = {
            self._normalise(label): code for label, code in labels.items()
        }

    @staticmethod
    def _normalise(text: str) -> str:
        """Collapse whitespace and case-fold ``text``."""
        return " ".join(text.split()).casefold()

    @classmethod
    def from_mapping(cls, spec: Mapping[str, Any]) -> PosCodeRepair:
        """
        Build a repairer from a ``field_mappings.json`` values spec.

        Args:
            spec: ``{"codes": [...], "labels": {label: code}}``.

        Returns:
            The repairer.

        Raises:
            ValueError: If the spec is malformed.

        """
        codes = spec.get("codes") if isinstance(spec, dict) else None
        labels = spec.get("labels") if isinstance(spec, dict) else None
        if not isinstance(codes, list) or not isinstance(labels, dict):
            msg = f"Malformed values mapping: {spec!r}"
            # ValueError, not TypeError: the import handler swallows TypeError.
            raise ValueError(msg)  # noqa: TRY004
        return cls(codes, labels)

    def repair(self, value: str) -> str | None:
        """
        Repair one stored value.

        Args:
            value: The stored string.

        Returns:
            The code; ``None`` for a blank value; ``value`` unchanged when no
            tier matches.

        """
        if value in self.valid_codes:
            return value
        if not value.strip():
            return None
        match = self._SUFFIX.search(value)
        if match and match.group(1).strip() in self.valid_codes:
            return match.group(1).strip()
        return self._labels.get(self._normalise(value), value)
