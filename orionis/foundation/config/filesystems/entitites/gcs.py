from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class GCS(BaseEntity):
    """
    Represent a Google Cloud Storage configuration.

    Using this disk requires the official Google Cloud client
    library, which is an optional dependency: install it with
    ``pip install google-cloud-storage`` (or ``pip install
    orionis[gcs]``).

    Parameters
    ----------
    driver : str, default="gcs"
        The filesystem driver type. Default is "gcs".
    project_id : str
        Google Cloud project identifier.
    key_file : str | None, default=None
        Path to the service-account JSON key file. When omitted,
        Application Default Credentials are used.
    bucket : str
        The GCS bucket name.
    url : str | None, default=None
        Public base URL used to build file URLs.

    Returns
    -------
    None
        This class does not return a value.
    """

    driver: str = field(
        default="gcs",
        metadata={
            "description": "The filesystem driver type.",
            "default": "gcs",
        },
    )

    project_id: str = field(
        default_factory=lambda: Env.get("GCS_PROJECT_ID", ""),
        metadata={
            "description": "Google Cloud project identifier.",
            "default": "",
        },
    )

    key_file: str | None = field(
        default_factory=lambda: Env.get("GCS_KEY_FILE", None),
        metadata={
            "description": "Path to the service-account JSON key file.",
            "default": None,
        },
    )

    bucket: str = field(
        default_factory=lambda: Env.get("GCS_BUCKET", ""),
        metadata={
            "description": "The GCS bucket name.",
            "default": "",
        },
    )

    url: str | None = field(
        default_factory=lambda: Env.get("GCS_URL", None),
        metadata={
            "description": "Public base URL used to build file URLs.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the types of the GCS entity attributes.

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

        # Validate `project_id` attribute type
        if not isinstance(self.project_id, str):
            error_msg = "The 'project_id' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `key_file` attribute type if not None
        if self.key_file is not None and not isinstance(self.key_file, str):
            error_msg = "The 'key_file' attribute must be a string or None."
            raise TypeError(error_msg)

        # Validate `bucket` attribute type
        if not isinstance(self.bucket, str):
            error_msg = "The 'bucket' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `url` attribute type if not None
        if self.url is not None and not isinstance(self.url, str):
            error_msg = "The 'url' attribute must be a string or None."
            raise TypeError(error_msg)
