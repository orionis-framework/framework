from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.security import HTTPSecurity

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.responses import Response

class SecurityMiddleware:
    """
    Enforce baseline HTTP security policies on every request.

    The following checks are always active and are not configurable:

    - CRLF-injection detection in header names and values.
    - Rejection of requests carrying more than one ``Host`` header.

    Host allowlist validation runs only when ``allowed_hosts`` is
    configured with an explicit list of host names.
    """

    __slots__ = (
        "__allowed_host_suffixes",
        "__allowed_hosts",
        "__default_responses",
        "__enforce_hosts",
    )

    def __init__(
        self,
        config: dict,
        default_responses: IDefaultResponses,
    ) -> None:
        """Initialize the middleware with the given security configuration.

        Parameters
        ----------
        config : dict
            A dictionary whose keys must match ``HTTPSecurity`` fields.
        default_responses : IDefaultResponses
            Predefined default responses for common HTTP errors.

        Returns
        -------
        None
        """
        # Validate the raw configuration through the entity dataclass.
        cfg = HTTPSecurity(**config)

        # Pre-build lowercase sets for O(1) membership tests.  Entries
        # with a leading '*.' are treated as wildcard subdomain patterns.
        exact: set[str] = set()
        suffixes: list[str] = []
        if isinstance(cfg.allowed_hosts, list):
            for entry in cfg.allowed_hosts:
                host = entry.strip().lower()
                if not host:
                    continue
                if host.startswith("*."):
                    # '*.example.com' matches any subdomain and the
                    # bare domain itself.
                    suffixes.append(host[1:])
                    exact.add(host[2:])
                else:
                    exact.add(host)
        self.__allowed_hosts: frozenset[str] = frozenset(exact)
        self.__allowed_host_suffixes: tuple[str, ...] = tuple(suffixes)

        # Host validation is skipped entirely when no allowlist is set.
        self.__enforce_hosts: bool = bool(exact or suffixes)

        # Store the default responses for use in the handler.
        self.__default_responses = default_responses

    @staticmethod
    def __extractHostname(raw_host: str) -> str:
        """Strip the optional port from a ``Host`` header value.

        Handles both ``host:port`` and IPv6 literals such as
        ``[::1]:8000``.

        Parameters
        ----------
        raw_host : str
            The raw ``Host`` header value.

        Returns
        -------
        str
            The lowercase hostname without the port component.
        """
        host = raw_host.strip().lower()

        # IPv6 literal: "[::1]" or "[::1]:8000"
        if host.startswith("["):
            end = host.find("]")
            if end != -1:
                return host[1:end]
            return host

        # "host:port" -> "host"
        return host.rsplit(":", 1)[0] if ":" in host else host

    def __isAllowedHost(self, host: str) -> bool:
        """Check a hostname against the configured allowlist.

        Parameters
        ----------
        host : str
            Lowercase hostname without the port component.

        Returns
        -------
        bool
            ``True`` when the host matches an exact entry or a
            wildcard subdomain pattern; ``False`` otherwise.
        """
        if host in self.__allowed_hosts:
            return True

        # Fall back to wildcard subdomain suffix matching.
        return any(
            host.endswith(suffix)
            for suffix in self.__allowed_host_suffixes
        )

    def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """Inspect the incoming request and enforce all security policies.

        Runs three sequential checks in order: CRLF-injection
        detection, duplicate Host header guard, and host allowlist
        validation.  Returns a ``Response`` on the first violation, or
        ``None`` when all checks pass.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport abstraction providing header access and
            client-preference detection.

        Returns
        -------
        Response | None
            An HTTP error response when a check fails, or ``None``
            when the request is considered safe to proceed.
        """
        # Resolve the headers structure once for the whole handler.
        headers = adapter.headers()

        # 1. Reject headers that contain bare CR or LF (CRLF injection).
        for name, value in headers:
            if (
                "\r" in name or "\n" in name
                or "\r" in value or "\n" in value
            ):
                return self.__default_responses.error(
                    status_code=400,
                    content="Invalid header format.",
                    expects_json=adapter.wantsJson(),
                )

        # 2. Reject requests that carry more than one Host header.
        host_values = headers.getAll("host")
        if len(host_values) > 1:
            return self.__default_responses.error(
                status_code=400,
                content="Multiple Host headers not allowed.",
                expects_json=adapter.wantsJson(),
            )

        # 3. Validate Host against the allowlist (strip port, lowercase).
        if self.__enforce_hosts:
            raw_host = headers.get("host")
            if not raw_host or not self.__isAllowedHost(
                self.__extractHostname(raw_host),
            ):
                return self.__default_responses.error(
                    status_code=400,
                    content="Host header not allowed.",
                    expects_json=adapter.wantsJson(),
                )

        # All checks passed; allow the request to proceed.
        return None
