from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

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

    # ── Read-only properties ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def id(self) -> str | None:
        """Current session identifier, or ``None`` before the first write."""

    @property
    @abstractmethod
    def started(self) -> bool:
        """``True`` once the session has been activated by a write."""

    @property
    @abstractmethod
    def dirty(self) -> bool:
        """``True`` if pending changes must be written to the backing store."""

    @property
    @abstractmethod
    def invalidated(self) -> bool:
        """``True`` when the session has been marked for full deletion."""

    @property
    @abstractmethod
    def isNew(self) -> bool:
        """``True`` for sessions not loaded from a backing store."""

    @property
    @abstractmethod
    def wantsRegenerate(self) -> bool:
        """``True`` when the session ID should be rotated before saving."""

    # ── Public API ──────────────────────────────────────────────────────────────

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return the value for *key*, or *default* when absent.

        Parameters
        ----------
        key : str
            Session data key.
        default : Any, optional
            Fallback value returned when *key* is not found.

        Returns
        -------
        Any
            The stored value, or *default*.
        """

    @abstractmethod
    def put(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Store *value* under *key*, activating the session on the first call.

        Parameters
        ----------
        key : str
            Session data key.
        value : Any
            Value to store.

        Returns
        -------
        None
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
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all data from this session.

        Returns
        -------
        None
        """

    @abstractmethod
    def flash(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Store *value* under *key* for exactly one subsequent request.

        Parameters
        ----------
        key : str
            Flash data key.
        value : Any
            Flash data value.

        Returns
        -------
        None
        """

    @abstractmethod
    def getFlash(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return the flash value for *key*.

        Values flashed during the current request take precedence over the
        ones inherited from the previous one.

        Parameters
        ----------
        key : str
            Flash data key.
        default : Any, optional
            Fallback value when the key is absent from both bags.

        Returns
        -------
        Any
            The flash value, or *default*.
        """

    @abstractmethod
    def flashInput(self, values: Mapping[str, Any]) -> None:
        """
        Flash a submitted form payload so the next request can repopulate it.

        Parameters
        ----------
        values : Mapping[str, Any]
            Submitted payload to remember.  Credential-like fields are
            stripped before storing.

        Returns
        -------
        None
        """

    @abstractmethod
    def getOldInput(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return the value submitted for *key* in the previous request.

        Parameters
        ----------
        key : str
            Form field name.
        default : Any, optional
            Fallback value when the field was not submitted.

        Returns
        -------
        Any
            The previously submitted value, or *default*.
        """

    @abstractmethod
    def flashErrors(self, errors: Mapping[str, Any] | Exception) -> None:
        """
        Flash validation errors for the next request.

        Parameters
        ----------
        errors : Mapping[str, Any] | Exception
            Mapping of field to message(s), or a validation exception.

        Returns
        -------
        None
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
        """

    @abstractmethod
    def invalidate(self) -> None:
        """
        Mark the session for full deletion and clear in-memory data.

        Returns
        -------
        None
        """

    @abstractmethod
    def all(self) -> dict[str, Any]:
        """
        Return a shallow copy of the current session data.

        Returns
        -------
        dict[str, Any]
            Copy of all session key-value pairs including internal flash bags.
        """
