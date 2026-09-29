from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.auth import (
    Auth, Guards, Identity, PasswordReset, RememberAuth, SessionAuth, Tokens,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapAppAuth(Auth):
    # ----------------------------------------------------------------------------------
    # default : Guards | str, optional
    # --- Guard applied when a middleware or a facade call does not name one.
    # --- Defaults to the value of the 'AUTH_GUARD' environment variable or
    # --- Guards.SESSION.
    # ----------------------------------------------------------------------------------
    default: Guards | str = field(
        default_factory=lambda: Env.get("AUTH_GUARD", Guards.SESSION),
    )

    # ----------------------------------------------------------------------------------
    # identity : Identity | dict, optional
    # --- Model backing the authenticated identity, plus the attributes used to look it
    # --- up and to verify the submitted password. Defaults to the value of the
    # --- 'AUTH_MODEL' environment variable or 'app.models.user.User'.
    # ----------------------------------------------------------------------------------
    identity: Identity | dict = field(
        default_factory=lambda: Identity(
            model=Env.get("AUTH_MODEL", "app.models.user.User"),
            username=Env.get("AUTH_USERNAME", "email"),
        ),
    )

    # ----------------------------------------------------------------------------------
    # session : SessionAuth | dict, optional
    # --- Session guard used by the web routes. Defaults to the values of the
    # --- 'AUTH_REDIRECT_TO' and 'AUTH_HOME' environment variables or '/login' and
    # --- '/home'.
    # ----------------------------------------------------------------------------------
    session: SessionAuth | dict = field(
        default_factory=lambda: SessionAuth(
            key=Env.get("AUTH_SESSION_KEY", "_auth_identifier"),
            redirect_to=Env.get("AUTH_REDIRECT_TO", "/login"),
            home=Env.get("AUTH_HOME", "/home"),
        ),
    )

    # ----------------------------------------------------------------------------------
    # tokens : Tokens | dict, optional
    # --- Personal access token guard used by the API routes. Defaults to the value of
    # --- the 'AUTH_TOKEN_EXPIRATION' environment variable or None.
    # ----------------------------------------------------------------------------------
    tokens: Tokens | dict = field(
        default_factory=lambda: Tokens(
            table=Env.get("AUTH_TOKEN_TABLE", "personal_access_tokens"),
            expiration=Env.get("AUTH_TOKEN_EXPIRATION", None),
            secret_bytes=Env.get("AUTH_TOKEN_SECRET_BYTES", 40),
        ),
    )

    # ----------------------------------------------------------------------------------
    # passwords : PasswordReset | dict, optional
    # --- Link lifetime in minutes, resend delay in seconds and token table.
    # --- The reset link origin comes from request.baseUrl.
    # ----------------------------------------------------------------------------------
    passwords: PasswordReset | dict = field(
        default_factory=lambda: PasswordReset(
            expiration=Env.get("AUTH_PASSWORD_RESET_EXPIRATION", 60),
            throttle=Env.get("AUTH_PASSWORD_RESET_THROTTLE", 60),
            table=Env.get("AUTH_PASSWORD_RESET_TABLE", "password_reset_tokens"),
        ),
    )

    # ----------------------------------------------------------------------------------
    # remember : RememberAuth | dict, optional
    # --- Persistent login is opt-in at login and uses an HttpOnly, host-only cookie.
    # --- Defaults to the values of the 'AUTH_REMEMBER_LIFETIME' and
    # --- 'AUTH_REMEMBER_SECURE' environment variables or 43200 and True.
    # ----------------------------------------------------------------------------------
    remember: RememberAuth | dict = field(
        default_factory=lambda: RememberAuth(
            cookie=Env.get("AUTH_REMEMBER_COOKIE", "orionis_remember"),
            lifetime=Env.get("AUTH_REMEMBER_LIFETIME", 43200),
            secure=Env.get("AUTH_REMEMBER_SECURE", False),
        ),
    )
