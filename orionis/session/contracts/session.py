# ruff: noqa: ANN401, TC003
# Preserve arbitrary session payloads and runtime-resolvable contract annotations.
"""Contract for a single HTTP session runtime object."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class ISession(ABC):
    """
    Contract for a single HTTP session runtime object.

    Implementors manage an in-memory key-value payload, flash data for
    one-request-lifetime values, and state flags consumed by the
    ``SessionManager`` (``started``, ``dirty``, ``invalidated``).

    Notes
    -----
    Implementors must **never** interact directly with ``Request``,
    ``Response``, or any ``ISessionStore``.  All I/O is the
    responsibility of the ``SessionManager``.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # ── Read-only properties ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def id(self) -> str | None:
        """
        Return the current session identifier.

        Returns
        -------
        str | None
            Identifier, or None before activation.
        """

    @property
    @abstractmethod
    def started(self) -> bool:
        """
        Report whether the session has been activated.

        Returns
        -------
        bool
            True after activation or restoration from a store.
        """

    @property
    @abstractmethod
    def dirty(self) -> bool:
        """
        Report whether changes require persistence.

        Returns
        -------
        bool
            True when tracked changes require a backing-store write.
        """

    @property
    @abstractmethod
    def invalidated(self) -> bool:
        """
        Report whether the session has been invalidated.

        Returns
        -------
        bool
            True when the session is marked for full deletion.
        """

    @property
    @abstractmethod
    def isNew(self) -> bool:
        """
        Report whether the session has a new storage identity.

        Returns
        -------
        bool
            True until the current identifier has been persisted.
        """

    @property
    @abstractmethod
    def wantsRegenerate(self) -> bool:
        """
        Report whether the session requests identifier rotation.

        Returns
        -------
        bool
            True when the identifier should be rotated before saving.
        """

    # ── Public API ──────────────────────────────────────────────────────────────

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Return the value for *key*, or *default* when absent.

        Parameters
        ----------
        key : str
            Session data key.
        default : typing.Any, optional
            Fallback value returned when *key* is not found.

        Returns
        -------
        typing.Any
            The stored value, or *default*.
        """

    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """
        Store *value* under *key*, activating the session on the first call.

        Parameters
        ----------
        key : str
            Session data key.
        value : typing.Any
            Value to store.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Return ``True`` when *key* exists in the session data.

        Parameters
        ----------
        key : str
            Session data key.

        Returns
        -------
        bool
            ``True`` if the key is present.
        """

    @abstractmethod
    def forget(self, key: str) -> None:
        """
        Remove *key* from session data (no-op when absent).

        Parameters
        ----------
        key : str
            Session data key to remove.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all data from this session.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def flash(self, key: str, value: Any) -> None:
        """
        Store *value* under *key* for exactly one subsequent request.

        Parameters
        ----------
        key : str
            Flash data key.
        value : typing.Any
            Flash data value.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def getFlash(self, key: str, default: Any = None) -> Any:
        """
        Return the flash value for *key*.

        Values flashed during the current request take precedence over the
        ones inherited from the previous one.

        Parameters
        ----------
        key : str
            Flash data key.
        default : typing.Any, optional
            Fallback value when the key is absent from both bags.

        Returns
        -------
        typing.Any
            The flash value, or *default*.
        """

    @abstractmethod
    def flashInput(self, values: Mapping[str, Any]) -> None:
        """
        Flash a submitted form payload so the next request can repopulate it.

        Parameters
        ----------
        values : collections.abc.Mapping[str, typing.Any]
            Submitted payload to remember.  Credential-like fields are
            stripped before storing.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def getOldInput(self, key: str, default: Any = None) -> Any:
        """
        Return the value submitted for *key* in the previous request.

        Parameters
        ----------
        key : str
            Form field name.
        default : typing.Any, optional
            Fallback value when the field was not submitted.

        Returns
        -------
        typing.Any
            The previously submitted value, or *default*.
        """

    @abstractmethod
    def flashErrors(self, errors: Mapping[str, Any] | Exception) -> None:
        """
        Flash validation errors for the next request.

        Parameters
        ----------
        errors : collections.abc.Mapping[str, typing.Any] | Exception
            Mapping of field to message(s), or a validation exception.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def getErrors(self) -> dict[str, list[str]]:
        """
        Return the validation errors flashed for this request.

        Returns
        -------
        dict[str, list[str]]
            Field-indexed error messages, empty when none were flashed.
        """

    @abstractmethod
    def setPreviousUrl(self, url: str) -> None:
        """
        Remember the page the user is currently viewing.

        Parameters
        ----------
        url : str
            Absolute URL of the current page.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def getPreviousUrl(self, default: str | None = None) -> str | None:
        """
        Return the last page the user navigated to.

        Parameters
        ----------
        default : str | None, optional
            Fallback returned when no page has been recorded yet.

        Returns
        -------
        str | None
            The stored URL, or *default*.
        """

    @abstractmethod
    def regenerate(self) -> None:
        """
        Request a session ID rotation (e.g. immediately after login).

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def invalidate(self) -> None:
        """
        Mark the session for full deletion and clear in-memory data.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def all(self) -> dict[str, Any]:
        """
        Return a shallow copy of the current session data.

        Returns
        -------
        dict[str, typing.Any]
            Copy of all session key-value pairs including internal flash bags.
        """
