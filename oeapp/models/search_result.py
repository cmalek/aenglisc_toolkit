"""Search result value objects shared by model search and UI navigation."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class SearchResult:
    """
    Search result descriptor used for project-wide navigation.

    Attributes:
        chapter_id: Owning chapter id.
        section_id: Owning section id.
        sentence_id: Owning sentence id.
        match_kind: Match source kind.
        token_id: Matched token id for OE matches.
        match_count: Number of matches represented by this result.

    """

    #: Owning chapter id.
    chapter_id: int
    #: Owning section id.
    section_id: int
    #: Owning sentence id.
    sentence_id: int
    #: Match source kind.
    match_kind: Literal["oe_surface", "oe_root", "mode_text", "note_text"]
    #: Matched token id for OE matches.
    token_id: int | None = None
    #: Number of matches represented by this result.
    match_count: int = 1


@dataclass(slots=True)
class ProjectSearchMatches:
    """
    Ordered project-wide search matches and highlight metadata.

    Attributes:
        results: Ordered search results across the project.
        total_match_count: Total number of matched occurrences.
        token_map: Sentence id to matched token ids for OE highlights.

    """

    #: Ordered search results across the project.
    results: list[SearchResult] = field(default_factory=list)
    #: Total number of matched occurrences.
    total_match_count: int = 0
    #: Sentence id to matched token ids for OE highlights.
    token_map: dict[int, set[int]] = field(default_factory=dict)
