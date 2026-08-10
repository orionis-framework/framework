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
            Redirect back to the login page, carrying the submitted input
            plus either the field errors or a success message.
        """
        url: str = "/login"

        credentials: dict[str, Any] = await request.data()
        email: str = credentials.get("email", "")
        password: str = credentials.get("password", "")

        errors: dict[str, str] = {}
        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."  # noqa: S105

        # withInput() repopulates the form; withErrors() feeds the errors bag.
        if errors:
            return (
                RedirectResponse(url)
                    .withInput(credentials)
                    .withErrors(errors)
            )

        remember: bool = credentials.get("remember", "off") == "on"
        value_cookie: str = email if remember else ""
        max_age_cookie: int = 3600 if remember else 0

        return (
            RedirectResponse(url)
                .withCookie("usrname", value_cookie, max_age=max_age_cookie)
                .withInput(credentials)
                .withFlash("success", "Credentials received.")
        )
