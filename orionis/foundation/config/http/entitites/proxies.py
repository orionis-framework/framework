from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPProxies(BaseEntity):

    trusted_proxies: list[str] = field(
        default_factory=lambda: Env.get("TRUSTED_PROXIES", []),
        metadata={
            "description": (
                "List of trusted proxy IP addresses or CIDR ranges."
            ),
        },
    )

    def __post_init__(self) -> None:
        """Validate proxy fields.

        Raises
        ------
        TypeError
            If any field has an unexpected type.

        Returns
        -------
        None
        """
        super().__post_init__()
        self.__validateTrustedProxies()

    def __validateTrustedProxies(self) -> None:
        """Validate the ``trusted_proxies`` field.

        Raises
        ------
        TypeError
            If the value is not a list of strings.

        Returns
        -------
        None
        """
        if not isinstance(self.trusted_proxies, list):
            error_msg = (
                "Invalid type for 'trusted_proxies': expected a list of strings."
            )
            raise TypeError(error_msg)

        if not all(
            isinstance(p, str)
            for p in self.trusted_proxies
        ):
            error_msg = (
                "Invalid type for 'trusted_proxies': all items must be strings."
            )
            raise TypeError(error_msg)
