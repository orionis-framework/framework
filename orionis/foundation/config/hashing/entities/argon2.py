from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.env import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Argon2(BaseEntity):
    """
    Represent the configuration entity for the Argon2id hashing driver.

    Attributes
    ----------
    memory : int
        Amount of memory, in kibibytes, used by the algorithm.
    threads : int
        Degree of parallelism used by the algorithm.
    time : int
        Number of iterations performed by the algorithm.
    """

    memory: int = field(
        default_factory=lambda: Env.get("ARGON_MEMORY", 65536),
        metadata={
            "description": (
                "Amount of memory, in kibibytes, used by Argon2id. Higher "
                "values increase resistance to brute-force attacks."
            ),
            "default": 65536,
        },
    )

    threads: int = field(
        default_factory=lambda: Env.get("ARGON_THREADS", 4),
        metadata={
            "description": (
                "Degree of parallelism (lanes) used by Argon2id."
            ),
            "default": 4,
        },
    )

    time: int = field(
        default_factory=lambda: Env.get("ARGON_TIME", 3),
        metadata={
            "description": (
                "Number of iterations (time cost) performed by Argon2id."
            ),
            "default": 3,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the Argon2id cost parameters after initialization.

        Returns
        -------
        None
            This method validates the instance attributes in place.

        Raises
        ------
        TypeError
            If any cost parameter is not an integer.
        ValueError
            If any cost parameter is lower than one.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Every Argon2id cost parameter must be a positive integer
        for name in ("memory", "threads", "time"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                error_msg = f"The Argon2 '{name}' option must be an integer."
                raise TypeError(error_msg)
            if value < 1:
                error_msg = f"The Argon2 '{name}' option must be at least 1."
                raise ValueError(error_msg)
