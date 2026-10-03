from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.http.entitites.body import HTTPBodyLimits
from orionis.foundation.config.http.entitites.cors import Cors
from orionis.foundation.config.http.entitites.csrf import HTTPCsrf
from orionis.foundation.config.http.entitites.proxies import (
    HTTPProxies,
)
from orionis.foundation.config.http.entitites.rate_limit import (
    HTTPRateLimit,
)
from orionis.foundation.config.http.entitites.security import (
    HTTPSecurity,
)
from orionis.foundation.config.http.entitites.websocket import HTTPWebSocket
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTP(BaseEntity):
    """Configure HTTP request handling and security.

    Parameters
    ----------
    monitor_disconnects : bool, optional
        Cancel handlers proactively when a client disconnects. Defaults to
        False, executing handlers in the server task with direct body reads.
        External server cancellation still propagates in both modes. The
        application snapshots this setting during create().
    """

    monitor_disconnects: bool = field(
        default=False,
        metadata={
            "description": "Monitor client disconnects during handler execution.",
            "default": False,
        },
    )

    body_limits: HTTPBodyLimits | dict = field(
        default_factory=HTTPBodyLimits,
        metadata={
            "description": "Request body, multipart and concurrency budgets.",
            "default": lambda: HTTPBodyLimits().toDict(),
        },
    )

    websocket: HTTPWebSocket | dict = field(
        default_factory=HTTPWebSocket,
        metadata={
            "description": "WebSocket connection and incoming message budgets.",
            "default": lambda: HTTPWebSocket().toDict(),
        },
    )

    proxies: HTTPProxies | dict = field(
        default_factory=HTTPProxies,
        metadata={
            "description": ("Trusted proxy resolution settings."),
            "default": lambda: HTTPProxies().toDict(),
        },
    )

    security: HTTPSecurity | dict = field(
        default_factory=HTTPSecurity,
        metadata={
            "description": ("Security header validation settings."),
            "default": lambda: HTTPSecurity().toDict(),
        },
    )

    rate_limit: HTTPRateLimit | dict = field(
        default_factory=HTTPRateLimit,
        metadata={
            "description": ("Global rate limiting settings."),
            "default": lambda: HTTPRateLimit().toDict(),
        },
    )

    cors: Cors | dict = field(
        default_factory=Cors,
        metadata={
            "description": ("CORS (Cross-Origin Resource Sharing) settings."),
            "default": lambda: Cors().toDict(),
        },
    )

    csrf: HTTPCsrf | dict = field(
        default_factory=HTTPCsrf,
        metadata={
            "description": ("CSRF protection settings for web routes."),
            "default": lambda: HTTPCsrf().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and coerce all composite fields.

        Convert dict values to their corresponding
        entity instances when provided as plain dicts.

        Raises
        ------
        TypeError
            If any field has an unexpected type.

        Returns
        -------
        None
        """
        super().__post_init__()
        if not isinstance(self.monitor_disconnects, bool):
            error_msg = "monitor_disconnects must be a bool."
            raise TypeError(error_msg)
        if isinstance(self.body_limits, dict):
            object.__setattr__(self, "body_limits", HTTPBodyLimits(**self.body_limits))
        elif not isinstance(self.body_limits, HTTPBodyLimits):
            error_msg = "body_limits must be an HTTPBodyLimits instance or dict."
            raise TypeError(error_msg)
        if isinstance(self.websocket, dict):
            object.__setattr__(self, "websocket", HTTPWebSocket(**self.websocket))
        elif not isinstance(self.websocket, HTTPWebSocket):
            error_msg = "websocket must be an HTTPWebSocket instance or dict."
            raise TypeError(error_msg)
        self.__validateProxies()
        self.__validateSecurity()
        self.__validateRateLimit()
        self.__validateCors()
        self.__validateCsrf()

    def __validateProxies(self) -> None:
        """
        Validate the ``proxies`` field.

        Coerce a dict to ``HTTPProxies`` if needed.

        Raises
        ------
        TypeError
            If the value is not an ``HTTPProxies``
            or dict.

        Returns
        -------
        None
        """
        if not isinstance(
            self.proxies,
            (HTTPProxies, dict),
        ):
            error_msg = (
                "Invalid type for 'proxies': expected an HTTPProxies instance or dict."
            )
            raise TypeError(error_msg)

        if isinstance(self.proxies, dict):
            object.__setattr__(
                self,
                "proxies",
                HTTPProxies(**self.proxies),
            )

    def __validateSecurity(self) -> None:
        """
        Validate the ``security`` field.

        Coerce a dict to ``HTTPSecurity`` if needed.

        Raises
        ------
        TypeError
            If the value is not an ``HTTPSecurity``
            or dict.

        Returns
        -------
        None
        """
        if not isinstance(
            self.security,
            (HTTPSecurity, dict),
        ):
            error_msg = (
                "Invalid type for 'security': expected "
                "an HTTPSecurity instance or dict."
            )
            raise TypeError(error_msg)

        if isinstance(self.security, dict):
            object.__setattr__(
                self,
                "security",
                HTTPSecurity(**self.security),
            )

    def __validateRateLimit(self) -> None:
        """
        Validate the ``rate_limit`` field.

        Coerce a dict to ``HTTPRateLimit`` if needed.

        Raises
        ------
        TypeError
            If the value is not an ``HTTPRateLimit``
            or dict.

        Returns
        -------
        None
        """
        if not isinstance(
            self.rate_limit,
            (HTTPRateLimit, dict),
        ):
            error_msg = (
                "Invalid type for 'rate_limit': "
                "expected an HTTPRateLimit instance "
                "or dict."
            )
            raise TypeError(error_msg)

        if isinstance(self.rate_limit, dict):
            object.__setattr__(
                self,
                "rate_limit",
                HTTPRateLimit(**self.rate_limit),
            )

    def __validateCors(self) -> None:
        """
        Validate the ``cors`` field.

        Coerce a dict to ``Cors`` if needed.

        Raises
        ------
        TypeError
            If the value is not a ``Cors``
            or dict.

        Returns
        -------
        None
        """
        if not isinstance(self.cors, (Cors, dict)):
            error_msg = "Invalid type for 'cors': expected a Cors instance or dict."
            raise TypeError(error_msg)

        if isinstance(self.cors, dict):
            object.__setattr__(
                self,
                "cors",
                Cors(**self.cors),
            )

    def __validateCsrf(self) -> None:
        """
        Validate the ``csrf`` field.

        Coerce a dict to ``HTTPCsrf`` if needed.

        Raises
        ------
        TypeError
            If the value is not an ``HTTPCsrf``
            or dict.

        Returns
        -------
        None
        """
        if not isinstance(self.csrf, (HTTPCsrf, dict)):
            error_msg = (
                "Invalid type for 'csrf': expected an HTTPCsrf instance or dict."
            )
            raise TypeError(error_msg)

        if isinstance(self.csrf, dict):
            object.__setattr__(
                self,
                "csrf",
                HTTPCsrf(**self.csrf),
            )
