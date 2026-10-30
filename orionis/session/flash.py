from __future__ import annotations
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from orionis.session.contracts.session import ISession

# Reserved flash-bag keys owned by the framework.  Application code must
# never write them directly; use ``withInput()`` / ``withErrors()`` instead.
OLD_INPUT_KEY: str = "_old_input"
ERRORS_KEY: str = "_errors"

# Reserved session key holding the last page the user navigated to.
PREVIOUS_URL_KEY: str = "_previous_url"

# Never carried over when repopulating a form.
SENSITIVE_INPUT_FIELDS: frozenset[str] = frozenset(
    {
        "_csrf",
        "csrf_token",
        "current_password",
        "new_password",
        "password",
        "password_confirmation",
    },
)

# Hoisted so the isinstance check does not rebuild the tuple on every field.
_SEQUENCE_TYPES: tuple[type, ...] = (list, tuple, set, frozenset)

def filter_input(values: Mapping[str, Any]) -> dict[str, Any]:
    """
    Drop credential-like fields from a form payload before flashing it.

    Parameters
    ----------
    values : Mapping[str, Any]
        Raw submitted payload.

    Returns
    -------
    dict[str, Any]
        Copy of *values* without any field listed in
        :data:`SENSITIVE_INPUT_FIELDS`.
    """
    # Most payloads carry no credential field at all: copy them wholesale.
    if SENSITIVE_INPUT_FIELDS.isdisjoint(values):
        return dict(values)

    return {
        key: value for key, value in values.items() if key not in SENSITIVE_INPUT_FIELDS
    }

def normalize_errors(errors: object) -> dict[str, list[str]]:  # NOSONAR
    """
    Normalize validation errors into field-indexed message lists.

    Parameters
    ----------
    errors : object
        Mapping of messages or ``{rule, message}`` details, or an exception
        exposing ``errors`` or ``failure``.

    Returns
    -------
    dict[str, list[str]]
        String messages grouped by field, with structured rule codes omitted.

    Raises
    ------
    TypeError
        If *errors* is neither a mapping nor a validation exception.
    """
    # Duck-typed so the session layer never imports the schemas package.
    if not isinstance(errors, Mapping):
        bag = getattr(errors, "errors", None)
        if isinstance(bag, Mapping):
            return normalize_errors(bag)

        failure = getattr(errors, "failure", None)
        if failure is not None:
            field = getattr(failure, "field", "") or ""
            message = getattr(failure, "message", "") or ""
            return {field: [message]}

        error_msg = (
            "errors must be a mapping of field to message(s) or a validation exception"
        )
        raise TypeError(error_msg)

    normalized: dict[str, list[str]] = {}
    for field, value in errors.items():
        if isinstance(value, str):
            normalized[field] = [value]
        elif isinstance(value, _SEQUENCE_TYPES):
            normalized[field] = [
                str(item["message"])
                if isinstance(item, Mapping) and "message" in item
                else str(item)
                for item in value
            ]
        elif isinstance(value, Mapping) and "message" in value:
            normalized[field] = [str(value["message"])]
        else:
            normalized[field] = [str(value)]
    return normalized

def queue_bag(
    flash: dict[str, Any],
    key: str,
    values: Mapping[str, Any],
) -> None:
    """
    Merge *values* into the reserved bag *key* of a pending flash payload.

    Parameters
    ----------
    flash : dict[str, Any]
        Pending flash payload owned by a response or a pending view.
    key : str
        Reserved bag key.
    values : Mapping[str, Any]
        Entries to merge into the bag.

    Returns
    -------
    None
    """
    current = flash.get(key)
    if isinstance(current, dict):
        current.update(values)
    else:
        flash[key] = dict(values)

def apply_flash(session: ISession, data: Mapping[str, Any]) -> None:
    """
    Write a pending flash payload into the session.

    Reserved bags are routed through their dedicated session methods so
    they merge with anything already flashed during this request instead
    of replacing it.

    Parameters
    ----------
    session : ISession
        Session receiving the flashed values.
    data : Mapping[str, Any]
        Pending flash payload.

    Returns
    -------
    None
    """
    for key, value in data.items():
        if key == OLD_INPUT_KEY:
            session.flashInput(value)
        elif key == ERRORS_KEY:
            session.flashErrors(value)
        else:
            session.flash(key, value)

class _FlashData:
    """Queue flash payloads for responses and deferred views.

    Owners initialize the slot and decide when to apply it to the session.
    Pending views apply it before rendering; responses apply it during dispatch.
    """

    __slots__ = ("_flash",)
    _flash: dict[str, Any] | None

    # ruff: noqa: ANN401

    def withFlash(self: Self, key: str, value: Any | None = None) -> Self:
        """
        Queue a status message for the owning response or pending view.

        The value survives for exactly one subsequent request and is read
        back in templates through the ``flash()`` global.

        Parameters
        ----------
        key : str
            Flash data key.
        value : Any, optional
            Value to flash.

        Returns
        -------
        Self
            The same owner, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        flash[key] = value
        return self

    def withInput(self: Self, values: Mapping[str, Any]) -> Self:
        """
        Flash the submitted payload so the next request can repopulate it.

        Values are read back in templates through the ``old()`` global.
        Credential-like fields such as ``password`` are stripped.

        Parameters
        ----------
        values : Mapping[str, Any]
            Submitted form payload to remember.

        Returns
        -------
        Self
            The same owner, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        queue_bag(flash, OLD_INPUT_KEY, filter_input(values))
        return self

    def withErrors(self: Self, errors: Mapping[str, Any] | Exception) -> Self:
        """
        Flash validation errors for the next request.

        Errors are read back in templates through the ``errors`` global.

        Parameters
        ----------
        errors : Mapping[str, Any] | Exception
            Mapping of field to message(s), or a validation exception.

        Returns
        -------
        Self
            The same owner, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        queue_bag(flash, ERRORS_KEY, normalize_errors(errors))
        return self
