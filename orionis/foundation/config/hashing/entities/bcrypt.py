from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.env import Env
from orionis.support.entities.base import BaseEntity

# Bounds imposed by the bcrypt algorithm itself
_MIN_ROUNDS: int = 4
_MAX_ROUNDS: int = 31

@dataclass(frozen=True, kw_only=True)
class Bcrypt(BaseEntity):
    """
    Represent the configuration entity for the bcrypt hashing driver.

    Attributes
    ----------
    rounds : int
        Cost factor (base-2 logarithm of the iteration count).
    """

    rounds: int = field(
        default_factory=lambda: Env.get("BCRYPT_ROUNDS", 12),
        metadata={
            "description": (
                "Cost factor used by bcrypt, expressed as the base-2 "
                "logarithm of the iteration count. Must be between 4 and 31."
            ),
            "default": 12,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the bcrypt cost factor after initialization.

        Returns
        -------
        None
            This method validates the instance attributes in place.

        Raises
        ------
        TypeError
            If ``rounds`` is not an integer.
        ValueError
            If ``rounds`` falls outside the range supported by bcrypt.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # The cost factor must be a plain integer, never a boolean
        if not isinstance(self.rounds, int) or isinstance(self.rounds, bool):
            error_msg = "The bcrypt 'rounds' option must be an integer."
            raise TypeError(error_msg)

        # bcrypt only accepts cost factors within a fixed range
        if not _MIN_ROUNDS <= self.rounds <= _MAX_ROUNDS:
            error_msg = (
                f"The bcrypt 'rounds' option must be between {_MIN_ROUNDS} "
                f"and {_MAX_ROUNDS}."
            )
            raise ValueError(error_msg)
