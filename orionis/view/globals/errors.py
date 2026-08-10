from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.session.contracts.session import ISession

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

# Returned when no session is reachable, so templates never blow up.
_EMPTY: dict[str, list[str]] = {}

class ErrorBag:
    """
    Read-only view over the validation errors flashed for this request.

    Exposed to templates as the ``errors`` global.  Every method is a
    coroutine, which Jinja2 awaits transparently in async environments::

        {% if errors.any() %}{{ errors.first('email') }}{% endif %}
    """

    __slots__ = ("_app",)

    def __init__(self, app: IApplication) -> None:
        """
        Bind the bag to the application container.

        Parameters
        ----------
        app : IApplication
            Application container used for service resolution.

        Returns
        -------
        None
        """
        self._app = app

    async def __resolve(self) -> dict[str, list[str]]:
        """
        Return the flashed error mapping, or an empty mapping.

        Returns
        -------
        dict[str, list[str]]
            Field-indexed error messages.
        """
        try:
            session: ISession = await self._app.make(ISession)
        except Exception:
            return _EMPTY
        return session.getErrors()

    async def all(self) -> dict[str, list[str]]:
        """
        Return every error grouped by field.

        Returns
        -------
        dict[str, list[str]]
            Field-indexed error messages.
        """
        return await self.__resolve()

    async def any(self) -> bool:
        """
        Report whether at least one field failed validation.

        Returns
        -------
        bool
            ``True`` when the bag holds any message.
        """
        return bool(await self.__resolve())

    async def has(self, field: str) -> bool:
        """
        Report whether *field* has at least one error.

        Parameters
        ----------
        field : str
            Form field name.

        Returns
        -------
        bool
            ``True`` when the field failed validation.
        """
        return bool((await self.__resolve()).get(field))

    async def get(self, field: str) -> list[str]:
        """
        Return every message recorded for *field*.

        Parameters
        ----------
        field : str
            Form field name.

        Returns
        -------
        list[str]
            Messages for the field, empty when it is valid.
        """
        return (await self.__resolve()).get(field, [])

    async def first(self, field: str | None = None) -> str:
        """
        Return the first message for *field*, or the first of any field.

        Parameters
        ----------
        field : str | None, optional
            Form field name.  When omitted, the first message of the whole
            bag is returned, which suits a single summary line.

        Returns
        -------
        str
            The message, or an empty string when there is none.
        """
        errors = await self.__resolve()

        if field is not None:
            messages = errors.get(field)
            return messages[0] if messages else ""

        for messages in errors.values():
            if messages:
                return messages[0]
        return ""

def _global_errors(app: IApplication) -> Any:
    """
    Build the ``errors`` template global.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Bag exposing the validation errors flashed for this request.
    """
    return ErrorBag(app)
