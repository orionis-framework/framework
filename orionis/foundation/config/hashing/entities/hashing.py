from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.env import Env
from orionis.foundation.config.hashing.entities.argon2 import Argon2
from orionis.foundation.config.hashing.entities.bcrypt import Bcrypt
from orionis.foundation.config.hashing.enums import Drivers
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid driver names for O(1) membership checks
_DRIVER_NAMES: frozenset[str] = frozenset(Drivers._member_names_)

@dataclass(frozen=True, kw_only=True)
class Hashing(BaseEntity):
    """
    Represent the password hashing configuration for the application.

    Attributes
    ----------
    driver : Drivers | str
        Default hashing driver. Accepts a ``Drivers`` enum member or a
        plain string (``'argon2'`` or ``'bcrypt'``). Resolved from the
        ``HASH_DRIVER`` environment variable or ``Drivers.ARGON2.value``.
    argon2 : Argon2 | dict
        Cost parameters applied by the Argon2id driver.
    bcrypt : Bcrypt | dict
        Cost parameters applied by the bcrypt driver.
    """

    driver: Drivers | str = field(
        default_factory=lambda: Env.get("HASH_DRIVER", Drivers.ARGON2.value),
        metadata={
            "description": (
                "The default password hashing driver. Can be a member of "
                "the Drivers enum or a string ('argon2', 'bcrypt')."
            ),
            "default": Drivers.ARGON2.value,
        },
    )

    argon2: Argon2 | dict = field(
        default_factory=Argon2,
        metadata={
            "description": "Cost parameters applied by the Argon2id driver.",
            "default": lambda: Argon2().toDict(),
        },
    )

    bcrypt: Bcrypt | dict = field(
        default_factory=Bcrypt,
        metadata={
            "description": "Cost parameters applied by the bcrypt driver.",
            "default": lambda: Bcrypt().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the hashing configuration after initialization.

        Returns
        -------
        None
            Modifies instance attributes in place via ``object.__setattr__``.

        Raises
        ------
        TypeError
            If ``driver`` is not a ``Drivers`` enum or ``str``, or if the
            driver options are neither entities nor dictionaries.
        ValueError
            If ``driver`` is a string that does not match any valid driver.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Reject types that are neither Drivers enum nor string
        if not isinstance(self.driver, (Drivers, str)):
            error_msg = (
                "The default hashing driver must be an instance of "
                "Drivers or a string."
            )
            raise TypeError(error_msg)

        # Validate string driver names and normalise to canonical enum value
        if isinstance(self.driver, str):
            _value = self.driver.upper().strip()
            if _value not in _DRIVER_NAMES:
                error_msg = (
                    f"Invalid hashing driver: {self.driver}. "
                    f"Must be one of {sorted(_DRIVER_NAMES)!s}."
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "driver", Drivers[_value].value)
        else:
            # Extract the raw string value from the Drivers enum member
            object.__setattr__(self, "driver", self.driver.value)

        # Convert plain dictionaries into typed configuration entities
        if not isinstance(self.argon2, (Argon2, dict)):
            error_msg = (
                "The argon2 configuration must be an instance of Argon2 "
                "or a dictionary."
            )
            raise TypeError(error_msg)
        if isinstance(self.argon2, dict):
            object.__setattr__(self, "argon2", Argon2(**self.argon2))

        if not isinstance(self.bcrypt, (Bcrypt, dict)):
            error_msg = (
                "The bcrypt configuration must be an instance of Bcrypt "
                "or a dictionary."
            )
            raise TypeError(error_msg)
        if isinstance(self.bcrypt, dict):
            object.__setattr__(self, "bcrypt", Bcrypt(**self.bcrypt))
