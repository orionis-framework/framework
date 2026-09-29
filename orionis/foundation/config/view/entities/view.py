from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import (
    validate_boolean,
    validate_integer,
    validate_string,
)
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class View(BaseEntity):
    """
    Represent view engine configuration for the application.

    Attributes
    ----------
    paths : list
        Ordered list of directory paths searched for templates.
    cache_size : int
        Maximum number of compiled templates kept in the LRU memory cache.
        A value of ``0`` disables the cache; ``-1`` keeps templates without a limit.
    cache_path : str | None
        Optional filesystem path used for Jinja2 bytecode caching.
        ``None`` disables disk-based caching.
    auto_reload : bool
        Reload templates from disk whenever the source file changes.
        Typically ``True`` in development and ``False`` in production.
    autoescape : bool
        Enable automatic HTML escaping of all template variables.
    """

    paths: list[str] | tuple[str, ...] = field(
        default_factory=lambda: Env.get("VIEW_PATHS", ["resources/views"]),
        metadata={
            "description": "Ordered list of directories searched for templates.",
            "default": ["resources/views"],
        },
    )

    cache_size: int = field(
        default_factory=lambda: Env.get("VIEW_CACHE_SIZE", 400),
        metadata={
            "description": (
                "Maximum compiled templates kept in the LRU memory cache. "
                "0 disables the cache; -1 removes the limit."
            ),
            "default": 400,
        },
    )

    cache_path: str | None = field(
        default_factory=lambda: Env.get("VIEW_CACHE_PATH", "storage/framework/views"),
        metadata={
            "description": "Optional filesystem path for Jinja2 bytecode cache.",
            "default": "storage/framework/views",
        },
    )

    auto_reload: bool = field(
        default_factory=lambda: Env.get("APP_DEBUG", True),
        metadata={
            "description": "Reload templates from disk when the source file changes.",
            "default": True,
        },
    )

    autoescape: bool = field(
        default_factory=lambda: Env.get("VIEW_AUTOESCAPE", True),
        metadata={
            "description": "Enable automatic HTML escaping of template variables.",
            "default": True,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate template paths and cache settings without coercing values.

        Returns
        -------
        None
            This method performs validation and normalization and returns None.

        Raises
        ------
        TypeError
            If any of the runner options are of an incorrect type.
        ValueError
            If any of the runner options are invalid.
        """
        super().__post_init__()
        if not isinstance(self.paths, (list, tuple)):
            message = "View 'paths' must be a list or tuple of directory strings."
            raise TypeError(message)
        if not self.paths:
            message = "View 'paths' must contain at least one template directory."
            raise ValueError(message)
        for path in self.paths:
            validate_string(path, "paths")
        if isinstance(self.paths, list):
            object.__setattr__(self, "paths", list(self.paths))
        validate_integer(self.cache_size, "cache_size", minimum=-1)
        if self.cache_path is not None:
            validate_string(self.cache_path, "cache_path")
        validate_boolean(self.auto_reload, "auto_reload")
        validate_boolean(self.autoescape, "autoescape")
