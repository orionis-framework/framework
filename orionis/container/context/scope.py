# ruff: noqa: SLF001
# Bind module helpers directly to the context variable owned by ScopedContext.
"""Store the active dependency-injection scope in a context variable."""

from __future__ import annotations
import contextvars


class ScopedContext:
    """Store the active dependency-injection scope in a context variable."""

    _active_scope: contextvars.ContextVar[object | None] = contextvars.ContextVar(
        "x-orionis-container-context-scope",
        default=None,
    )
    """
    Define a context variable to hold the active scope. The default value is None,
    indicating no active scope.
    """

    @classmethod
    def getCurrentScope(cls) -> object | None:
        """
        Retrieve the current active scope.

        Returns
        -------
        object or None
            The current scope object if set, otherwise None.
        """
        # Get the current value of the active scope context variable.
        return cls._active_scope.get()

    @classmethod
    def setCurrentScope(cls, scope: object) -> contextvars.Token:
        """
        Set the current active scope.

        Parameters
        ----------
        scope : object
            The scope object to set as the current active scope.

        Returns
        -------
        ``contextvars.Token``
            A token representing the previous state of the context variable.
        """
        # Set the active scope and return the token for possible reset.
        return cls._active_scope.set(scope)

    @classmethod
    def reset(cls, token: contextvars.Token) -> None:
        """
        Reset the active scope to a previous state.

        Parameters
        ----------
        token : ``contextvars.Token``
            The token representing the previous state to restore.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Reset the active scope context variable to the state represented by token.
        cls._active_scope.reset(token)


# Define module-level functions for easier access to the ScopedContext methods.
get_current_scope = ScopedContext._active_scope.get
set_current_scope = ScopedContext._active_scope.set
reset_scope = ScopedContext._active_scope.reset
