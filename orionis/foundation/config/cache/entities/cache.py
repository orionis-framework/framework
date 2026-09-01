from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.foundation.config.cache.entities.stores import Stores
from orionis.foundation.config.cache.enums import Drivers
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid driver names for O(1) membership checks
_DRIVER_NAMES: frozenset[str] = frozenset(Drivers._member_names_)

@dataclass(frozen=True, kw_only=True)
class Cache(BaseEntity):
    """
    Represent the cache configuration for the application.

    Attributes
    ----------
    default : Drivers | str
        The default cache storage type. Accepts a ``Drivers`` enum member
        or a plain string (e.g. ``'memory'``, ``'file'``). Resolved from
        the ``CACHE_STORE`` environment variable or ``Drivers.FILE.value``.
    prefix : str
        Global key prefix applied to all cache entries. Resolved from
        the ``CACHE_PREFIX`` environment variable or ``'orionis'``.
    stores : Stores | dict
        Configuration for the available cache stores. Defaults to a
        ``Stores`` instance backed by a file store.
    """

    default: Drivers | str = field(
        default_factory=lambda: Env.get("CACHE_STORE", Drivers.FILE.value),
        metadata={
            "description": (
                "The default cache storage type. Can be a member of the "
                "Drivers enum or a string (e.g., 'memory', 'file')."
            ),
            "default": Drivers.FILE.value,
        },
    )

    prefix: str = field(
        default_factory=lambda: Env.get("CACHE_PREFIX", "orionis"),
        metadata={
            "description": "Global key prefix applied to all cache entries.",
            "default": "orionis",
        },
    )

    stores: Stores | dict = field(
        default_factory=Stores,
        metadata={
            "description": (
                "The configuration for available cache stores. Defaults to "
                "a file store at the specified path."
            ),
            "default": lambda: Stores().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the cache configuration after initialization.

        Returns
        -------
        None
            Modifies instance attributes in place via ``object.__setattr__``.

        Raises
        ------
        TypeError
            If ``prefix`` is not a ``str``, ``default`` is not a
            ``Drivers`` enum or ``str``, or ``stores`` is not a
            ``Stores`` instance or ``dict``.
        ValueError
            If ``default`` is a string that does not match any valid driver.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Ensure prefix is always a plain string
        if not isinstance(self.prefix, str):
            error_msg = "The cache prefix must be a string."
            raise TypeError(error_msg)

        # Reject types that are neither Drivers enum nor string
        if not isinstance(self.default, (Drivers, str)):
            error_msg = (
                "The default cache store must be an instance of "
                "Drivers or a string."
            )
            raise TypeError(error_msg)

        # Validate string driver names and normalise to canonical enum value
        if isinstance(self.default, str):
            _value = self.default.upper().strip()
            if _value not in _DRIVER_NAMES:
                error_msg = (
                    f"Invalid cache driver: {self.default}. "
                    f"Must be one of {sorted(_DRIVER_NAMES)!s}."
                )
                raise ValueError(error_msg)
            # Normalise to the canonical string value stored in the enum
            object.__setattr__(self, "default", Drivers[_value].value)
        else:
            # Extract the raw string value from the Drivers enum member
            object.__setattr__(self, "default", self.default.value)

        # Reject stores that are neither Stores instances nor dicts
        if not isinstance(self.stores, (Stores, dict)):
            error_msg = (
                "The stores configuration must be an instance of "
                "Stores or a dictionary."
            )
            raise TypeError(error_msg)

        # Convert a plain dict to a typed Stores instance
        if isinstance(self.stores, dict):
            object.__setattr__(self, "stores", Stores(**self.stores))
