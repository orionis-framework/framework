from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class FromAddress(BaseEntity):
    """
    Represent the global sender applied to messages that declare no From.

    Attributes
    ----------
    address : str
        Default sender mailbox, or an empty string to require an explicit one.
    name : str
        Optional display name attached to the default mailbox.
    """

    address: str = field(
        default_factory=lambda: Env.get("MAIL_FROM_ADDRESS", ""),
        metadata={
            "description": "The sender mailbox used when a message declares none.",
            "default": "",
        },
    )

    name: str = field(
        default_factory=lambda: Env.get("MAIL_FROM_NAME", ""),
        metadata={
            "description": "The display name attached to the global sender.",
            "default": "",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the structural types without parsing the mailbox.

        Mailbox syntax is validated while composing a message, so an unused or
        empty global sender never prevents the application from starting.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If 'address' or 'name' is not a string.
        """
        # Validate 'address' type
        if not isinstance(self.address, str):
            error_msg = "The 'address' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'name' type
        if not isinstance(self.name, str):
            error_msg = "The 'name' attribute must be a string."
            raise TypeError(error_msg)
