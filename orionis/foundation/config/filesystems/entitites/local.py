from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_string
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Local(BaseEntity):
    """
    Represent a local filesystem configuration.

    Parameters
    ----------
    local : Local
        The local filesystem configuration entity.
    path : str, default="storage/app/private"
        The absolute or relative path where local files are stored.

    Returns
    -------
    None
        This class does not return a value.
    """

    driver: str = field(
        default="local",
        metadata={
            "description": "The filesystem driver type.",
            "default": "local",
        },
    )

    path: str = field(
        default_factory=lambda: Env.get("LOCAL_PATH", "storage/app/private"),
        metadata={
            "description": (
                "The absolute or relative path where local files are stored."
            ),
            "default": "storage/app/private",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and initialize the 'path' attribute after object creation.

        Ensure that the 'path' attribute is a non-empty string. The selected
        storage driver creates the directory when it is initialized.

        Parameters
        ----------
        self : Local
            The instance of the Local class.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call the superclass post-init method
        super().__post_init__()

        # Custom drivers may reuse the local disk options.
        validate_string(self.driver, "driver")

        # Ensure 'path' is a string
        if not isinstance(self.path, str):
            error_msg = "The 'path' attribute must be a string."
            raise TypeError(error_msg)

        # Ensure 'path' is not empty or whitespace
        if not self.path.strip():
            error_msg = "The 'path' attribute cannot be empty."
            raise ValueError(error_msg)
