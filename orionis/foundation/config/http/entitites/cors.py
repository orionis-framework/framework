from __future__ import annotations
import re
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import (
    copy_string_list,
    validate_boolean,
    validate_integer,
    validate_string,
)
from orionis.support.entities.base import BaseEntity

# Module-level frozenset: avoids recreating the set per __validateAllowMethods call.
_ALLOWED_HTTP_METHODS: frozenset[str] = frozenset(
    {"GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "QUERY"},
)

@dataclass(frozen=True, kw_only=True)
class Cors(BaseEntity):
    """
    Represent a CORS configuration compatible with Starlette CORSMiddleware.

    Attributes
    ----------
    allow_origins : list[str]
        List of allowed origins. Defaults to []. Use ["*"] to allow all origins.
    allow_origin_regex : str | None
        Regular expression to match allowed origins. Defaults to None.
    allow_methods : list[str]
        List of allowed HTTP methods. Defaults to []. Use ["*"] to allow all methods.
    allow_headers : list[str]
        List of allowed HTTP headers. Defaults to []. Use ["*"] to allow all headers.
    expose_headers : list[str]
        List of headers exposed to the browser. Defaults to [].
    allow_credentials : bool
        Whether to allow credentials (cookies, authorization headers, etc.).
        Defaults to False.
    max_age : int | None
        Maximum time (in seconds) for the preflight request to be cached.
        Defaults to 600.
    """

    allow_origins: list[str] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_ORIGINS", []),
        metadata={
            "description": 'List of allowed origins. Use ["*"] to allow all origins.',
            "default": [],
        },
    )

    allow_origin_regex: str | None = field(
        default_factory=lambda: Env.get("CORS_ALLOW_ORIGIN_REGEX", None),
        metadata={
            "description": "Regular expression pattern to match allowed origins.",
            "default": None,
        },
    )

    allow_methods: list[str] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_METHODS", []),
        metadata={
            "description": (
                'List of allowed HTTP methods. Use ["*"] to allow all methods.'
            ),
            "default": [],
        },
    )

    allow_headers: list[str] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_HEADERS", []),
        metadata={
            "description": (
                'List of allowed HTTP headers. Use ["*"] to allow all headers.'
            ),
            "default": [],
        },
    )

    expose_headers: list[str] = field(
        default_factory=lambda: Env.get("CORS_EXPOSE_HEADERS", []),
        metadata={
            "description": "List of headers exposed to the browser.",
            "default": [],
        },
    )

    allow_credentials: bool = field(
        default_factory=lambda: Env.get("CORS_ALLOW_CREDENTIALS", False),
        metadata={
            "description": (
                "Whether to allow credentials (cookies, authorization headers, etc.)."
            ),
            "default": False,
        },
    )

    max_age: int | None = field(
        default_factory=lambda: Env.get("CORS_MAX_AGE", 600),
        metadata={
            "description": "Maximum time (in seconds) for preflight request caching.",
            "default": 600,
        },
    )

    def __validateAllowMethods(self) -> None:
        """
        Validate that all items in 'allow_methods' are valid HTTP methods or a wildcard.

        Checks that each entry in 'allow_methods' is a string and matches a valid HTTP
        method or is the wildcard '*'. Raises a TypeError or ValueError if invalid.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If any item in 'allow_methods' is not a string.
        ValueError
            If any item is not a valid HTTP method or the wildcard.
        """
        # Validate each method against the pre-cached module-level frozenset
        if self.allow_methods != ["*"]:
            for method in self.allow_methods:
                if not isinstance(method, str):
                    error_msg = (
                        f"Invalid type in 'allow_methods': {method!r} is not a string."
                    )
                    raise TypeError(error_msg)
                if method.upper() not in _ALLOWED_HTTP_METHODS:
                    error_msg = (
                        f"Invalid HTTP method in 'allow_methods': {method!r}. "
                        f"Allowed methods are {sorted(_ALLOWED_HTTP_METHODS)}."
                    )
                    raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate CORS options and own the supplied mutable lists.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__post_init__()
        for name in (
            "allow_origins",
            "allow_methods",
            "allow_headers",
            "expose_headers",
        ):
            object.__setattr__(self, name, copy_string_list(getattr(self, name), name))
        self.__validateAllowMethods()
        validate_boolean(self.allow_credentials, "allow_credentials")
        if self.max_age is not None:
            validate_integer(self.max_age, "max_age")
        if self.allow_origin_regex is not None:
            validate_string(
                self.allow_origin_regex,
                "allow_origin_regex",
                allow_empty=True,
            )
            try:
                re.compile(self.allow_origin_regex)
            except re.error as exc:
                message = "'allow_origin_regex' must be a valid regular expression."
                raise ValueError(message) from exc
