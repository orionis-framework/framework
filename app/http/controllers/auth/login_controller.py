from typing import Any

from orionis.http import HTMLResponse, Request
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

    async def login(self, request: Request) -> HTMLResponse:
        """
        Handle the login form submission.

        Parameters
        ----------
        request : Request
            Incoming request carrying the submitted credentials.

        Returns
        -------
        HTMLResponse
            Rendered login page including the submitted credentials.
        """
        credentials: dict[str, Any] = await request.data()

        print(f"Received credentials: {credentials}")  # Debugging statement

        return await View.make(
            "auth.login",
            email=credentials.get("email", ""),
        )
