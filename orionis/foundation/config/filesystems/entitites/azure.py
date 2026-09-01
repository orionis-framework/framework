from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Azure(BaseEntity):
    """
    Represent an Azure Blob Storage configuration.

    Using this disk requires the official Azure SDK, which is an
    optional dependency: install it with ``pip install
    azure-storage-blob`` (or ``pip install orionis[azure]``).

    Parameters
    ----------
    driver : str, default="azure"
        The filesystem driver type. Default is "azure".
    connection_string : str
        Azure storage connection string. When provided, it takes
        precedence over the account name and key.
    account_name : str
        Azure storage account name.
    account_key : str
        Azure storage account key.
    container : str
        The blob container name.
    url : str | None, default=None
        Public base URL used to build file URLs.

    Returns
    -------
    None
        This class does not return a value.
    """

    driver: str = field(
        default="azure",
        metadata={
            "description": "The filesystem driver type.",
            "default": "azure",
        },
    )

    connection_string: str = field(
        default_factory=lambda: Env.get("AZURE_CONNECTION_STRING", ""),
        metadata={
            "description": "Azure storage connection string.",
            "default": "",
        },
    )

    account_name: str = field(
        default_factory=lambda: Env.get("AZURE_ACCOUNT_NAME", ""),
        metadata={
            "description": "Azure storage account name.",
            "default": "",
        },
    )

    account_key: str = field(
        default_factory=lambda: Env.get("AZURE_ACCOUNT_KEY", ""),
        metadata={
            "description": "Azure storage account key.",
            "default": "",
        },
    )

    container: str = field(
        default_factory=lambda: Env.get("AZURE_CONTAINER", ""),
        metadata={
            "description": "The blob container name.",
            "default": "",
        },
    )

    url: str | None = field(
        default_factory=lambda: Env.get("AZURE_URL", None),
        metadata={
            "description": "Public base URL used to build file URLs.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the types of the Azure entity attributes.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If any attribute is of the wrong type.
        """
        super().__post_init__()

        # Validate `connection_string` attribute type
        if not isinstance(self.connection_string, str):
            error_msg = "The 'connection_string' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `account_name` attribute type
        if not isinstance(self.account_name, str):
            error_msg = "The 'account_name' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `account_key` attribute type
        if not isinstance(self.account_key, str):
            error_msg = "The 'account_key' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `container` attribute type
        if not isinstance(self.container, str):
            error_msg = "The 'container' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `url` attribute type if not None
        if self.url is not None and not isinstance(self.url, str):
            error_msg = "The 'url' attribute must be a string or None."
            raise TypeError(error_msg)
