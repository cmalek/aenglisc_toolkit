"""Token model."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.annotation import Annotation

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class Token(Base):
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
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the token was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="tokens")
    annotation: Mapped[Annotation | None] = relationship(
        "Annotation",
        back_populates="token",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @classmethod
    def create_from_sentence(
        cls, session, sentence_id: int, sentence_text: str
    ) -> list[Token]:
        """
        Create new tokens for a sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`import` taking a token id
        or surface, it takes the sentence text and sentence id.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID
            sentence_text: Text of the sentence to tokenize

        Returns:
            List of :class:`~oeapp.models.token.Token` objects

        """
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

            existing_annotation = session.scalar(
                select(Annotation).where(Annotation.token_id == token.id)
            )
            if not existing_annotation:
                annotation = Annotation(token_id=token.id)
                session.add(annotation)

            tokens.append(token)
        session.flush()
        return tokens

    @classmethod
    def tokenize(cls, sentence_text: str) -> list[str]:
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
        for word in words:
            if not word:
                continue
            # Skip standalone punctuation marks
            if word in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                continue
            # Check for punctuation-quote combinations (?" ." !") - skip these
            if re.match(r'^[.!?]+["\']+$', word):
                continue
            # Split punctuation from words
            # Match word characters (including Old English chars) and punctuation
            # separately
            pattern = rf'[\w{re.escape(cls.OE_CHARS)}]+|[.,;:!?\-—"\'.]+'
            parts = re.findall(pattern, word)
            # Filter out quotes and standalone punctuation
            # Also filter out punctuation-quote combinations
            filtered_parts = []
            for part in parts:
                # Skip standalone punctuation marks
                if part in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                    continue
                # Skip punctuation-quote combinations (like ?" ." !")
                if re.match(r'^[.!?]+["\']+$', part):
                    continue
                filtered_parts.append(part)
            tokens.extend(filtered_parts)

        # Filter out closing punctuation at the end of the token list
        # Remove trailing .!? tokens (even without quotes) - these are closing
        # punctuation that should remain in sentence text but not be tokenized
        while tokens and tokens[-1] in (".", "!", "?"):
            tokens.pop()

        return tokens

    @classmethod
    def _find_matched_token_ids(
        cls,
        existing_tokens: list[Token],
        token_strings: list[str],
    ) -> tuple[set[int], dict[int, Token]]:
        """
        When updating a sentence, find matched tokens in the existing tokens and
        the new token strings.  This is called by :meth:`update_from_sentence`.

        Args:
            existing_tokens: List of existing tokens
            token_strings: List of new token strings

        Returns:
            Dictionary of matched tokens
            The key is the position of the token in the new token strings,
            the value is the matched token.

        """
        # Build a mapping of position -> existing token for quick lookup
        position_to_token = {token.order_index: token for token in existing_tokens}
        # Track which existing tokens have been matched (by their id)
        matched_token_ids = set()

        matched_positions = {}
        for new_index, new_surface in enumerate(token_strings):
            if new_index in position_to_token:
                existing_token = position_to_token[new_index]
                if (
                    existing_token.surface == new_surface
                    and existing_token.id is not None
                ):
                    # Perfect match at same position - no changes needed
                    matched_positions[new_index] = existing_token
                    matched_token_ids.add(existing_token.id)

        return matched_token_ids, matched_positions

    @classmethod
    def _process_unmatched_tokens(  # noqa: PLR0913
        cls,
        session,
        existing_tokens: list[Token],
        matched_token_ids: set[int],
        matched_positions: dict[int, Token],
        token_strings: list[str],
        sentence_id: int,
    ) -> None:
        """
        Process unmatched tokens when updating a sentence.  Save the new tokens
        and update the existing tokens.  This is called by
        :meth:`update_from_sentence`.

        Args:
            session: SQLAlchemy session
            existing_tokens: List of existing tokens
            matched_token_ids: Set of matched token IDs
            matched_positions: Dictionary of matched positions
            token_strings: List of new token strings
            sentence_id: Sentence ID

        """
        unmatched_existing = [
            token
            for token in existing_tokens
            if token.id is not None and token.id not in matched_token_ids
        ]

        # First, move all unmatched existing tokens to temporary positions to avoid
        # conflicts when renumbering. Use negative offsets to avoid conflicts.
        temp_offset = -(len(existing_tokens) + len(token_strings))
        for token in unmatched_existing:
            if token.id is not None:
                token.order_index = temp_offset
                session.add(token)
                temp_offset += 1
        session.flush()

        # Iterate over the new token strings and try to match them to existing
        # tokens
        for new_index, new_surface in enumerate(token_strings):
            if new_index not in matched_positions:
                # Try to find an unmatched existing token with matching surface
                matched = False
                for existing_token in unmatched_existing:
                    if (
                        existing_token.surface == new_surface
                        and existing_token.id is not None
                    ):
                        # Match found - use this existing token
                        matched_positions[new_index] = existing_token
                        matched_token_ids.add(existing_token.id)
                        unmatched_existing.remove(existing_token)
                        # Update order_index and surface (in case surface changed)
                        # Safe to update now since we moved all tokens to temp positions
                        existing_token.order_index = new_index
                        existing_token.surface = new_surface
                        session.add(existing_token)
                        matched = True
                        break

                if not matched:
                    # No match found - create a new token
                    new_token = cls(
                        sentence_id=sentence_id,
                        order_index=new_index,
                        surface=new_surface,
                    )
                    session.add(new_token)
                    session.flush()  # Get the ID

                    existing_annotation = session.scalar(
                        select(Annotation).where(Annotation.token_id == new_token.id)
                    )
                    if not existing_annotation:
                        annotation = Annotation(token_id=new_token.id)
                        session.add(annotation)

                    matched_positions[new_index] = new_token
        session.flush()

    @classmethod
    def update_from_sentence(
        cls, session, sentence_text: str, sentence_id: int
    ) -> None:
        """
        Update all the tokens in the sentence, removing any tokens that are no
        longer in the sentence, and adding any new tokens.

        We will also re-order the tokens to match the order of the tokens in the
        sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`update` taking a token id
        or surface, it takes the sentence text and sentence id.

        Our here is to update the text of the sentence without losing any
        annotations on the tokens that need to remain.

        The algorithm handles duplicate tokens (e.g., multiple instances of "þā"
        or "him") by matching them positionally and by surface, ensuring each
        existing token is matched at most once.

        Args:
            session: SQLAlchemy session
            sentence_text: Text of the sentence to tokenize
            sentence_id: Sentence ID

        """
        token_strings = cls.tokenize(sentence_text)
        # Get existing tokens using SQLAlchemy query
        stmt = (
            select(cls).where(cls.sentence_id == sentence_id).order_by(cls.order_index)
        )
        existing_tokens = list(session.scalars(stmt).all())

        # First pass: Try to match tokens at the same position with same surface
        # This preserves tokens that haven't moved
        matched_token_ids, matched_positions = cls._find_matched_token_ids(
            existing_tokens, token_strings
        )
        # Second pass: For unmatched positions, try to find an unmatched
        # existing token with matching surface. This handles cases where tokens
        # have been reordered or where duplicates exist.
        cls._process_unmatched_tokens(
            session,
            existing_tokens,
            matched_token_ids,
            matched_positions,
            token_strings,
            sentence_id,
        )

        # Third pass: Delete tokens that weren't matched (they no longer exist
        # in the sentence)
        for token in existing_tokens:
            if token.id and token.id not in matched_token_ids:
                session.delete(token)

        # Fourth pass: Ensure all matched tokens have the correct order_index
        # (This handles any edge cases where order_index might be inconsistent)
        for new_index in range(len(token_strings)):
            if new_index in matched_positions:
                token = matched_positions[new_index]
                if token.order_index != new_index:
                    token.order_index = new_index
                    session.add(token)

        session.flush()

        # Final pass: Ensure every position has a token and all tokens are
        # numbered sequentially. This catches any inconsistencies and ensures
        # proper sequential numbering.
        if len(matched_positions) != len(token_strings):
            # This should not happen, but if it does, we need to handle it
            msg = (
                f"Position count mismatch: expected {len(token_strings)} "
                f"positions, found {len(matched_positions)} in matched_positions"
            )
            raise ValueError(msg)
        # Ensure all tokens are numbered sequentially (0, 1, 2, ...)
        # This handles any edge cases where order_index might be inconsistent
        for new_index in range(len(token_strings)):
            if new_index not in matched_positions:
                msg = f"Missing token at position {new_index}"
                raise ValueError(msg)
            token = matched_positions[new_index]
            # Reload token from DB to get latest state (in case it was updated
            # elsewhere)
            if token.id is not None:
                session.refresh(token)
            if token.order_index != new_index:
                token.order_index = new_index
                session.add(token)

        session.commit()
