from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.filesystems.entitites.aws import S3
from orionis.foundation.config.filesystems.entitites.azure import Azure
from orionis.foundation.config.filesystems.entitites.gcs import GCS
from orionis.foundation.config.filesystems.entitites.local import Local
from orionis.foundation.config.filesystems.entitites.public import Public
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Disks(BaseEntity):
    """
    Represent the configuration for different filesystem disks.

    Attributes
    ----------
    local : Local | dict
        The disk configuration for local file storage.
    public : Public | dict
        The disk configuration for public file storage.
    s3 : S3 | dict
        The configuration for AWS S3 storage.
    azure : Azure | dict
        The configuration for Azure Blob Storage.
    gcs : GCS | dict
        The configuration for Google Cloud Storage.
    """

    local: Local | dict = field(
        default_factory=Local,
        metadata={
            "description": (
                "The absolute or relative path where local files are stored."
            ),
            "default": lambda: Local().toDict(),
        },
    )

    public: Public | dict = field(
        default_factory=Public,
        metadata={
            "description": (
                "The absolute or relative path where public files are stored."
            ),
            "default": lambda: Public().toDict(),
        },
    )

    s3: S3 | dict = field(
        default_factory=S3,
        metadata={
            "description": "The configuration for AWS S3 storage.",
            "default": lambda: S3().toDict(),
        },
    )

    azure: Azure | dict = field(
        default_factory=Azure,
        metadata={
            "description": "The configuration for Azure Blob Storage.",
            "default": lambda: Azure().toDict(),
        },
    )

    gcs: GCS | dict = field(
        default_factory=GCS,
        metadata={
            "description": "The configuration for Google Cloud Storage.",
            "default": lambda: GCS().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate and convert disk attributes after initialization.

        Ensures every disk attribute is an instance of its respective
        entity class, converting from a dictionary when necessary.

        Parameters
        ----------
        self : Disks
            The instance of the Disks class.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call the superclass post-init method
        super().__post_init__()

        # Validate and convert every disk attribute in a single pass
        conversions: tuple[tuple[str, type], ...] = (
            ("local", Local),
            ("public", Public),
            ("s3", S3),
            ("azure", Azure),
            ("gcs", GCS),
        )
        for name, entity in conversions:
            value = getattr(self, name)
            if not isinstance(value, (entity, dict)):
                error_msg = (
                    f"The '{name}' attribute must be a {entity.__name__} "
                    "object or a dictionary."
                )
                raise TypeError(error_msg)
            if isinstance(value, dict):
                object.__setattr__(self, name, entity(**value))
