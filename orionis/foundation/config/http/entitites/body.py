from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPBodyLimits(BaseEntity):
    """
    Configure finite request, buffering, multipart and concurrency budgets.

    Read environment defaults when each instance is created. Explicit constructor
    values take precedence and every budget remains immutable after validation.

    Attributes
    ----------
    max_body_size : int
        Maximum transport bytes consumed for one request, including framing.
        Defaults to 16 MiB from ``HTTP_MAX_BODY_SIZE``.
    max_buffer_size : int
        Maximum bytes materialized by body(), JSON and other buffered parsers.
        Defaults to 2 MiB from ``HTTP_MAX_BUFFER_SIZE``.
    max_concurrent_requests : int
        Maximum active HTTP requests per kernel, including response delivery.
        Defaults to 128 from ``HTTP_MAX_CONCURRENT_REQUESTS``.
    max_files : int
        Maximum multipart file count; zero rejects all files.
        Defaults to 32 from ``HTTP_MAX_FILES``.
    max_fields : int
        Maximum multipart text field count; zero rejects all text fields.
        Defaults to 128 from ``HTTP_MAX_FIELDS``.
    max_part_size : int
        Maximum bytes of one multipart file or field.
        Defaults to 10 MiB from ``HTTP_MAX_PART_SIZE``.
    max_field_size : int
        Maximum bytes of one multipart text field before decoding.
        Defaults to 1 MiB from ``HTTP_MAX_FIELD_SIZE``.
    max_header_size : int
        Maximum MIME header bytes per multipart part.
        Defaults to 16 KiB from ``HTTP_MAX_PART_HEADER_SIZE``.
    memory_threshold : int
        Maximum file payload bytes retained before spooling to disk.
        Defaults to 256 KiB from ``HTTP_UPLOAD_MEMORY_THRESHOLD``.
    max_memory_size : int
        Budget for retained multipart field strings and in-memory file payloads.
        Transport buffers, object metadata and temporary copies are additional.
        Defaults to 8 MiB from ``HTTP_MAX_MULTIPART_MEMORY_SIZE``.
    """

    max_body_size: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_BODY_SIZE", 16 * 1024 * 1024),
        metadata={
            "description": (
                "Maximum transport bytes per request, including framing."
            ),
            "default": 16 * 1024 * 1024,
        },
    )

    max_buffer_size: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_BUFFER_SIZE", 2 * 1024 * 1024),
        metadata={
            "description": "Maximum bytes materialized by buffered body parsers.",
            "default": 2 * 1024 * 1024,
        },
    )

    max_concurrent_requests: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_CONCURRENT_REQUESTS", 128),
        metadata={
            "description": (
                "Maximum active requests per kernel, including response delivery."
            ),
            "default": 128,
        },
    )

    max_files: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_FILES", 32),
        metadata={
            "description": "Maximum multipart file count; zero rejects all files.",
            "default": 32,
        },
    )

    max_fields: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_FIELDS", 128),
        metadata={
            "description": (
                "Maximum multipart text field count; zero rejects all text fields."
            ),
            "default": 128,
        },
    )

    max_part_size: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_PART_SIZE", 10 * 1024 * 1024),
        metadata={
            "description": "Maximum bytes in one multipart file or text field.",
            "default": 10 * 1024 * 1024,
        },
    )

    max_field_size: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_FIELD_SIZE", 1024 * 1024),
        metadata={
            "description": "Maximum multipart text field bytes before decoding.",
            "default": 1024 * 1024,
        },
    )

    max_header_size: int = field(
        default_factory=lambda: Env.get("HTTP_MAX_PART_HEADER_SIZE", 16 * 1024),
        metadata={
            "description": "Maximum MIME header bytes per multipart part.",
            "default": 16 * 1024,
        },
    )

    memory_threshold: int = field(
        default_factory=lambda: Env.get("HTTP_UPLOAD_MEMORY_THRESHOLD", 256 * 1024),
        metadata={
            "description": "Maximum file payload bytes retained before disk spooling.",
            "default": 256 * 1024,
        },
    )

    max_memory_size: int = field(
        default_factory=lambda: Env.get(
            "HTTP_MAX_MULTIPART_MEMORY_SIZE", 8 * 1024 * 1024,
        ),
        metadata={
            "description": (
                "Budget for retained multipart field strings and in-memory files, "
                "excluding transport buffers, metadata and temporary copies."
            ),
            "default": 8 * 1024 * 1024,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate finite byte budgets and nonnegative multipart counts.

        Returns
        -------
        None
            Validate limits before the HTTP kernel snapshots them.

        Raises
        ------
        TypeError
            If a limit is not an integer or is a boolean.
        ValueError
            If a byte or concurrency limit is nonpositive, or a count is negative.
        """
        super().__post_init__()
        for name in self.__dataclass_fields__:
            minimum = 0 if name in ("max_files", "max_fields") else 1
            validate_integer(getattr(self, name), name, minimum=minimum)
