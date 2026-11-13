# ruff: noqa: BLE001, TC001
# Keep public callback and application annotations resolvable at runtime.
# Observe optional service failures centrally before returning a fallback.
"""Expose validation errors from the current request session."""

from __future__ import annotations

from orionis.foundation.contracts.application import IApplication
from orionis.session.contracts.session import ISession
from orionis.view._failures import capture_service_failure


class ErrorBag:
    """
    Expose validation errors from the current request session.

    Exposed to templates as the ``errors`` global.  Every method is a
    coroutine, which Jinja2 awaits transparently in async environments::

        {% if errors.any() %}{{ errors.first('email') }}{% endif %}
    """

    __slots__ = ("_app",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, app: IApplication) -> None:
        """
        Bind the bag to the application container.

        Parameters
        ----------
        app : orionis.IApplication
            Application container used for service resolution.

        Returns
        -------
        None
            No return value.
        """
        self._app = app
        """Application container used for service resolution."""

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
        except Exception as error:
            await capture_service_failure(error, ISession, app=self._app)
            return {}
        return session.getErrors()

    async def all(self) -> dict[str, list[str]]:
        """
        Return every error grouped by field.

        Returns
        -------
        dict[str, list[str]]
            Existing session mapping, or a new empty mapping without a session.
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
        return any((await self.__resolve()).values())

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


def _global_errors(app: IApplication) -> ErrorBag:
    """
    Build the ``errors`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    orionis.view.globals.errors.ErrorBag
        Bag exposing the validation errors flashed for this request.
    """
    return ErrorBag(app)
