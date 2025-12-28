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
