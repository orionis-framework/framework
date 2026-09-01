from __future__ import annotations
from dataclasses import dataclass, field, fields as dc_fields
from orionis.foundation.config.queue.entities.brokers import Brokers
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed broker field names
_BROKER_OPTIONS: frozenset[str] = frozenset(
    f.name for f in dc_fields(Brokers)
) | {"async"}

@dataclass(frozen=True, kw_only=True)
class Queue(BaseEntity):
    """
    Represent the configuration for a queue system.

    Attributes
    ----------
    default : str
        The default queue connection to use.
    brokers : Brokers | dict
        The configuration for the queue brokers.
    """

    default: str = field(
        default_factory=lambda: Env.get("QUEUE_CONNECTION", "async"),
        metadata={
            "description": "The default queue connection to use.",
            "default": lambda: Env.get("QUEUE_CONNECTION", "async"),
        },
    )

    brokers: Brokers | dict = field(
        default_factory=Brokers,
        metadata={
            "description": "The default queue broker to use.",
            "default": lambda: Brokers().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize properties after initialization.

        Validates and normalizes the following properties:
        - default: Must be a string and match available broker options.
        - brokers: Must be an instance of Brokers or a dictionary.

        Returns
        -------
        None
            This method modifies the instance in place and returns None.
        """
        # Call the parent class's __post_init__ method
        super().__post_init__()

        # Validate 'default' against pre-cached broker option names
        if not isinstance(self.default, str) or self.default not in _BROKER_OPTIONS:
            error_msg = (
                f"The 'default' property must be a string and match one of the "
                f"available options ({sorted(_BROKER_OPTIONS)})."
            )
            raise ValueError(error_msg)

        # Ensure 'brokers' is a Brokers instance or convert from dict if needed
        if not isinstance(self.brokers, (Brokers, dict)):
            error_msg = (
                "brokers must be an instance of the Brokers class or a dictionary."
            )
            raise TypeError(error_msg)
        if isinstance(self.brokers, dict):
            object.__setattr__(self, "brokers", Brokers(**self.brokers))
