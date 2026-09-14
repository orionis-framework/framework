from typing import TYPE_CHECKING, ClassVar
from orionis.auth.exceptions import AuthorizationException
from orionis.auth.middleware.resolve_identity import ResolveIdentityMiddleware
from orionis.foundation.config.auth.enums.guards import Guards
from orionis.http.responses import RedirectResponse

if TYPE_CHECKING:
    from orionis.http.layer.contracts.middleware import NextCallable
    from orionis.http.request import Request
    from orionis.http.responses import Response

class GuestMiddleware(ResolveIdentityMiddleware):
    """Keep web login and registration routes restricted to guests."""

    __slots__ = ()

    guard: ClassVar[str | None] = Guards.SESSION.value
    redirect_to: ClassVar[str] = "/"

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """Continue for guests and reject authenticated access to guest routes.

        Parameters
        ----------
        request : Request
            Incoming request.
        call_next : NextCallable
            Remaining route pipeline.

        Returns
        -------
        Response
            Guest response or a browser redirect to the subclass's target.

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
        return RedirectResponse(url=self.redirect_to)
