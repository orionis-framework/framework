from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.auth import (
    Auth,
    Guards,
    Identity,
    SessionAuth,
    Tokens,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapAppAuth(Auth):

    # Guard applied when a middleware or a facade call does not name one.
    default: Guards | str = field(
        default_factory=lambda: Env.get("AUTH_GUARD", Guards.SESSION),
    )

    # Model backing the authenticated identity, plus the attributes used
    # to look it up and to verify the submitted password.
    identity: Identity | dict = field(
        default_factory=lambda: Identity(
            model=Env.get("AUTH_MODEL", "app.models.user.User"),
            username="email",
        ),
    )

    # Session guard used by the web routes.
    session: SessionAuth | dict = field(
        default_factory=lambda: SessionAuth(
            key="auth_identifier",
            redirect_to=Env.get("AUTH_REDIRECT_TO", "/login"),
            home=Env.get("AUTH_HOME", "/home"),
        ),
    )

    # Personal access token guard used by the API routes.
    tokens: Tokens | dict = field(
        default_factory=lambda: Tokens(
            table="personal_access_tokens",
            expiration=Env.get("AUTH_TOKEN_EXPIRATION", None),
            secret_bytes=40,
        ),
    )
