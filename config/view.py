from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.view import View

@dataclass(frozen=True, kw_only=True)
class BootstrapView(View):
    # ----------------------------------------------------------------------------------
    # paths : list[str] | tuple[str, ...], optional
    # --- Directories searched for templates in priority order.
    # ----------------------------------------------------------------------------------
    paths: list[str] | tuple[str, ...] = field(
        default_factory=lambda: Env.get("VIEW_PATHS", ["resources/views"]),
    )

    # ----------------------------------------------------------------------------------
    # cache_size : int, optional
    # --- Maximum compiled templates held in the LRU memory cache.
    # ----------------------------------------------------------------------------------
    cache_size: int = field(
        default_factory=lambda: Env.get("VIEW_CACHE_SIZE", 400),
    )

    # ----------------------------------------------------------------------------------
    # cache_path : str | None, optional
    # --- Filesystem path for bytecode caching (None disables disk cache).
    # ----------------------------------------------------------------------------------
    cache_path: str | None = field(
        default_factory=lambda: Env.get("VIEW_CACHE_PATH", "storage/framework/views"),
    )

    # ----------------------------------------------------------------------------------
    # auto_reload : bool, optional
    # --- Check for template changes while application debugging is enabled.
    # ----------------------------------------------------------------------------------
    auto_reload: bool = field(
        default_factory=lambda: Env.get("APP_DEBUG", True),
    )

    # ----------------------------------------------------------------------------------
    # autoescape : bool, optional
    # --- Enable automatic HTML escaping of all template variables.
    # ----------------------------------------------------------------------------------
    autoescape: bool = field(
        default_factory=lambda: Env.get("VIEW_AUTOESCAPE", True),
    )
