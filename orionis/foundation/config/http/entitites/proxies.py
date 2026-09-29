from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import copy_string_list
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPProxies(BaseEntity):
    """
    Represent the configuration for trusted HTTP proxies.

    Attributes
    ----------
    trusted_proxies : list[str]
        List of trusted proxy IP addresses or CIDR ranges.
    """

    trusted_proxies: list[str] = field(
        default_factory=lambda: Env.get("TRUSTED_PROXIES", ["127.0.0.1"]),
        metadata={
            "description": ("List of trusted proxy IP addresses or CIDR ranges."),
            "default": ["127.0.0.1"],
        },
    )

    def __post_init__(self) -> None:
        """
        Validate proxy fields.

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
        """
        Validate the ``trusted_proxies`` field.

        Coerce the list to ensure all elements are strings.

        Raises
        ------
        TypeError
            If the value is not a list of strings.

        Returns
        -------
        None
        """
        object.__setattr__(
            self,
            "trusted_proxies",
            copy_string_list(
                self.trusted_proxies,
                "trusted_proxies",
            ),
        )
