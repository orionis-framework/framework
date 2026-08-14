from __future__ import annotations
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.session.contracts.session import ISession

# Reserved flash-bag keys owned by the framework.  Application code must
# never write them directly; use ``withInput()`` / ``withErrors()`` instead.
OLD_INPUT_KEY: str = "_old_input"
ERRORS_KEY: str = "_errors"

# Reserved session key holding the last page the user navigated to.
PREVIOUS_URL_KEY: str = "_previous_url"

# Never carried over when repopulating a form.
SENSITIVE_INPUT_FIELDS: frozenset[str] = frozenset({
    "_csrf",
    "csrf_token",
    "current_password",
    "new_password",
    "password",
    "password_confirmation",
})

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
        key: value
        for key, value in values.items()
        if key not in SENSITIVE_INPUT_FIELDS
    }

def normalize_errors(errors: object) -> dict[str, list[str]]:
    """
    Coerce any supported error payload into ``{field: [message, ...]}``.

    Accepts a mapping of field to a single message or to a sequence of
    messages, or an exception exposing a ``failure`` attribute with
    ``field`` and ``message`` (e.g. ``ValidationException``).

    Parameters
    ----------
    errors : object
        Mapping of errors, or a validation exception.

    Returns
    -------
    dict[str, list[str]]
        Field-indexed error messages.

    Raises
    ------
    TypeError
        If *errors* is neither a mapping nor a validation exception.
    """
    # Duck-typed so the session layer never imports the schemas package.
    if not isinstance(errors, Mapping):
        bag = getattr(errors, "errors", None)
        if isinstance(bag, Mapping):
            return {field: list(messages) for field, messages in bag.items()}

        failure = getattr(errors, "failure", None)
        if failure is not None:
            field = getattr(failure, "field", "") or ""
            message = getattr(failure, "message", "") or ""
            return {field: [message]}

        error_msg = (
            "errors must be a mapping of field to message(s) "
            "or a validation exception"
        )
        raise TypeError(error_msg)

    normalized: dict[str, list[str]] = {}
    for field, value in errors.items():
        if isinstance(value, str):
            normalized[field] = [value]
        elif isinstance(value, _SEQUENCE_TYPES):
            normalized[field] = [str(item) for item in value]
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
