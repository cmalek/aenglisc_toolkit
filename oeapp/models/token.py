"""Token model."""

import builtins
import difflib
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.annotation import Annotation
from oeapp.models.mixins import SaveDeleteMixin
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class Token(SaveDeleteMixin, Base):
    """Represents a tokenized word in a sentence."""

    __tablename__ = "tokens"
    __table_args__ = (
        UniqueConstraint("sentence_id", "order_index", name="uq_tokens_sentence_order"),
    )

    #: The Old English characters. These are the characters that are allowed in
    #: the surface form of a token beyond the basic Latin characters.
    OE_CHARS: ClassVar[str] = "þÞðÐæǣÆǢȝġĠċĊāĀȳȲēĒīĪūŪōŌū"
    #: The value of the order index that indicates a token is no longer in the
    #: sentence.
    NO_ORDER_INDEX: ClassVar[int] = -1

    #: The token ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The order index of the token in the sentence.
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The surface form of the token.
    surface: Mapped[str] = mapped_column(String, nullable=False)
    #: The lemma of the token.
    lemma: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the token was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the token was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="tokens")
    annotation: Mapped[Annotation | None] = relationship(
        "Annotation",
        back_populates="token",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_json(self) -> dict:
        """
        Serialize token to JSON-compatible dictionary (without PKs).

        Returns:
            Dictionary containing token data with annotation if exists

        """
        token_data: dict = {
            "order_index": self.order_index,
            "surface": self.surface,
            "lemma": self.lemma,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

        # Add annotation if it exists
        if self.annotation:
            token_data["annotation"] = self.annotation.to_json()

        return token_data

    @classmethod
    def from_json(
        cls,
        sentence_id: int,
        token_data: dict,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Token:
        """
        Create a token and annotation from JSON import data.

        Args:
            sentence_id: Sentence ID to attach token to
            token_data: Token data dictionary from JSON

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Created Token entity

        """
        session = cls._get_session()
        token = cls(
            sentence_id=sentence_id,
            order_index=token_data["order_index"],
            surface=token_data["surface"],
            lemma=token_data.get("lemma"),
        )
        created_at = from_utc_iso(token_data.get("created_at"))
        if created_at:
            token.created_at = created_at
        updated_at = from_utc_iso(token_data.get("updated_at"))
        if updated_at:
            token.updated_at = updated_at

        session.add(token)
        session.flush()

        # Create annotation if it exists
        if "annotation" in token_data:
            Annotation.from_json(token.id, token_data["annotation"], commit=commit)

        if commit:
            session.commit()

        return token

    @classmethod
    def get(cls, token_id: int) -> Token | None:
        """
        Get a token by ID.

        Args:
            token_id: Token ID

        Returns:
            Token or None if not found

        """
        session = cls._get_session()
        return session.get(cls, token_id)

    @classmethod
    def list(cls, sentence_id: int) -> builtins.list[Token]:
        """
        Get all tokens by sentence ID, ordered by order index.

        Args:
            sentence_id: Sentence ID

        Returns:
            List of tokens ordered by order index

        """
        session = cls._get_session()
        return builtins.list(
            session.scalars(
                select(cls)
                .where(cls.sentence_id == sentence_id)
                .order_by(cls.order_index)
            ).all()
        )

    @classmethod
    def create_from_sentence(
        cls,
        sentence_id: int,
        sentence_text: str,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> builtins.list[Token]:
        """
        Create new tokens for a sentence.

        Args:
            sentence_id: Sentence ID
            sentence_text: Text of the sentence to tokenize

        Keyword Args:
            commit: Whether to commit the changes to the database

        Returns:
            List of :class:`~oeapp.models.token.Token` objects

        """
        session = cls._get_session()
        # Tokenize sentence
        token_strings = cls.tokenize(sentence_text)
        tokens = []
        for token_index, token_surface in enumerate(token_strings):
            token = cls(
                sentence_id=sentence_id,
                order_index=token_index,
                surface=token_surface,
            )
            session.add(token)
            session.flush()  # Get the ID

            if not Annotation.exists(token_id=token.id):
                annotation = Annotation(token_id=token.id)
                annotation.save(commit=False)

            tokens.append(token)
        session.flush()
        if commit:
            session.commit()
        return tokens

    @classmethod
    def update_from_sentence(
        cls, sentence_text: str, sentence_id: int
    ) -> builtins.list[str]:
        """
        Update tokens in the sentence and re-order them.

        Args:
            sentence_text: Text of the sentence to update
            sentence_id: Sentence ID

        Returns:
            List of messages

        """
        session = cls._get_session()
        token_strings = cls.tokenize(sentence_text)
        existing_tokens = cls.list(sentence_id)

        # Capture original order indices before moving to temp positions
        original_orders = {t.id: t.order_index for t in existing_tokens}

        # Move to temporary negative positions
        cls._move_to_temp_positions(existing_tokens, session)

        # Match tokens
        old_surfaces = [t.surface for t in existing_tokens]
        matcher = difflib.SequenceMatcher(None, old_surfaces, token_strings)

        matched_positions: dict[int, Token] = {}
        matched_token_ids: set[int] = set()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            cls._process_opcode(
                tag,
                i1,
                i2,
                j1,
                j2,
                existing_tokens,
                token_strings,
                sentence_id,
                session,
                matched_positions,
                matched_token_ids,
            )

        session.flush()
        cls._delete_unmatched_tokens(existing_tokens, matched_token_ids, session)

        # Update notes AND idioms
        cls._update_notes_for_token_changes(
            sentence_id, existing_tokens, matched_positions, matched_token_ids
        )
        messages = cls._update_idioms_for_token_changes(
            sentence_id,
            existing_tokens,
            matched_positions,
            matched_token_ids,
            original_orders,
        )

        session.commit()
        return messages

    @classmethod
    def _move_to_temp_positions(cls, tokens: builtins.list[Token], session) -> None:
        """Move tokens to temporary negative positions."""
        for i, token in enumerate(tokens):
            token.order_index = -(i + 1)
            session.add(token)
        session.flush()

    @classmethod
    def _process_opcode(  # noqa: PLR0913
        cls,
        tag,
        i1,
        i2,
        j1,
        j2,
        existing_tokens,
        token_strings,
        sentence_id,
        session,
        matched_positions,
        matched_token_ids,
    ) -> None:
        """Process a single difflib opcode."""
        if tag == "equal":
            for k in range(i2 - i1):
                token = existing_tokens[i1 + k]
                new_idx = j1 + k
                token.order_index = new_idx
                session.add(token)
                matched_positions[new_idx] = token
                matched_token_ids.add(token.id)
        elif tag == "replace":
            cls._handle_replace_opcode(
                i1,
                i2,
                j1,
                j2,
                existing_tokens,
                token_strings,
                sentence_id,
                session,
                matched_positions,
                matched_token_ids,
            )
        elif tag == "insert":
            for k in range(j2 - j1):
                cls._create_new_token(
                    j1 + k,
                    token_strings[j1 + k],
                    sentence_id,
                    session,
                    matched_positions,
                )

    @classmethod
    def _handle_replace_opcode(  # noqa: PLR0913
        cls,
        i1,
        i2,
        j1,
        j2,
        existing_tokens,
        token_strings,
        sentence_id,
        session,
        matched_positions,
        matched_token_ids,
    ) -> None:
        """Handle 'replace' opcode."""
        if (i2 - i1) == (j2 - j1):
            # Typo fix preservation
            for k in range(i2 - i1):
                token = existing_tokens[i1 + k]
                new_idx = j1 + k
                token.surface = token_strings[new_idx]
                token.order_index = new_idx
                session.add(token)
                matched_positions[new_idx] = token
                matched_token_ids.add(token.id)
        else:
            # Treat as delete + insert
            for k in range(j2 - j1):
                cls._create_new_token(
                    j1 + k,
                    token_strings[j1 + k],
                    sentence_id,
                    session,
                    matched_positions,
                )

    @classmethod
    def _create_new_token(
        cls, index, surface, sentence_id, session, matched_positions
    ) -> Token:
        """Create a new token and its empty annotation."""
        token = cls(sentence_id=sentence_id, order_index=index, surface=surface)
        session.add(token)
        session.flush()
        if not Annotation.exists(token_id=token.id):
            annotation = Annotation(token_id=token.id)
            session.add(annotation)
        matched_positions[index] = token
        return token

    @classmethod
    def _delete_unmatched_tokens(cls, tokens, matched_ids, session) -> None:
        """Delete tokens that were not matched."""
        for token in tokens:
            if token.id not in matched_ids:
                session.delete(token)
        session.flush()

    @classmethod
    def _update_notes_for_token_changes(
        cls,
        sentence_id: int,
        old_tokens: builtins.list[Token],
        new_token_positions: dict[int, Token],
        matched_token_ids: set[int],
    ) -> None:
        """Update notes when tokens change."""
        from oeapp.models.sentence import Sentence  # noqa: PLC0415

        sentence = Sentence.get(sentence_id)
        session = cls._get_session()
        if not sentence or not sentence.notes:
            return

        # Build mapping of old token ID to new token
        old_token_id_to_new: dict[int, Token] = {}
        for token in new_token_positions.values():
            if token.id:
                old_token_id_to_new[token.id] = token

        # Process each note
        notes_to_delete = []
        for note in sentence.notes:
            if not note.start_token or not note.end_token:
                notes_to_delete.append(note)
                continue

            # Check if start/end tokens still exist
            start_exists = note.start_token in matched_token_ids
            end_exists = note.end_token in matched_token_ids

            if not start_exists or not end_exists:
                # One or both tokens were deleted - try to find replacement tokens
                new_start_token, new_end_token = cls._find_replacement_tokens_for_note(
                    note, old_tokens, new_token_positions
                )

                if (
                    new_start_token
                    and new_end_token
                    and new_start_token.id
                    and new_end_token.id
                ):
                    note.start_token = new_start_token.id
                    note.end_token = new_end_token.id
                    session.add(note)
                else:
                    notes_to_delete.append(note)
            else:
                # Both exist, check if range is still valid
                new_start_token = old_token_id_to_new.get(note.start_token)
                new_end_token = old_token_id_to_new.get(note.end_token)

                if new_start_token and new_end_token:
                    if new_start_token.order_index > new_end_token.order_index:
                        note.start_token, note.end_token = (
                            new_end_token.id,
                            new_start_token.id,
                        )
                        session.add(note)

        for note in notes_to_delete:
            session.delete(note)
        session.flush()

    @classmethod
    def _find_replacement_tokens_for_note(
        cls, note, old_tokens, new_token_positions
    ) -> tuple[Token | None, Token | None]:
        """Find replacement tokens for a note whose tokens were deleted."""
        old_start_token = next(
            (t for t in old_tokens if t.id == note.start_token), None
        )
        old_end_token = next((t for t in old_tokens if t.id == note.end_token), None)

        if not old_start_token or not old_end_token:
            return None, None

        old_start_order = old_start_token.order_index
        old_end_order = old_end_token.order_index

        new_start_token = None
        new_end_token = None
        min_start_dist = float("inf")
        min_end_dist = float("inf")

        for new_pos, new_token in new_token_positions.items():
            if new_token.id:
                dist_start = abs(new_pos - old_start_order)
                if dist_start < min_start_dist:
                    min_start_dist = dist_start
                    new_start_token = new_token

                dist_end = abs(new_pos - old_end_order)
                if dist_end < min_end_dist:
                    min_end_dist = dist_end
                    new_end_token = new_token

        return new_start_token, new_end_token

    @classmethod
    def _update_idioms_for_token_changes(
        cls,
        sentence_id: int,
        old_tokens: builtins.list[Token],
        new_token_positions: dict[int, Token],
        matched_token_ids: set[int],
        original_orders: dict[int, int],
    ) -> builtins.list[str]:
        """
        Update idioms when tokens change.

        Args:
            sentence_id: Sentence ID
            old_tokens: List of old tokens
            new_token_positions: Dictionary of new token positions
            matched_token_ids: Set of matched token IDs
            original_orders: Dictionary of original orders

        Returns:
            List of messages

        """
        from oeapp.models.sentence import Sentence  # noqa: PLC0415

        sentence = Sentence.get(sentence_id)
        session = cls._get_session()
        messages: builtins.list[str] = []
        if not sentence or not sentence.idioms:
            return messages

        for idiom in list(sentence.idioms):
            # Check if all tokens in the ORIGINAL range still exist
            start_order = original_orders.get(idiom.start_token_id)
            end_order = original_orders.get(idiom.end_token_id)

            if start_order is None or end_order is None:
                # Should not happen if data is consistent
                session.delete(idiom)
                messages.append(
                    "Idiom annotation deleted because its boundary tokens were lost."
                )
                continue

            # Find old tokens in this original range
            old_ids_in_range = {
                t.id
                for t in old_tokens
                if start_order <= original_orders.get(t.id, -1) <= end_order
            }

            # If any of the tokens that were in this idiom are missing from matches...
            if not old_ids_in_range.issubset(matched_token_ids):
                # A token was deleted from the idiom
                session.delete(idiom)
                messages.append(
                    "Idiom annotation deleted because one of its tokens was removed."
                )
                continue

            # Update boundary tokens if they were replaced by typo fixes
            # (token_id remains same, so no action needed for IDs)
            # But we should check if they still exist in new_token_positions
            # (which they should if matched_token_ids includes them)

        session.flush()
        return messages

    @classmethod
    def tokenize(cls, sentence_text: str) -> builtins.list[str]:  # noqa: PLR0912, PLR0915
        """
        Tokenize a sentence.

        Args:
            sentence_text: Text of the sentence to tokenize

        Returns:
            List of token strings

        """
        # Split on whitespace, but preserve punctuation as separate tokens
        # This handles Old English characters like þ, ð, æ, etc.
        tokens = []
        # Use regex to split on whitespace while preserving punctuation
        words = re.split(r"\s+", sentence_text.strip())

        # Build character class for word characters including Old English chars
        # Escape special regex characters in OE_CHARS
        oe_chars_escaped = re.escape(cls.OE_CHARS)
        word_char_class = rf"[\w{oe_chars_escaped}]"

        # Pattern to match hyphenated words: word_chars + hyphen/en-dash/em-dash
        # + word_chars
        hyphenated_pattern = rf"{word_char_class}+[-–—]{word_char_class}+"  # noqa: RUF001

        # Pattern for remaining words and punctuation
        word_pattern = rf"{word_char_class}+"
        punct_pattern = r'[.,;:!?\-—"\'.]+'

        for word in words:
            if not word:
                continue
            # Skip standalone punctuation marks
            if word in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                continue
            # Check for punctuation-quote combinations (?" ." !") - skip these
            if re.match(r'^[.!?]+["\']+$', word):
                continue

            # First, extract hyphenated words
            hyphenated_matches = list(re.finditer(hyphenated_pattern, word))

            if hyphenated_matches:
                # Process hyphenated words and remaining text
                last_end = 0
                processed_ranges = []

                for match in hyphenated_matches:
                    # Add any text before this hyphenated word
                    before_text = word[last_end : match.start()]
                    if before_text:
                        # Tokenize the text before the hyphenated word
                        parts = re.findall(
                            rf"{word_pattern}|{punct_pattern}", before_text
                        )
                        for part in parts:
                            # Skip commas, colons, semicolons, hyphens, quotes
                            # (attached punctuation)
                            if part in [",", ";", ":", "-", "—", '"', "'"]:
                                continue
                            # Skip punctuation-quote combinations
                            if re.match(r'^[.!?]+["\']+$', part):
                                continue
                            tokens.append(part)

                    # Add the hyphenated word as a single token
                    tokens.append(match.group())
                    processed_ranges.append((match.start(), match.end()))
                    last_end = match.end()

                # Add any remaining text after the last hyphenated word
                remaining_text = word[last_end:]
                if remaining_text:
                    # Tokenize remaining text, but skip parts that overlap with
                    # hyphenated words
                    parts = re.findall(
                        rf"{word_pattern}|{punct_pattern}", remaining_text
                    )
                    for part in parts:
                        # Skip commas, colons, semicolons, hyphens, quotes
                        # (attached punctuation)
                        if part in [",", ";", ":", "-", "—", '"', "'"]:
                            continue
                        # Skip punctuation-quote combinations
                        if re.match(r'^[.!?]+["\']+$', part):
                            continue
                        # Check if this part overlaps with any processed hyphenated word
                        part_start_in_word = word.find(part, last_end)
                        if part_start_in_word != -1:
                            part_end_in_word = part_start_in_word + len(part)
                            overlaps = any(
                                start < part_end_in_word and end > part_start_in_word
                                for start, end in processed_ranges
                            )
                            if not overlaps:
                                tokens.append(part)
            else:
                # No hyphenated words, use original logic
                parts = re.findall(rf"{word_pattern}|{punct_pattern}", word)
                for part in parts:
                    # Skip commas, colons, semicolons, hyphens, quotes (attached
                    # punctuation)
                    if part in [",", ";", ":", "-", "—", '"', "'"]:
                        continue
                    # Skip punctuation-quote combinations
                    if re.match(r'^[.!?]+["\']+$', part):
                        continue
                    tokens.append(part)

        # Filter out closing punctuation at the end of the token list
        # Remove trailing .!? tokens (even without quotes) - these are closing
        # punctuation that should remain in sentence text but not be tokenized
        while tokens and tokens[-1] in (".", "!", "?"):
            tokens.pop()

        return tokens
