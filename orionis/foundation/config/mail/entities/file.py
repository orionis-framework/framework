from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class File(BaseEntity):
    """
    Represent a file configuration entity for storing outgoing emails.

    Attributes
    ----------
    path : str
        The file path where outgoing emails are stored.
    """

    path: str = field(
        default_factory=lambda: Env.get("MAIL_FILE_PATH", "storage/mail"),
        metadata={
            "description": "The file path where outgoing emails are stored.",
            "default": "storage/mail",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the 'path' attribute after initialization.

        Raises
        ------
        ValueError
            If 'path' is not a non-empty string.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Ensure 'path' is a non-empty string
        super().__post_init__()
        if not isinstance(self.path, str) or self.path.strip() == "":
            error_msg = "The 'path' attribute must be a non-empty string."
            raise ValueError(error_msg)
