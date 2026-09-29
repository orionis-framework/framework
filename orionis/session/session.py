from __future__ import annotations
import secrets
from typing import TYPE_CHECKING, Any
from orionis.session.contracts.session import ISession
from orionis.session.flash import (
    ERRORS_KEY,
    OLD_INPUT_KEY,
    PREVIOUS_URL_KEY,
    filter_input,
    normalize_errors,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

# Flash-bag keys defined at module level to avoid per-call string allocation.
_FLASH_NEW: str = "_flash_new"
_FLASH_OLD: str = "_flash_old"
_MISSING: object = object()
_IMMUTABLE_VALUE_TYPES = frozenset({type(None), bool, bytes, float, int, str})

class Session(ISession):
    """
    Runtime representation of a single HTTP session.

    The session is **lazy**: no identifier is generated and no record is
    persisted until the application writes at least one value via
    ``put()`` or ``flash()``.  The ``SessionManager`` inspects the
    ``started`` and ``dirty`` flags to decide whether persistence and a
    ``Set-Cookie`` header are required.

    Attributes
    ----------
    _id : str | None
        Unique session identifier; ``None`` until first activation.
    _data : dict[str, Any]
        In-memory key-value payload.
    _started : bool
        ``True`` once the session has been activated by any write.
    _dirty : bool
        ``True`` when the in-memory session state must be persisted before
        the response is sent.
    _invalidated : bool
        ``True`` when the session should be fully deleted.
    _is_new : bool
        ``True`` for sessions that were not restored from a store.
    _regenerate : bool
        ``True`` when the ID must be rotated before the next save.
    _renew_at : datetime | None
        Deadline for renewing an unchanged scalar payload. ``None`` requires
        persistence because no deadline is known or mutable data is present.

    Notes
    -----
    This class must **never** interact directly with ``Request``,
    ``Response``, or any ``ISessionStore``.  All I/O is the
    responsibility of the ``SessionManager``.
    """

    __slots__ = (
        "_data",
        "_dirty",
        "_id",
        "_invalidated",
        "_is_new",
        "_regenerate",
        "_renew_at",
        "_started",
    )

    def __init__(
        self,
        id: str | None = None,  # noqa: A002
        data: dict[str, Any] | None = None,
        *,
        started: bool = False,
        is_new: bool = True,
    ) -> None:
        """
        Initialise a session instance.

        Parameters
        ----------
        id : str | None, optional
            Session identifier.  Pass ``None`` for a brand-new session
            (lazy activation generates the ID on the first write).
        data : dict[str, Any] | None, optional
            Initial session data.  Defaults to an empty dictionary.
        started : bool, optional
            ``True`` when the session was loaded from a backing store.
        is_new : bool, optional
            ``False`` for sessions restored from a backing store.

        Returns
        -------
        None
        """
        self._id: str | None = id
        self._data: dict[str, Any] = data if data is not None else {}
        self._started: bool = started
        self._dirty: bool = False
        self._invalidated: bool = False
        self._is_new: bool = is_new
        self._regenerate: bool = False
        self._renew_at: datetime | None = None

    # ── Internal activation ─────────────────────────────────────────────────────

    def __activate(self) -> None:
        """
        Ensure the session has an identifier and is marked active.

        Called automatically on the first write.  Idempotent: safe to
        call multiple times.

        Returns
        -------
        None
        """
        # token_urlsafe(32) produces 43 URL-safe characters (~192 bits).
        if self._id is None:
            self._id = secrets.token_urlsafe(32)
        self._started = True

    # ── Read-only properties ────────────────────────────────────────────────────

    @property
    def id(self) -> str | None:
        """
        Return the current session identifier.

        Returns
        -------
        str | None
            Identifier, or None before the first write.
        """
        return self._id

    @property
    def started(self) -> bool:
        """
        Report whether the session has been activated.

        Returns
        -------
        bool
            True after activation by a write or restoration from the store.
        """
        return self._started

    @property
    def dirty(self) -> bool:
        """
        Report whether changes require persistence.

        Returns
        -------
        bool
            True when tracked changes must be written to the backing store.
        """
        return self._dirty

    @property
    def invalidated(self) -> bool:
        """
        Report whether the session has been invalidated.

        Returns
        -------
        bool
            True when the session is marked for full deletion.
        """
        return self._invalidated

    @property
    def isNew(self) -> bool:
        """
        Report whether the session has a new storage identity.

        Returns
        -------
        bool
            True for sessions not yet persisted under their current identifier.
        """
        return self._is_new

    @property
    def wantsRegenerate(self) -> bool:
        """
        Report whether the session requests identifier rotation.

        Returns
        -------
        bool
            True when the identifier should be rotated before saving.
        """
        return self._regenerate

    # ── Public API ──────────────────────────────────────────────────────────────

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
        return self._data.get(key, default)

    def put(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Store *value* under *key*, activating the session on the first call.

        No-op when *key* already holds a value equal to *value*, avoiding
        unnecessary dirty-marking and store writes.

        Parameters
        ----------
        key : str
            Session data key.
        value : Any
            Value to store.  Must be JSON-serialisable when using the
            file backing store.

        Returns
        -------
        None
        """
        current = self._data.get(key, _MISSING)
        if current is not _MISSING and current == value:
            return
        if not self._started:
            self.__activate()
        self._data[key] = value
        self._dirty = True

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
        return key in self._data

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
        if self._data.pop(key, _MISSING) is not _MISSING and self._started:
            self._dirty = True

    def clear(self) -> None:
        """
        Remove all data from this session.

        Returns
        -------
        None
        """
        if self._data:
            self._data.clear()
            if self._started:
                self._dirty = True

    def flash(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Store *value* under *key* for exactly one subsequent request.

        No-op when *key* already holds the same flash value, avoiding
        unnecessary dirty-marking and store writes.

        Flash data is readable via ``getFlash()`` for the rest of this
        request and the next one, and is discarded by ``_ageFlashData()``
        at the start of the request after that.

        Parameters
        ----------
        key : str
            Flash data key.
        value : Any
            Flash data value.  Must be JSON-serialisable.

        Returns
        -------
        None
        """
        flash_bag = self._data.get(_FLASH_NEW)
        if flash_bag is None:
            if not self._started:
                self.__activate()
            self._data[_FLASH_NEW] = {key: value}
            self._dirty = True
            return

        current = flash_bag.get(key, _MISSING)
        if current is not _MISSING and current == value:
            return
        if not self._started:
            self.__activate()
        flash_bag[key] = value
        self._dirty = True

    def getFlash(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return the flash value for *key*.

        Values flashed during the current request take precedence over the
        ones inherited from the previous one, so a handler that re-renders
        its own view reads back what it just flashed instead of having to
        redirect first.

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
        new_flash = self._data.get(_FLASH_NEW)
        if new_flash is not None and key in new_flash:
            return new_flash[key]

        old_flash = self._data.get(_FLASH_OLD)
        return old_flash.get(key, default) if old_flash is not None else default

    def __mergeReservedBag(
        self,
        key: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge *values* with the reserved bag already flashed in this request.

        Only the *new* flash bag is consulted so values inherited from the
        previous request never leak into the one being written.

        Parameters
        ----------
        key : str
            Reserved bag key.
        values : dict[str, Any]
            Entries to merge into the bag.

        Returns
        -------
        dict[str, Any]
            The resulting bag content.
        """
        new_flash = self._data.get(_FLASH_NEW)
        current = new_flash.get(key) if new_flash is not None else None
        if isinstance(current, dict):
            merged = dict(current)
            merged.update(values)
            return merged
        return values

    def flashInput(self, values: Mapping[str, Any]) -> None:
        """
        Flash a submitted form payload so the next request can repopulate it.

        Credential-like fields are stripped before storing.  Repeated calls
        during the same request merge instead of replacing.

        Parameters
        ----------
        values : Mapping[str, Any]
            Submitted payload to remember.

        Returns
        -------
        None
        """
        self.flash(
            OLD_INPUT_KEY,
            self.__mergeReservedBag(OLD_INPUT_KEY, filter_input(values)),
        )

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
        bag = self.getFlash(OLD_INPUT_KEY)
        return bag.get(key, default) if isinstance(bag, dict) else default

    def flashErrors(self, errors: Mapping[str, Any] | Exception) -> None:
        """
        Flash validation errors for the next request.

        Repeated calls during the same request merge instead of replacing.

        Parameters
        ----------
        errors : Mapping[str, Any] | Exception
            Mapping of field to message(s), or a validation exception.

        Returns
        -------
        None
        """
        self.flash(
            ERRORS_KEY,
            self.__mergeReservedBag(ERRORS_KEY, normalize_errors(errors)),
        )

    def getErrors(self) -> dict[str, list[str]]:
        """
        Return the validation errors flashed for this request.

        Returns
        -------
        dict[str, list[str]]
            Field-indexed error messages, empty when none were flashed.
        """
        bag = self.getFlash(ERRORS_KEY)
        return bag if isinstance(bag, dict) else {}

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
        self.put(PREVIOUS_URL_KEY, url)

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
        return self.get(PREVIOUS_URL_KEY, default)

    def regenerate(self) -> None:
        """
        Request a session ID rotation (e.g. immediately after login).

        The actual ID swap is performed by the ``SessionManager`` during
        the save phase so the old record can be deleted atomically.

        Returns
        -------
        None
        """
        self._regenerate = True
        self._invalidated = False
        if not self._started:
            self.__activate()
        self._dirty = True

    def invalidate(self) -> None:
        """
        Mark the session for full deletion and clear in-memory data.

        The backing-store record will be removed and the cookie cleared
        when ``SessionManager`` processes the outgoing response.

        Returns
        -------
        None
        """
        self._data.clear()
        self._invalidated = True
        self._dirty = True
        self._regenerate = False

    def all(self) -> dict[str, Any]:
        """Return a shallow copy of the current session data.

        Returns
        -------
        dict[str, Any]
            Copy of all session key-value pairs including internal flash bags.
        """
        return dict(self._data)

    # ── Framework-internal methods (prefixed with _) ────────────────────────────

    def _setRenewalDeadline(self, deadline: datetime) -> None:
        """
        Set a renewal deadline for payloads containing immutable scalars.

        Mutable values can be changed through references returned by ``get()``
        or ``all()`` without setting the dirty flag. Such payloads retain
        unconditional persistence, including tuples with mutable descendants.

        Parameters
        ----------
        deadline : datetime
            UTC time at which an unchanged session needs renewal.

        Returns
        -------
        None
            The session retains only the deadline, never request state.
        """
        for value in self._data.values():
            if type(value) not in _IMMUTABLE_VALUE_TYPES:
                self._renew_at = None
                return
        self._renew_at = deadline

    def _needsPersistence(self, now: datetime) -> bool:
        """
        Check whether payload changes or the renewal deadline require a save.

        Parameters
        ----------
        now : datetime
            Current UTC time evaluated when the response is ready.

        Returns
        -------
        bool
            Whether to persist this session and refresh its cookie.
        """
        return (
            self._dirty or self._is_new or self._regenerate
            or self._renew_at is None or now >= self._renew_at
        )

    def _ageFlashData(self) -> None:
        """
        Advance the flash lifecycle: new → old; discard previous old.

        Called by ``SessionManager.start()`` at the beginning of each
        request.  Flash values written in the previous request remain
        readable via ``getFlash()`` and are removed after this request.

        Sets ``_dirty`` when the flash state changes so the aged layout
        is persisted even if the request handler makes no further writes.
        Idle sessions without any flash data are not affected.

        Returns
        -------
        None
        """
        new_flash = self._data.pop(_FLASH_NEW, None)
        had_old = self._data.pop(_FLASH_OLD, None) is not None
        if new_flash is not None:
            self._data[_FLASH_OLD] = new_flash
        if new_flash is not None or had_old:
            self._dirty = True

    def _rotateId(self) -> str | None:
        """
        Assign a fresh identifier and return the previous one.

        Called by ``SessionManager`` during the ID rotation phase so
        the manager can delete the old backing-store record before
        persisting under the new identifier.  All ID generation remains
        inside ``Session``.

        Returns
        -------
        str | None
            The identifier that was active before the rotation, or
            ``None`` when the session had no identifier yet.
        """
        old_id = self._id
        self._id = secrets.token_urlsafe(32)
        self._is_new = True
        self._regenerate = False
        self._dirty = True
        return old_id

    def _markClean(self) -> None:
        """
        Reset the dirty flag after a successful persistence operation.

        Returns
        -------
        None
        """
        self._dirty = False
        self._is_new = False
