from typing import TYPE_CHECKING, ClassVar
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthorizationException
from orionis.auth.middleware.resolve_identity import ResolveIdentityMiddleware
from orionis.foundation.config.auth.enums.guards import Guards
from orionis.foundation.contracts.application import IApplication
from orionis.http.responses import RedirectResponse

if TYPE_CHECKING:
    from orionis.http.layer.contracts.middleware import NextCallable
    from orionis.http.request import Request
    from orionis.http.responses import Response

# Target used when ``auth.session.home`` is absent from the configuration.
_DEFAULT_HOME: str = "/home"

class GuestMiddleware(ResolveIdentityMiddleware):
    """
    Keep web login and registration routes restricted to guests.

    Authenticated browsers are sent to the page declared in
    ``auth.session.home``. Subclasses pin a different destination by
    overriding the ``redirect_to`` class attribute.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_home",)

    guard: ClassVar[str | None] = Guards.SESSION.value

    # Explicit destination replacing the configured home page.
    redirect_to: ClassVar[str | None] = None

    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
        """
        Initialise the middleware with its collaborators.

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
        self._home: str = (
            self.redirect_to or app.config("auth.session.home") or _DEFAULT_HOME
        )

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """
        Continue for guests and reject authenticated access to guest routes.

        Parameters
        ----------
        request : Request
            Incoming request.
        call_next : NextCallable
            Remaining route pipeline.

        Returns
        -------
        Response
            Guest response or a browser redirect to the home page.

        Raises
        ------
        AuthorizationException
            If an authenticated JSON or AJAX client accesses a guest-only route.
        """
        context = await self._establish(request)
        if context.isGuest:
            return await call_next()
        if request.wantsJson() or request.isAjax():
            error_msg = "This route is only available to guests."
            raise AuthorizationException(error_msg)
        return RedirectResponse(url=self._home)
