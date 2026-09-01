from __future__ import annotations
from dataclasses import dataclass, field, fields
from orionis.foundation.config.logging.entities.channels import Channels
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed channel option names
_CHANNEL_OPTIONS: frozenset[str] = frozenset(f.name for f in fields(Channels))

@dataclass(frozen=True, kw_only=True)
class Logging(BaseEntity):
    """
    Represent the logging system configuration.

    Attributes
    ----------
    default : str
        The default logging channel to use.
    channels : Channels or dict
        A collection of available logging channels.
    """

    default: str = field(
        default_factory=lambda: Env.get("LOG_CHANNEL", "stack"),
        metadata={
            "description": "The default logging channel to use.",
            "default": lambda: Env.get("LOG_CHANNEL", "stack"),
        },
    )

    channels: Channels | dict = field(
        default_factory=Channels,
        metadata={
            "description": "A collection of available logging channels.",
            "default": lambda: Channels().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the logging configuration after dataclass initialization.

        Parameters
        ----------
        self : Logging
            The instance of the Logging class.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the default channel is not a string or does not match available
            channel options.
        TypeError
            If the channels configuration is malformed or cannot be converted
            to a Channels instance.
        TypeError
            If the channels property is not a Channels instance or a dictionary.

        Notes
        -----
        - Ensures 'default' is a string matching available channel options from
          Channels fields.
        - Ensures 'channels' is a Channels instance or a dictionary.
        """
        # Call the parent class's __post_init__ method.
        super().__post_init__()

        # Validate 'default' against pre-cached channel names
        if not isinstance(self.default, str) or self.default not in _CHANNEL_OPTIONS:
            error_msg = (
                f"The 'default' property must be a string and match one of the "
                f"available options ({sorted(_CHANNEL_OPTIONS)})."
            )
            raise ValueError(error_msg)

        # Validate that 'channels' is either a Channels instance or a dictionary.
        if not isinstance(self.channels, (Channels, dict)):
            error_msg = (
                "The 'channels' property must be an instance of Channels or a "
                "dictionary."
            )
            raise TypeError(error_msg)

        # Convert dictionary to Channels instance if necessary.
        if isinstance(self.channels, dict):
            object.__setattr__(self, "channels", Channels(**self.channels))
