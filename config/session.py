from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.session import (
    SameSitePolicy,
    Session,
    SessionDriver,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapSession(Session):
    # ----------------------------------------------------------------------------------
    # driver : str | SessionDriver, optional
    # --- Session driver.
    # --- Defaults to SessionDriver.MEMORY.
    # ----------------------------------------------------------------------------------
    driver: str | SessionDriver = field(
        default_factory=lambda: Env.get("SESSION_DRIVER", SessionDriver.MEMORY),
    )

    # ----------------------------------------------------------------------------------
    # lifetime : int, optional
    # --- Session lifetime in minutes.
    # --- Defaults to 120.
    # ----------------------------------------------------------------------------------
    lifetime: int = field(
        default_factory=lambda: Env.get("SESSION_LIFETIME", 120),
    )

    # ----------------------------------------------------------------------------------
    # expire_on_close : bool, optional
    # --- Expire session on browser close (omits Max-Age).
    # --- Defaults to False.
    # ----------------------------------------------------------------------------------
    expire_on_close: bool = field(
        default_factory=lambda: Env.get("SESSION_EXPIRE_ON_CLOSE", False),
    )

    # ----------------------------------------------------------------------------------
    # files : str | None, optional
    # --- Path to session files (file driver).
    # --- Defaults to 'storage/framework/sessions'.
    # ----------------------------------------------------------------------------------
    files: str | None = field(
        default_factory=lambda: Env.get("SESSION_FILES", "storage/framework/sessions"),
    )

    # ----------------------------------------------------------------------------------
    # connection : str | None, optional
    # --- Database connection for session storage (database driver).
    # --- Defaults to None.
    # ----------------------------------------------------------------------------------
    connection: str | None = field(
        default_factory=lambda: Env.get("SESSION_DB_CONNECTION", None),
    )

    # ----------------------------------------------------------------------------------
    # table : str | None, optional
    # --- Database table for session storage (database driver).
    # --- Defaults to 'sessions'.
    # ----------------------------------------------------------------------------------
    table: str | None = field(
        default_factory=lambda: Env.get("SESSION_DB_TABLE", "sessions"),
    )

    # ----------------------------------------------------------------------------------
    # cache : str | None, optional
    # --- Cache store for session storage (cache driver).
    # --- Defaults to None.
    # ----------------------------------------------------------------------------------
    cache: str | None = field(
        default_factory=lambda: Env.get("SESSION_CACHE_STORE", None),
    )

    # ----------------------------------------------------------------------------------
    # cookie : str, optional
    # --- Name of the session cookie.
    # --- Defaults to 'sessionid'.
    # ----------------------------------------------------------------------------------
    cookie: str = field(
        default_factory=lambda: Env.get("SESSION_COOKIE", "sessionid"),
    )

    # ----------------------------------------------------------------------------------
    # path : str, optional
    # --- Path for the session cookie.
    # --- Defaults to '/'.
    # ----------------------------------------------------------------------------------
    path: str = field(
        default_factory=lambda: Env.get("SESSION_PATH", "/"),
    )

    # ----------------------------------------------------------------------------------
    # domain : str | None, optional
    # --- Domain for the session cookie.
    # --- None means cookie is valid for current domain only.
    # ----------------------------------------------------------------------------------
    domain: str | None = field(
        default_factory=lambda: Env.get("SESSION_DOMAIN", None),
    )

    # ----------------------------------------------------------------------------------
    # secure : bool, optional
    # --- Restricts session cookie to HTTPS if True.
    # --- Must be True if same_site is 'none'.
    # --- Defaults to False.
    # ----------------------------------------------------------------------------------
    secure: bool = field(
        default_factory=lambda: Env.get("SESSION_SECURE", False),
    )

    # ----------------------------------------------------------------------------------
    # http_only : bool, optional
    # --- Prevent JavaScript from accessing the cookie.
    # --- Defaults to True.
    # ----------------------------------------------------------------------------------
    http_only: bool = field(
        default_factory=lambda: Env.get("SESSION_HTTP_ONLY", True),
    )

    # ----------------------------------------------------------------------------------
    # same_site : str | SameSitePolicy, optional
    # --- SameSite cookie policy: 'lax', 'strict', or 'none'.
    # --- If 'none', secure must be True.
    # ----------------------------------------------------------------------------------
    same_site: str | SameSitePolicy = field(
        default_factory=lambda: Env.get("SESSION_SAME_SITE", SameSitePolicy.LAX.value),
    )

    # ----------------------------------------------------------------------------------
    # partitioned : bool, optional
    # --- Enable CHIPS (partitioned) cookies.
    # --- Defaults to False.
    # ----------------------------------------------------------------------------------
    partitioned: bool = field(
        default_factory=lambda: Env.get("SESSION_PARTITIONED", False),
    )
