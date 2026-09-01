from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Public(BaseEntity):
    """
    Represent a local filesystem configuration.

    Parameters
    ----------
    driver : str, default="local"
        The filesystem driver type. Default is "local".
    path : str
        The absolute or relative path where public files are stored.
    url : str
        The URL where the public files can be accessed.

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
        default_factory=lambda: Env.get("PUBLIC_PATH", "storage/app/public"),
        metadata={
            "description": (
                "The absolute or relative path where public files are stored."
            ),
            "default": "storage/app/public",
        },
    )

    url: str = field(
        default_factory=lambda: Env.get("PUBLIC_URL", "/static"),
        metadata={
            "description": "The URL where the public files can be accessed.",
            "default": "/static",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and initialize the Public entity.

        Ensures that 'path' and 'url' are non-empty strings of type str.

        Parameters
        ----------
        self : Public
            The instance of the Public class.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If 'path' or 'url' is not of type str.
        ValueError
            If 'path' or 'url' is an empty string.
        """
        super().__post_init__()

        # Validate that 'path' is a string
        if not isinstance(self.path, str):
            error_msg = "The 'path' attribute must be a string."
            raise TypeError(error_msg)

        # Validate that 'url' is a string
        if not isinstance(self.url, str):
            error_msg = "The 'url' attribute must be a string."
            raise TypeError(error_msg)

        # Ensure neither 'path' nor 'url' is empty or whitespace
        if not self.path.strip() or not self.url.strip():
            error_msg = "The 'path' and 'url' attributes cannot be empty."
            raise ValueError(error_msg)

        # Create the directory if it does not exist
        Path(self.path.strip()).mkdir(parents=True, exist_ok=True)
