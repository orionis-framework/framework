from __future__ import annotations

from dataclasses import dataclass, field

from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.support.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Mailers(BaseEntity):
    """
    Represent mail transport configurations for the application.

    Attributes
    ----------
    smtp : Smtp | dict
        The SMTP configuration used for sending emails.
    file : File | dict
        The file-based mail transport configuration.
    """

    smtp: Smtp | dict = field(
        default_factory=Smtp,
        metadata={
            "description": "The SMTP configuration used for sending emails.",
            "default": lambda: Smtp().toDict(),
        },
    )

    file: File | dict = field(
        default_factory=File,
        metadata={
            "description": "The file-based mail transport configuration.",
            "default": lambda: File().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate attribute types after initialization.

        Ensures that the 'smtp' attribute is an instance of the Smtp class or a
        dictionary, and the 'file' attribute is an instance of the File class or
        a dictionary.

        Raises
        ------
        TypeError
            If 'smtp' is not a Smtp object or a dictionary, or if 'file' is not a
            File object or a dictionary.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate `smtp` attribute type and convert dict to Smtp if needed
        super().__post_init__()
        if not isinstance(self.smtp, (Smtp, dict)):
            error_msg = "The 'smtp' attribute must be a Smtp object or a dictionary."
            raise TypeError(error_msg)
        if isinstance(self.smtp, dict):
            object.__setattr__(self, "smtp", Smtp(**self.smtp))

        # Validate `file` attribute type and convert dict to File if needed
        if not isinstance(self.file, (File, dict)):
            error_msg = "The 'file' attribute must be a File object or a dictionary."
            raise TypeError(error_msg)
        if isinstance(self.file, dict):
            object.__setattr__(self, "file", File(**self.file))
