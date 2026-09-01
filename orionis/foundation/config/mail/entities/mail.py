from __future__ import annotations
from dataclasses import dataclass, field, fields
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed mailer option names
_MAILER_OPTIONS: frozenset[str] = frozenset(f.name for f in fields(Mailers))

@dataclass(frozen=True, kw_only=True)
class Mail(BaseEntity):
    """
    Represent the mail configuration entity.

    Attributes
    ----------
    default : str
        The default mailer transport to use.
    mailers : Mailers or dict
        The available mail transport configurations.
    """

    default: str = field(
        default_factory=lambda: Env.get("MAIL_MAILER", "smtp"),
        metadata={
            "description": "The default mailer transport to use.",
            "default": "smtp",
        },
    )

    mailers: Mailers | dict = field(
        default_factory=Mailers,
        metadata={
            "description": "The available mail transport configurations.",
            "default": lambda: Mailers().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the integrity of the Mail instance after initialization.

        Ensures that the 'default' attribute is a string and matches one of the
        available mailer options, and that the 'mailers' attribute is an instance
        of Mailers or a dictionary.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If 'default' is not a valid string option.
        TypeError
            If 'mailers' is not a Mailers object or a dictionary.
        """
        # Validate 'default' attribute against pre-cached mailer options
        options = _MAILER_OPTIONS
        if not isinstance(self.default, str) or self.default not in options:
            error_msg = (
                f"The 'default' property must be a string and match one of the "
                f"available options ({sorted(options)})."
            )
            raise ValueError(error_msg)

        # Validate 'mailers' attribute
        if not isinstance(self.mailers, (Mailers, dict)):
            error_msg = (
                "The 'mailers' property must be an instance of Mailers or a dictionary."
            )
            raise TypeError(error_msg)
        # Convert dict to Mailers if necessary
        if isinstance(self.mailers, dict):
            object.__setattr__(self, "mailers", Mailers(**self.mailers))
