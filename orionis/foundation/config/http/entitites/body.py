from __future__ import annotations
from dataclasses import dataclass
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPBodyLimits(BaseEntity):
    """
    Configure finite request, buffering, multipart and concurrency budgets.

    Attributes
    ----------
    max_body_size : int
        Maximum transport bytes consumed for one request, including framing.
    max_buffer_size : int
        Maximum bytes materialized by body(), JSON and other buffered parsers.
    max_concurrent_requests : int
        Maximum active HTTP requests per kernel, including response delivery.
    max_files : int
        Maximum multipart file count.
    max_fields : int
        Maximum multipart text field count.
    max_part_size : int
        Maximum bytes of one multipart file or field.
    max_field_size : int
        Maximum bytes of one multipart text field before decoding.
    max_header_size : int
        Maximum MIME header bytes per multipart part.
    memory_threshold : int
        Maximum file payload bytes retained before spooling to disk.
    max_memory_size : int
        Budget for retained multipart field strings and in-memory file payloads.
        Transport buffers, object metadata and temporary copies are additional.
    """

    max_body_size: int = 16 * 1024 * 1024
    max_buffer_size: int = 2 * 1024 * 1024
    max_concurrent_requests: int = 128
    max_files: int = 32
    max_fields: int = 128
    max_part_size: int = 10 * 1024 * 1024
    max_field_size: int = 1024 * 1024
    max_header_size: int = 16 * 1024
    memory_threshold: int = 256 * 1024
    max_memory_size: int = 8 * 1024 * 1024

    def __post_init__(self) -> None:
        """
        Reject noninteger, boolean and nonpositive resource limits.

        Returns
        -------
        None
            Validate limits before the HTTP kernel snapshots them.

        Raises
        ------
        TypeError
            If a limit is not an integer or is a boolean.
        ValueError
            If a limit is nonpositive, or a count is negative.
        """
        super().__post_init__()
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                error_msg = f"{name} must be an integer."
                raise TypeError(error_msg)
            minimum = 0 if name in ("max_files", "max_fields") else 1
            if value < minimum:
                error_msg = f"{name} must be at least {minimum}."
                raise ValueError(error_msg)
