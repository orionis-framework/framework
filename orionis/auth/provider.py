from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.authorization.repository import DatabasePermissionRepository
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.contracts.session_guard import ISessionGuard
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.manager import AuthManager
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.auth import Auth as AuthFacade

class AuthProvider(ServiceProvider):
    """Service provider wiring the authentication module.

    The provider is deliberately eager: ``Auth.user()``, ``Auth.check()``
    and ``Auth.guest()`` are synchronous and are called from templates and
    controllers without ``await``. A deferred provider would leave the
    facade unpinned, and the first access would return a dispatcher
    instead of the manager.
    """

    def register(self) -> None:
        """Bind stateless services and the request-scoped authentication context.

        Guards, repositories and the authorizer hold no per request
        state, so a single shared instance is safe. Everything that
        belongs to a request lives in the authentication context, which
        the HTTP kernel scopes with ``contextvars``.

        Returns
        -------
        None
            The container is populated as a side effect.
        """
        # Identity resolution and password verification.
        self.app.scoped(IAuthenticationContext, AuthenticationContext)
        self.app.singleton(IIdentityProvider, ModelIdentityProvider)

        # Authorization sources.
        self.app.singleton(IPermissionRepository, DatabasePermissionRepository)
        self.app.singleton(IAuthorizer, Authorizer)
        self.app.singleton(PermissionRegistrar, PermissionRegistrar)

        # Credentials.
        self.app.singleton(IAccessTokenRepository, AccessTokenRepository)
        self.app.singleton(ISessionGuard, SessionGuard)
        self.app.singleton(TokenGuard, TokenGuard)

        # Public entry point backing the ``Auth`` facade.
        self.app.singleton(IAuthManager, AuthManager)

    async def boot(self) -> None:
        """Pin the Auth facade once every service is registered.

        Returns
        -------
        None
            Attribute access on the facade becomes a direct passthrough.
        """
        await AuthFacade.pin()
