from typing import TYPE_CHECKING, ClassVar
from orionis.auth.context.functions import current_auth_context
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthenticationException
from orionis.auth.middleware.resolve_identity import ResolveIdentityMiddleware
from orionis.foundation.config.auth.enums.guards import Guards
from orionis.foundation.contracts.application import IApplication
from orionis.http.responses import RedirectResponse

if TYPE_CHECKING:
    from orionis.http.layer.contracts.middleware import NextCallable
    from orionis.http.request import Request
    from orionis.http.responses import Response

# Status used when a browser is sent to the login page instead of
# receiving the plain 401 error document.
_REDIRECT_STATUS: int = 302

class AuthenticateMiddleware(ResolveIdentityMiddleware):
    """Require an authenticated identity before reaching the controller.

    Guests never reach the route handler. Browsers are redirected to the
    page declared in ``auth.session.redirect_to`` when one is configured,
    and every other client receives a ``401`` response produced by the
    standard exception handler.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_redirect_to",)

    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
        """Initialise the middleware with its collaborators.

        Parameters
        ----------
        app : IApplication
            Application exposing the ``auth.session`` configuration.
        manager : IAuthManager
            Manager exposing the configured guards.
        permissions : IPermissionRepository
            Source the authorization snapshot is built from.

        Returns
        -------
        None
            The redirect target is resolved once, at boot time.
        """
        super().__init__(manager, permissions)
        self._redirect_to: str | None = app.config("auth.session.redirect_to")

    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
        """Reject anonymous requests and continue authenticated ones.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.
        call_next : NextCallable
            Callable advancing to the next layer.

        Returns
        -------
        Response
            Response produced by the rest of the pipeline, or a redirect
            to the login page for anonymous browser requests.

        Raises
        ------
        AuthenticationException
            When no identity backs the request and no redirect target is
            configured for browsers.
        """
        context = await self._establish(request)
        if context.isGuest:
            return self._unauthenticated(request)
        return await call_next()

    def _unauthenticated(self, request: Request) -> Response:
        """Build the answer given to an anonymous request.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        Response
            Redirect to the configured login page.

        Raises
        ------
        AuthenticationException
            When the client expects a machine readable answer, or no
            redirect target is configured. The exception is translated
            into a ``401`` response by the framework exception handler.
        """
        redirect_to = self._redirect_to
        if (
            current_auth_context().guard == Guards.SESSION.value
            and redirect_to
            and not (request.wantsJson() or request.isAjax())
        ):
            return RedirectResponse(
                url=redirect_to,
                status_code=_REDIRECT_STATUS,
            )

        error_msg = "Unauthenticated."
        raise AuthenticationException(error_msg)

class AuthenticateSessionMiddleware(AuthenticateMiddleware):
    """Require an identity authenticated through the HTTP session."""

    __slots__ = ()

    guard: ClassVar[str | None] = Guards.SESSION.value

class AuthenticateTokenMiddleware(AuthenticateMiddleware):
    """Require an identity authenticated through a personal access token."""

    __slots__ = ()

    guard: ClassVar[str | None] = Guards.TOKEN.value
