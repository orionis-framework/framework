from typing import Any
from app.http.schemas.auth.login import LoginSchema
from orionis.auth.contracts.manager import IAuthManager
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.request import Request

class LoginController(BaseController):

    async def index(self) -> HttpResponse:
        """
        Return the login page response.

        Returns
        -------
        HttpResponse
            Rendered response for the login page.
        """
        return await response.view("auth.login")

    async def login(
        self,
        request: Request,
        payload: LoginSchema,
        auth: IAuthManager,
    ) -> HttpResponse:
        """
        Handle the login form submission.

        Parameters
        ----------
        request : Request
            Incoming HTTP request, used to read the raw submitted payload.
        payload : LoginSchema
            Validated credentials; invalid submissions never reach this method.
        auth : IAuthManager
            Authentication service using the request's existing session.

        Returns
        -------
        HttpResponse
            Redirect home on success, or back with a generic credential error.
        """
        credentials: dict[str, Any] = await request.data()
        authenticated = await auth.attempt({
            "email": payload.email, "password": payload.password,
        })
        if not authenticated:
            return (
                response.redirect("/login")
                .withInput(credentials)
                .withErrors({"email": "These credentials do not match our records."})
            )

        remember: bool = credentials.get("remember", "off") == "on"
        value_cookie: str = payload.email if remember else ""
        max_age_cookie: int = 3600 if remember else 0

        return (
            response.redirect("/")
                .withCookie("usrname", value_cookie, max_age=max_age_cookie)
        )

    async def logout(self, auth: IAuthManager) -> HttpResponse:
        """Invalidate the current session and return to the login page.

        Parameters
        ----------
        auth : IAuthManager
            Authentication service bound to the current request.

        Returns
        -------
        HttpResponse
            Redirect whose session cookie is cleared by the web middleware.
        """
        await auth.logout()
        return response.redirect("/login")
