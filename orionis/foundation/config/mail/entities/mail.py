from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.from_address import FromAddress
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.foundation.config.mail.enums.drivers import MailDriver
from orionis.foundation.config.validation import validate_string
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Mail(BaseEntity):
    """
    Represent the mail configuration entity.

    Attributes
    ----------
    default : str or MailDriver
        The default configured mailer name or its transport driver.
    from_address : FromAddress or dict
        Global sender applied to every message that declares no From header.
    mailers : Mailers or dict
        Conventional entities or arbitrary mailer names mapped to their settings.
    """

    default: str | MailDriver = field(
        default_factory=lambda: Env.get("MAIL_MAILER", MailDriver.SMTP),
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
        """
        Post-initialization processing for the Mail entity.

        This method validates the default mailer, the from_address, and the mailers.
        It ensures that the default mailer is declared in the mailers and that all
        nested settings are correctly typed and structured.

        Raises
        ------
        TypeError
            If any of the attributes are not of the expected type.
        ValueError
            If the default mailer is not declared in the mailers.
        """
        super().__post_init__()
        validate_string(self.default, "default")
        if not isinstance(self.from_address, (FromAddress, dict)):
            message = "'from_address' must be a FromAddress or dictionary."
            raise TypeError(message)
        if isinstance(self.from_address, dict):
            FromAddress(**self.from_address)
            object.__setattr__(self, "from_address", deepcopy(self.from_address))
        if not isinstance(self.mailers, (Mailers, dict)):
            message = "'mailers' must be a Mailers or dictionary."
            raise TypeError(message)
        if isinstance(self.mailers, dict):
            self.__validateMailers()
            available = self.mailers
        else:
            available = self.mailers.toDict()
        if self.default not in available:
            message = "The default mailer must be declared in 'mailers'."
            raise ValueError(message)

    def __validateMailers(self) -> None:
        """
        Validate nested mailer settings and ensure they are correctly typed.

        This method iterates over the mailers, checking that each mailer is either
        a dictionary, Smtp, or File instance. If a mailer is a dictionary, it will
        be validated and converted to the appropriate type.

        Raises
        ------
        TypeError
            If any of the mailer settings are not of the expected type.
        ValueError
            If the mailer settings are invalid or missing required keys.
        """
        for name, settings in self.mailers.items():
            validate_string(name, "mailer name")
            if not isinstance(settings, (dict, Smtp, File)):
                message = "Mailer settings must be a dictionary, Smtp, or File."
                raise TypeError(message)
            if isinstance(settings, dict):
                driver = settings.get("driver", name)
                validate_string(driver, "mailer driver")
                if driver == "smtp":
                    Smtp(**settings)
                elif driver == "file":
                    File(
                        **{
                            key: value
                            for key, value in settings.items()
                            if key != "driver"
                        },
                    )
        object.__setattr__(self, "mailers", deepcopy(self.mailers))
