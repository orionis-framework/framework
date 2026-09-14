from typing import TYPE_CHECKING, ClassVar
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import (
    authentication_lock,
    bind_auth_context,
    current_auth_context,
)
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthenticationException
from orionis.http.middleware import BaseMiddleware

if TYPE_CHECKING:
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.http.layer.contracts.middleware import NextCallable
    from orionis.http.request import Request
    from orionis.http.responses import Response

class ResolveIdentityMiddleware(BaseMiddleware):
    """Establish authentication while allowing anonymous requests to continue.

    Register it globally when public pages need to know who is browsing
    them. Guests simply reach the controller with a guest context, and
    ``Auth.check()`` answers ``False``.

    An authenticated context cannot be replaced by another guard. Repeated
    resolution by the same guard reuses the context, including guest results.

    Subclasses pin a specific guard by overriding the ``guard`` class
    attribute::

        class ResolveApiIdentity(ResolveIdentityMiddleware):
            guard = "token"
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_manager", "_permissions")

    # Guard used to resolve the identity. ``None`` uses the configured
    # default guard.
    guard: ClassVar[str | None] = None

    def __init__(
        self,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
        """Initialise the middleware with its collaborators.

        Parameters
        ----------
        manager : IAuthManager
            Manager exposing the configured guards.
        permissions : IPermissionRepository
            Source the authorization snapshot is built from.

        Returns
        -------
        None
            Middleware instances are built once at boot and stay
            stateless afterwards.
        """
        self._manager = manager
        self._permissions = permissions

    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
        """Bind the authentication context and continue the pipeline.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : NextCallable
            Callable advancing to the next layer.

        Returns
        -------
        Response
            Response produced by the rest of the pipeline.
        """
        await self._establish(request)
        return await call_next()

    async def _establish(self, request: Request) -> IAuthenticationContext:
        """Resolve the identity and bind the resulting context.

        The context is stored in the container scope opened by the HTTP
        kernel, never on this middleware: instances are shared by every
        concurrent request.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        IAuthenticationContext
            Context bound for the rest of the request.
        """
        async with authentication_lock():
            guard = self._manager.guard(self.guard)
            context = current_auth_context()
            if context.guard == guard.name:
                return context
            if context.isAuthenticated:
                error_msg = "An authenticated request cannot switch guards."
                raise AuthenticationException(error_msg)
            result = await guard.resolve(request)

            if result is None:
                context = AuthenticationContext(guard=guard.name)
            else:
                context = AuthenticationContext(
                    identity=result.identity,
                    guard=result.guard,
                    abilities=result.abilities,
                    repository=self._permissions,
                    credential_id=result.credential_id,
                )

            bind_auth_context(context)
            return context
