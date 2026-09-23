from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.auth.contracts.manager import IAuthManager
from orionis.http import HTMLResponse, response
from orionis.http.base import BaseController

class HomeController(BaseController):

    async def home(
        self,
        auth: IAuthManager,
    ) -> HTMLResponse:
        """
        Render the authenticated home page response.

        Parameters
        ----------
        auth : IAuthManager
            Authentication service bound to the current request.

        Returns
        -------
        HTMLResponse
            The rendered home page for the signed-in user.
        """
        identity: IAuthenticatable | None = auth.user()
        return await response.view(
            "home.index",
            user={"name": identity.name, "email": identity.email},
        )
