from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.env import Env
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
        A value of ``0`` disables the cache entirely.
    cache_path : str | None
        Optional filesystem path used for Jinja2 bytecode caching.
        ``None`` disables disk-based caching.
    auto_reload : bool
        Reload templates from disk whenever the source file changes.
        Typically ``True`` in development and ``False`` in production.
    autoescape : bool
        Enable automatic HTML escaping of all template variables.
    """

    paths: list = field(
        default_factory=lambda: Env.get("VIEW_PATHS", ["resources/views"]),
        metadata={
            "description": "Ordered list of directories searched for templates.",
            "default": ["resources/views"],
        },
    )

    cache_size: int = field(
        default_factory=lambda: int(Env.get("VIEW_CACHE_SIZE", 400)),
        metadata={
            "description": (
                "Maximum compiled templates kept in the LRU memory cache. "
                "0 disables the cache."
            ),
            "default": 400,
        },
    )

    cache_path: str | None = field(
        default_factory=lambda: Env.get("VIEW_CACHE_PATH", None),
        metadata={
            "description": "Optional filesystem path for Jinja2 bytecode cache.",
            "default": None,
        },
    )

    auto_reload: bool = field(
        default_factory=lambda: bool(Env.get("APP_DEBUG", True)),
        metadata={
            "description": "Reload templates from disk when the source file changes.",
            "default": True,
        },
    )

    autoescape: bool = field(
        default_factory=lambda: bool(Env.get("VIEW_AUTOESCAPE", True)),
        metadata={
            "description": "Enable automatic HTML escaping of template variables.",
            "default": True,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate view configuration fields after dataclass initialisation.

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If any field carries an unexpected type.
        ValueError
            If ``paths`` is empty or ``cache_size`` is negative.
        """
        super().__post_init__()

        if not isinstance(self.paths, (list, tuple)):
            error_msg = "View 'paths' must be a list or tuple of directory strings."
            raise TypeError(error_msg)

        if not self.paths:
            error_msg = "View 'paths' must contain at least one template directory."
            raise ValueError(error_msg)

        if not isinstance(self.cache_size, int) or self.cache_size < 0:
            error_msg = "View 'cache_size' must be a non-negative integer."
            raise ValueError(error_msg)

        if self.cache_path is not None and not isinstance(self.cache_path, str):
            error_msg = "View 'cache_path' must be a string or None."
            raise TypeError(error_msg)

        if not isinstance(self.auto_reload, bool):
            error_msg = "View 'auto_reload' must be a boolean."
            raise TypeError(error_msg)

        if not isinstance(self.autoescape, bool):
            error_msg = "View 'autoescape' must be a boolean."
            raise TypeError(error_msg)
