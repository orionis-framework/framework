import asyncio
import socket
from urllib.parse import urlsplit
from orionis.schemas.rule import Rule

class ActiveUrl(Rule):
    """
    Ensure a URL points at a hostname that currently resolves.

    The hostname is extracted from the URL and looked up through the system
    resolver, so the check succeeds only when an ``A`` or ``AAAA`` record
    exists. The lookup blocks the calling thread.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be a URL with a resolvable hostname."
    __code__ = "active_url"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as an active URL.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Owning object instance. This argument is accepted for
            interface compatibility.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        # Leave non-string values to the type layer, which already reports them.
        if not isinstance(value, str):
            return True

        try:
            host = urlsplit(value).hostname
        except ValueError:
            return False

        if not host:
            return False

        try:
            socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except (OSError, UnicodeError):
            return False

        return True

    async def enforceAsync(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Resolve a URL hostname without blocking the current event loop.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            URL to inspect, or a value left to type validation.
        instance : object
            Schema instance owning the field value.

        Returns
        -------
        bool
            Whether the hostname resolves or the value is not a string.
        """
        if not isinstance(value, str):
            return True
        try:
            host = urlsplit(value).hostname
        except ValueError:
            return False
        if not host:
            return False
        try:
            await asyncio.get_running_loop().getaddrinfo(
                host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM,
            )
        except (OSError, UnicodeError):
            return False
        return True
