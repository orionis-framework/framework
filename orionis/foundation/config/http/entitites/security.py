from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPSecurity(BaseEntity):
    """
    Represent the security-related configuration for HTTP.

    Attributes
    ----------
    allowed_hosts : list[str] | Literal["*"]
        List of allowed host names or '*' to allow all hosts.
    """

    allowed_hosts: list[str] | Literal["*"] = field(
        default_factory=lambda: Env.get("ALLOWED_HOSTS", []),
        metadata={
            "description": (
                "List of allowed host names or '*' to allow all hosts. "
                "Entries may use a leading wildcard to match subdomains "
                "(e.g. '*.example.com')."
            ),
            "default": [],
        },
    )

    def __post_init__(self) -> None:
        """
        Validate security-related fields.

        Raises
        ------
        TypeError
            If any field has an unexpected type.

        Returns
        -------
        None
        """
        super().__post_init__()
        self.__validateAllowedHosts()

    def __validateAllowedHosts(self) -> None:
        """
        Validate the ``allowed_hosts`` field.

        Raises
        ------
        TypeError
            If the value is not a list of strings or the literal '*'.

        Returns
        -------
        None
        """
        if self.allowed_hosts == "*":
            return

        if not isinstance(self.allowed_hosts, list):
            error_msg = (
                "Invalid type for 'allowed_hosts': expected a list of strings or '*'."
            )
            raise TypeError(error_msg)

        if not all(isinstance(host, str) for host in self.allowed_hosts):
            error_msg = "Invalid type for 'allowed_hosts': all items must be strings."
            raise TypeError(error_msg)

        normalized_hosts = [
            host.strip() for host in self.allowed_hosts if host and host.strip()
        ]
        app_url = Env.get("APP_URL")
        if app_url is not None:
            host = self.__extractHostFromUrl(str(app_url))
            if host and not self.__isLocalHost(host):
                self.__addHostToAllowedHosts(normalized_hosts, host)

        object.__setattr__(self, "allowed_hosts", normalized_hosts)

    def __extractHostFromUrl(self, url: str) -> str:
        """
        Extract the hostname from a URL-like value.

        Parameters
        ----------
        url : str
            URL or host string.

        Returns
        -------
        str
            Normalized hostname, or an empty string if it cannot be parsed.
        """
        if not url:
            return ""

        candidate = url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlsplit(candidate)
        host = parsed.hostname
        return host.lower() if host else ""

    def __isLocalHost(self, host: str) -> bool:
        """
        Return whether the host is local-only.

        Parameters
        ----------
        host : str
            Host to evaluate.

        Returns
        -------
        bool
            ``True`` when the host should not be added automatically.
        """
        return host in {"localhost", "127.0.0.1", "::1"}

    def __addHostToAllowedHosts(self, hosts: list[str], host: str) -> None:
        """
        Add a host to the list if it is missing.

        Parameters
        ----------
        hosts : list[str]
            Current allowed hosts list.
        host : str
            Host to add.

        Returns
        -------
        None
        """
        if not host or host in hosts:
            return

        hosts.append(host)
