from typing import Any
from orionis.http import HTMLResponse, Request, RedirectResponse
from orionis.http.base import BaseController
from orionis.support.facades import View

class LoginController(BaseController):

    async def index(self) -> HTMLResponse:
        """
        Return the login page response.

        Returns
        -------
        HTMLResponse
            Rendered response for the login page.
        """
        return await View.make("auth.login")

    async def login(self, request: Request) -> RedirectResponse:
        """
        Handle the login form submission.

        Parameters
        ----------
        request : Request
            Incoming request carrying the submitted credentials.

        Returns
        -------
        RedirectResponse
            Redirect back to the login page with the submitted email.
        """
        credentials: dict[str, Any] = await request.data()
        remember: bool = credentials.get("remember", "off") == "on"
        email: str = credentials.get("email")

        return (
            RedirectResponse("/login")
                .withCookie("usrname", email if remember else "")
                .withFlash({
                    "email": email,
                })
        )
