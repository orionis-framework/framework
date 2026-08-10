from typing import Any

from orionis.http import HTMLResponse, Request
from orionis.http.base import BaseController
from orionis.support.facades import View

class RegisterController(BaseController):

    async def index(self) -> HTMLResponse:
        """
        Return the registration page response.

        Returns
        -------
        HTMLResponse
            Rendered response for the registration page.
        """
        return await View.make("auth.register")

    async def register(self, request: Request) -> HTMLResponse:
        """
        Handle the registration form submission.

        Parameters
        ----------
        request : Request
            Incoming request carrying the submitted account data.

        Returns
        -------
        HTMLResponse
            Rendered registration page including the submitted data.
        """
        account: dict[str, Any] = await request.data()

        return await View.make(
            "auth.register",
            name=account.get("name", ""),
            email=account.get("email", ""),
        )
