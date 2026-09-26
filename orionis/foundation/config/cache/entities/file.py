from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class File(BaseEntity):
    """
    Represent the configuration entity for a file-based cache store.

    Attributes
    ----------
    driver : str
        The driver type for the cache store. Defaults to ``'file'``.
    path : str
        The filesystem path where cache data will be stored. Defaults
        to ``'storage/framework/cache/data'``.
    """

    driver: str = field(
        default="file",
        metadata={
            "description": ("The driver type for the cache store. Defaults to 'file'."),
            "default": "file",
        },
    )

    path: str = field(
        default_factory=lambda: Env.get(
            "CACHE_FILE_PATH",
            "storage/framework/cache/data",
        ),
        metadata={
            "description": (
                "The filesystem path where cache data will be stored. Defaults "
                "to 'storage/framework/cache/data'."
            ),
            "default": "storage/framework/cache/data",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and initialise the ``path`` attribute after dataclass init.

        Ensure ``path`` is a non-empty string. The selected cache driver
        creates the backing directory when it is initialized.

        Returns
        -------
        None
            Validate the configuration without changing the filesystem.

        Raises
        ------
        TypeError
            If ``path`` is not a ``str``.
        ValueError
            If ``path`` is an empty string.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Ensure the driver attribute is set to 'file'
        if self.driver != "file":
            message = f"The 'driver' attribute must be 'file', but got {self.driver}."
            raise TypeError(message)

        # Check type before truthiness to avoid misleading error messages
        if not isinstance(self.path, str):
            error_msg = (
                "File cache configuration error: 'path' must be a string, "
                f"got {type(self.path).__name__}."
            )
            raise TypeError(error_msg)

        # Reject empty strings after confirming the correct type
        if not self.path.strip():
            error_msg = (
                "File cache configuration error: 'path' cannot be empty. "
                "Please provide a valid file path."
            )
            raise ValueError(error_msg)
