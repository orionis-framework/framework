from __future__ import annotations
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.proxies import HTTPProxies

if TYPE_CHECKING:
    from collections.abc import Iterable
    from ipaddress import IPv4Address, IPv6Address
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

# Loopback and RFC-1918 networks used to expand the 'private' shorthand.
_PRIVATE_NETWORKS: tuple[IPv4Network, ...] = (
    ip_network("127.0.0.0/8"),    # NOSONAR
    ip_network("10.0.0.0/8"),     # NOSONAR
    ip_network("172.16.0.0/12"),  # NOSONAR
    ip_network("192.168.0.0/16"), # NOSONAR
)

class ProxiesMiddleware:
    """
    Normalize client IP and scheme using trusted proxy headers.

    - Supports multiple proxies (X-Forwarded-For chain)
    - Supports multiple headers (get_all)
    - Prevents spoofing via trusted proxy validation

    The headers used to resolve the real client IP and the original
    scheme are an internal framework decision: the de-facto standard
    ``X-Forwarded-For`` and ``X-Forwarded-Proto`` headers are always
    used.  Applications only declare which proxies are trusted via
    ``trusted_proxies``.
    """

    # Standard forwarding headers; not configurable by design.
    _IP_HEADER: str = "x-forwarded-for"
    _PROTO_HEADER: str = "x-forwarded-proto"

    __slots__ = ("__enabled", "__trusted_networks")

    def __init__(
        self,
        config: dict,
    ) -> None:
        """
        Initialize the middleware with the given proxy configuration.

        Parameters
        ----------
        config : dict
            A dictionary whose keys must match ``HTTPProxies`` fields.

        Returns
        -------
        None
        """
        # Validate the raw configuration through the entity dataclass.
        cfg = HTTPProxies(**config)

        # Pre-compile proxy CIDRs into network objects for fast membership tests.
        self.__trusted_networks = self.__compile(cfg.trusted_proxies)

        # Requests are only rewritten when at least one proxy is trusted.
        self.__enabled = bool(self.__trusted_networks)

    def handle(self, adapter: TransportAdapter) -> TransportAdapter:
        """
        Process an ASGI/RSGI scope and normalize its client IP and scheme.

        Parameters
        ----------
        adapter : TransportAdapter
            The transport adapter to process.

        Returns
        -------
        TransportAdapter
            The same transport adapter with updated client and scheme fields.
        """
        # Bypass all proxy processing when no trusted proxies are configured.
        if not self.__enabled:
            return adapter

        self.__process(adapter)
        return adapter

    def __process(self, adapter: TransportAdapter) -> None:
        """
        Apply trusted-proxy normalization to the transport adapter.

        Parameters
        ----------
        adapter : TransportAdapter
            Abstraction over an RSGI or ASGI scope.

        Returns
        -------
        None
            Mutates ``adapter`` in place; no value is returned.
        """
        client_ip = adapter.client()
        if not client_ip:
            return

        # Skip requests that do not originate from a trusted proxy.
        client_addr = self.__parseIp(client_ip)
        if client_addr is None or not self.__isTrustedAddress(client_addr):
            return

        real_ip, proxies, chain = self.__resolveForwardedChain(
            adapter, client_ip,
        )

        adapter.setClient(real_ip)

        scheme = self.__resolveScheme(adapter)
        if scheme:
            adapter.setScheme(scheme)

        # Expose resolved forwarding metadata for downstream middleware.
        adapter.setState("forwarded", {
            "client": real_ip,
            "proxies": proxies,
            "chain": chain,
        })

    def __resolveForwardedChain(
        self,
        adapter: TransportAdapter,
        fallback_ip: str,
    ) -> tuple[str, list[str], list[str]]:
        """
        Resolve the real client IP from the forwarded header chain.

        Walks the chain right-to-left to skip trusted intermediaries
        and find the first untrusted address.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport abstraction providing header access.
        fallback_ip : str
            IP to return when no forwarded chain header is present.

        Returns
        -------
        tuple[str, list[str], list[str]]
            A three-element tuple of ``(real_ip, proxies, full_chain)``.
        """
        # Collect every well-formed IP from the forwarded header, keeping
        # the parsed address object alongside the original string.
        chain: list[str] = []
        parsed: list[IPv4Address | IPv6Address] = []
        for value in adapter.headers().getAll(self._IP_HEADER):
            # Headers may contain comma-separated IP lists.
            for raw_ip in value.split(","):
                ip = raw_ip.strip()
                if not ip:
                    continue
                addr = self.__parseIp(ip)
                if addr is not None:
                    chain.append(ip)
                    parsed.append(addr)

        if not chain:
            return fallback_ip, [], [fallback_ip]

        # Traverse right-to-left; the first untrusted IP is the real client.
        real_ip: str | None = None
        for index in range(len(parsed) - 1, -1, -1):
            if not self.__isTrustedAddress(parsed[index]):
                real_ip = chain[index]
                break

        # If every hop is trusted, fall back to the leftmost IP.
        if real_ip is None:
            real_ip = chain[0]

        proxies = [ip for ip in chain if ip != real_ip]

        return real_ip, proxies, chain

    def __resolveScheme(self, adapter: TransportAdapter) -> str | None:
        """
        Determine the original request scheme from forwarded headers.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport abstraction providing header access.

        Returns
        -------
        str or None
            ``'http'`` or ``'https'`` when the header is valid;
            ``None`` otherwise.
        """
        values = adapter.headers().getAll(self._PROTO_HEADER)

        if not values:
            return None

        # Only the first header value is considered; normalize case.
        value = values[0].strip().lower()

        if value in ("http", "https"):
            return value

        return None

    def __isTrustedAddress(
        self,
        addr: IPv4Address | IPv6Address,
    ) -> bool:
        """
        Determine whether a parsed address belongs to a trusted network.

        Parameters
        ----------
        addr : IPv4Address | IPv6Address
            The parsed IP address to evaluate.

        Returns
        -------
        bool
            ``True`` if the address is within a trusted network;
            ``False`` otherwise.
        """
        # Linear scan over the pre-compiled networks; the tuple is small.
        return any(addr in net for net in self.__trusted_networks)

    @staticmethod
    def __parseIp(value: str) -> IPv4Address | IPv6Address | None:
        """
        Parse a string into an IP address object.

        Parameters
        ----------
        value : str
            The string to parse.

        Returns
        -------
        IPv4Address | IPv6Address | None
            The parsed address, or ``None`` when the string is not a
            well-formed IPv4 or IPv6 address.
        """
        # Reject malformed addresses without propagating the exception.
        try:
            addr = ip_address(value)
        except ValueError:
            return None
        return addr

    @staticmethod
    def __compile(
        proxies: Iterable[str],
    ) -> tuple[IPv4Network | IPv6Network, ...]:
        """
        Compile proxy identifiers into network objects.

        The special token ``'private'`` expands into the standard
        RFC-1918 and loopback address ranges.

        Parameters
        ----------
        proxies : Iterable[str]
            An iterable of CIDR strings or the keyword ``'private'``.

        Returns
        -------
        tuple[IPv4Network | IPv6Network, ...]
            Compiled network objects used for IP membership tests.
        """
        networks: list[IPv4Network | IPv6Network] = []

        for p in proxies:
            if p == "private":
                # Expand shorthand to RFC-1918 + loopback networks.
                networks.extend(_PRIVATE_NETWORKS)
            else:
                networks.append(ip_network(p, strict=False))

        return tuple(networks)
