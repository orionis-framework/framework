from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.logging.entities.chunked import Chunked
from orionis.foundation.config.logging.entities.daily import Daily
from orionis.foundation.config.logging.entities.hourly import Hourly
from orionis.foundation.config.logging.entities.monthly import Monthly
from orionis.foundation.config.logging.entities.stack import Stack
from orionis.foundation.config.logging.entities.weekly import Weekly
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Channels(BaseEntity):
    """
    Represent the available logging channels and their configurations.

    Attributes
    ----------
    stack : Stack | dict
        Configuration for stack log channel.
    hourly : Hourly | dict
        Configuration for hourly log rotation.
    daily : Daily | dict
        Configuration for daily log rotation.
    weekly : Weekly | dict
        Configuration for weekly log rotation.
    monthly : Monthly | dict
        Configuration for monthly log rotation.
    chunked : Chunked | dict
        Configuration for chunked log file storage.
    """

    stack: Stack | dict = field(
        default_factory=Stack,
        metadata={
            "description": "Configuration for stack log channel.",
            "default": lambda: Stack().toDict(),
        },
    )

    hourly: Hourly | dict = field(
        default_factory=Hourly,
        metadata={
            "description": "Configuration for hourly log rotation.",
            "default": lambda: Hourly().toDict(),
        },
    )

    daily: Daily | dict = field(
        default_factory=Daily,
        metadata={
            "description": "Configuration for daily log rotation.",
            "default": lambda: Daily().toDict(),
        },
    )

    weekly: Weekly | dict = field(
        default_factory=Weekly,
        metadata={
            "description": "Configuration for weekly log rotation.",
            "default": lambda: Weekly().toDict(),
        },
    )

    monthly: Monthly | dict = field(
        default_factory=Monthly,
        metadata={
            "description": "Configuration for monthly log rotation.",
            "default": lambda: Monthly().toDict(),
        },
    )

    chunked: Chunked | dict = field(
        default_factory=Chunked,
        metadata={
            "description": "Configuration for chunked log file storage.",
            "default": lambda: Chunked().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and construct every configured logging channel.

        Raises
        ------
        TypeError
            If any of the channel configurations is not a dictionary
            or the expected entity instance.
        """
        super().__post_init__()
        for name, entity in (
            ("stack", Stack),
            ("hourly", Hourly),
            ("daily", Daily),
            ("weekly", Weekly),
            ("monthly", Monthly),
            ("chunked", Chunked),
        ):
            value = getattr(self, name)
            if isinstance(value, dict):
                object.__setattr__(self, name, entity(**value))
            elif not isinstance(value, entity):
                message = f"'{name}' must be a {entity.__name__} or dictionary."
                raise TypeError(message)
