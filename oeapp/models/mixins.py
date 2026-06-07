from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SessionMixin:
    """Mixin for models that need a session."""

    @classmethod
    def _get_session(cls) -> "Session":
        """
        Get the session from the application state.

        Returns:
            SQLAlchemy session

        """
        from oeapp.db import get_runtime_session  # noqa: PLC0415

        return get_runtime_session()


class SaveDeleteMixin(SessionMixin):
    """Mixin for models that need to save and delete."""

    def save(self, commit: bool = True) -> None:
        """
        Save the model.

        Keyword Args:
            commit: Whether to commit the changes

        """
        session = self._get_session()
        session.add(self)
        if commit:
            session.commit()
        else:
            session.flush()
        session.refresh(self)

    def delete(self, commit: bool = True) -> None:
        """
        Delete the model.

        Keyword Args:
            commit: Whether to commit the changes

        Raises:
            DoesNotExist: If model does not exist

        """
        session = self._get_session()
        session.delete(self)
        session.flush()
        if commit:
            session.commit()
