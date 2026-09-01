from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class S3(BaseEntity):
    """
    Represent an AWS S3 storage configuration.

    Parameters
    ----------
    driver : str, default="aws"
        The filesystem driver type. Default is "aws".
    key : str
        AWS access key ID.
    secret : str
        AWS secret access key.
    region : str
        AWS region where the bucket is located.
    bucket : str
        The S3 bucket name.
    url : str | None, default=None
        The URL endpoint for accessing the S3 bucket.
    endpoint : str | None, default=None
        The AWS S3 endpoint URL.
    use_path_style_endpoint : bool, default=False
        Whether to use a path-style endpoint.

    Returns
    -------
    None
        This class does not return a value.
    """

    driver: str = field(
        default="aws",
        metadata={
            "description": "The filesystem driver type.",
            "default": "aws",
        },
    )

    key: str = field(
        default_factory=lambda: Env.get("S3_KEY", ""),
        metadata={
            "description": "AWS access key ID.",
            "default": "",
        },
    )

    secret: str = field(
        default_factory=lambda: Env.get("S3_SECRET", ""),
        metadata={
            "description": "AWS secret access key.",
            "default": "",
        },
    )

    region: str = field(
        default_factory=lambda: Env.get("S3_REGION", "us-east-1"),
        metadata={
            "description": "AWS region where the bucket is located.",
            "default": "us-east-1",
        },
    )

    bucket: str = field(
        default_factory=lambda: Env.get("S3_BUCKET", ""),
        metadata={
            "description": "The S3 bucket name.",
            "default": "",
        },
    )

    url: str | None = field(
        default_factory=lambda: Env.get("S3_URL", None),
        metadata={
            "description": "The URL endpoint for accessing the S3 bucket.",
            "default": None,
        },
    )

    endpoint: str | None = field(
        default_factory=lambda: Env.get("S3_ENDPOINT", None),
        metadata={
            "description": "The AWS S3 endpoint URL.",
            "default": None,
        },
    )

    use_path_style_endpoint: bool = field(
        default_factory=lambda: Env.get("S3_USE_PATH_STYLE_ENDPOINT", False),
        metadata={
            "description": "Whether to use a path-style endpoint.",
            "default": False,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate initialization of AWS filesystem entity attributes.

        Ensures all required attributes are of correct type and, where applicable,
        are non-empty.

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
        ValueError
            If any required attribute is empty.
        """
        super().__post_init__()

        # Validate `key` attribute type
        if not isinstance(self.key, str):
            error_msg = "The 'key' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `secret` attribute type
        if not isinstance(self.secret, str):
            error_msg = "The 'secret' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `region` attribute type and non-empty value
        if not isinstance(self.region, str):
            error_msg = "The 'region' attribute must be a string."
            raise TypeError(error_msg)
        if not self.region:
            error_msg = "The 'region' attribute must be a non-empty string."
            raise ValueError(error_msg)

        # Validate `bucket` attribute type
        if not isinstance(self.bucket, str):
            error_msg = "The 'bucket' attribute must be a string."
            raise TypeError(error_msg)

        # Validate `url` attribute type if not None
        if self.url is not None and not isinstance(self.url, str):
            error_msg = "The 'url' attribute must be a string or None."
            raise TypeError(error_msg)

        # Validate `endpoint` attribute type if not None
        if self.endpoint is not None and not isinstance(self.endpoint, str):
            error_msg = "The 'endpoint' attribute must be a string or None."
            raise TypeError(error_msg)

        # Validate `use_path_style_endpoint` attribute type
        if not isinstance(self.use_path_style_endpoint, bool):
            error_msg = (
                "The 'use_path_style_endpoint' attribute must be a boolean."
            )
            raise TypeError(error_msg)
