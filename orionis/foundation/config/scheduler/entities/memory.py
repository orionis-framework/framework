from __future__ import annotations
from dataclasses import dataclass, field
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Memory(BaseEntity):
    """
    Represent the configuration entity for an in-memory job store.

    Attributes
    ----------
    driver : str
        The driver type for the job store. Defaults to ``'memory'``.
    """

    driver: str = field(
        default="memory",
        metadata={
            "description": ("The driver type for the job store. Defaults to 'memory'."),
            "default": "memory",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the Memory configuration after initialization.

        Returns
        -------
        None
            Delegates validation to the parent ``BaseEntity.__post_init__``.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Ensure the driver is set to 'memory' for this store.
        if self.driver != "memory":
            message = f"Invalid driver for Memory store: {self.driver}"
            raise ValueError(message)
