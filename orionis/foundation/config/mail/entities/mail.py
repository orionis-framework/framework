from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.mail.entities.from_address import FromAddress
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Mail(BaseEntity):
    """
    Represent the mail configuration entity.

    Attributes
    ----------
    default : str
        The default configured mailer name, not its transport driver.
    from_address : FromAddress or dict
        Global sender applied to every message that declares no From header.
    mailers : Mailers or dict
        Conventional entities or arbitrary mailer names mapped to their settings.
    """

    default: str = field(
        default_factory=lambda: Env.get("MAIL_MAILER", "smtp"),
        metadata={
            "description": "The default configured mailer name.",
            "default": "smtp",
        },
    )

    from_address: FromAddress | dict = field(
        default_factory=FromAddress,
        metadata={
            "description": "The global sender used when a message declares none.",
            "default": lambda: FromAddress().toDict(),
        },
    )

    mailers: Mailers | dict = field(
        default_factory=Mailers,
        metadata={
            "description": "The available named mailer configurations.",
            "default": lambda: Mailers().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """Validate the configuration shape without resolving transports.

        Preserve named dictionary entries for driver registration by providers.
        Transport availability and operational settings are checked on sending.

        Returns
        -------
        None
            Copy dictionary entries without modifying the supplied configuration.

        Raises
        ------
        ValueError
            If the default or a mailer name is empty or not a string.
        TypeError
            If the global sender, mailers or their settings have an
            unsupported structure.
        """
        if not isinstance(self.default, str) or not self.default.strip():
            error_msg = "The 'default' property must be a non-empty mailer name."
            raise ValueError(error_msg)

        if not isinstance(self.from_address, (FromAddress, dict)):
            error_msg = (
                "The 'from_address' property must be an instance of FromAddress "
                "or a dictionary."
            )
            raise TypeError(error_msg)

        if not isinstance(self.mailers, (Mailers, dict)):
            error_msg = (
                "The 'mailers' property must be an instance of Mailers or a dictionary."
            )
            raise TypeError(error_msg)
        if not isinstance(self.mailers, dict):
            return
        entries = {}
        for name, settings in self.mailers.items():
            if not isinstance(name, str) or not name.strip():
                error_msg = "Mailer names must be non-empty strings."
                raise ValueError(error_msg)
            if not isinstance(settings, (dict, BaseEntity)):
                error_msg = "Mailer settings must be dictionaries or entities."
                raise TypeError(error_msg)
            entries[name] = dict(settings) if isinstance(settings, dict) else settings
        object.__setattr__(self, "mailers", entries)
