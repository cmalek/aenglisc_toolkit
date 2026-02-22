"""Idiom model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.utils import from_utc_iso, to_utc_iso

from .mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class Idiom(SaveDeleteMixin, Base):
    """Represents a multi-token group (idiom) in a sentence."""

    __tablename__ = "idioms"
    __table_args__ = (
        Index(
            "idx_idioms_sentence_token_span",
            "sentence_id",
            "start_token_id",
            "end_token_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The start token ID for the idiom in the sentence.
    start_token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    #: The end token ID for the idiom in the sentence.
    end_token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    #: The date and time the idiom was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the idiom was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    sentence: Mapped["Sentence"] = relationship("Sentence", back_populates="idioms")
    start_token: Mapped["Token"] = relationship("Token", foreign_keys=[start_token_id])
    end_token: Mapped["Token"] = relationship("Token", foreign_keys=[end_token_id])
    annotation: Mapped["Annotation | None"] = relationship(
        "Annotation",
        back_populates="idiom",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @classmethod
    def get(cls, idiom_id: int) -> "Idiom | None":
        """
        Get an idiom by ID.

        Args:
            idiom_id: ID of the idiom

        Returns:
            Idiom or None if not found

        """
        session = cls._get_session()
        return session.get(cls, idiom_id)

    @classmethod
    def create(
        cls,
        sentence_id: int,
        start_token_id: int,
        end_token_id: int,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> "Idiom":
        """
        Create a new idiom.

        Args:
            sentence_id: Sentence ID
            start_token_id: Start token ID
            end_token_id: End token ID
            commit: Whether to commit the changes to the database

        Returns:
            The new :class:`~oeapp.models.idiom.Idiom` object

        """
        session = cls._get_session()
        idiom = cls(
            sentence_id=sentence_id,
            start_token_id=start_token_id,
            end_token_id=end_token_id,
        )
        session.add(idiom)
        if commit:
            session.commit()
        session.refresh(idiom)
        return idiom

    def save(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Save the idiom.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        super().save(commit=commit)
        logger.info(
            "idiom.saved",
            project_id=self.sentence.project_id,
            project_name=self.sentence.project.name,
            sentence_id=self.sentence_id,
            sentence_number=self.sentence.display_order,
            idiom_id=self.id,
            text=self.sentence.get_token_surfaces(
                self.start_token.id,
                self.end_token.id,
            ),
        )

    def delete(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Delete the idiom.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)
        super().delete(commit=commit)
        if commit:
            logger.info(
                "idiom.deleted",
                idiom_id=self.id,
                project_id=self.sentence.project_id,
                sentence_id=self.sentence_id,
                text=self.sentence.get_token_surfaces(
                    self.start_token.id,
                    self.end_token.id,
                ),
            )

    def to_json(self) -> dict:
        """
        Serialize idiom to JSON-compatible dictionary (without PKs).

        Returns:
            Dictionary containing idiom data

        """
        idiom_data: dict = {
            "start_token_order_index": self.start_token.order_index,
            "end_token_order_index": self.end_token.order_index,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }
        if self.annotation:
            idiom_data["annotation"] = self.annotation.to_json()
        return idiom_data

    @classmethod
    def from_json(
        cls,
        sentence_id: int,
        idiom_data: dict,
        token_map: dict[int, "Token"],
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> "Idiom":
        """
        Create idiom from JSON import data.

        Args:
            sentence_id: Sentence ID to attach idiom to
            idiom_data: Idiom data dictionary from JSON
            token_map: Map of order_index to Token entities

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Created idiom

        """
        # Import here to avoid circular import
        from oeapp.models.annotation import Annotation  # noqa: PLC0415

        start_order = idiom_data["start_token_order_index"]
        end_order = idiom_data["end_token_order_index"]
        start_token = token_map.get(start_order)
        end_token = token_map.get(end_order)
        if start_token is None or end_token is None:
            msg = (
                "Unable to resolve idiom token references for order indices "
                f"{start_order}..{end_order}"
            )
            raise ValueError(msg)
        if start_token.id is None or end_token.id is None:
            msg = "Idiom token references do not have database IDs"
            raise ValueError(msg)

        session = cls._get_session()
        idiom = cls(
            sentence_id=sentence_id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )
        created_at = from_utc_iso(idiom_data.get("created_at"))
        if created_at:
            idiom.created_at = created_at
        updated_at = from_utc_iso(idiom_data.get("updated_at"))
        if updated_at:
            idiom.updated_at = updated_at

        session.add(idiom)
        session.flush()

        if "annotation" in idiom_data:
            Annotation.from_json(
                None,
                idiom_data["annotation"],
                idiom_id=idiom.id,
                commit=False,
            )

        if commit:
            session.commit()
        else:
            session.flush()

        return idiom
