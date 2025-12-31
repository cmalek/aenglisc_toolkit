from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SessionMixin:
    """Mixin for models that need a session."""

    @classmethod
    def _get_session(cls) -> Session:
        """
        Get the session from the application state.

        Returns:
            SQLAlchemy session

        """
        # Avoid circular import
        from oeapp.state import ApplicationState  # noqa: PLC0415

        state = ApplicationState()
        assert state.session is not None, "Session is not set"  # noqa: S101
        return state.session


class SaveDeleteMixin(SessionMixin):
    """Mixin for models that need to save and delete."""

    def save(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Save the model.

        Keyword Args:
            commit: Whether to commit the changes

        """
        session = self._get_session()
        session.add(self)
        session.flush()
        if commit:
            session.commit()

    def delete(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
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
