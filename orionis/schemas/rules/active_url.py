import asyncio
import socket
from urllib.parse import urlsplit
from orionis.schemas.rule import Rule

class ActiveUrl(Rule):
    """
    Ensure a URL points at a hostname that currently resolves.

    The hostname is extracted from the URL and looked up through the system
    resolver, so the check succeeds only when an ``A`` or ``AAAA`` record
    exists. Resolution is awaited without blocking the calling event loop.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be a URL with a resolvable hostname."
    __code__ = "active_url"

    async def enforce(
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
