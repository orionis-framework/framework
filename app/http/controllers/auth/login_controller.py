from typing import Any
from app.http.schemas.auth.login import LoginSchema
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

    async def login(self, request: Request, payload: LoginSchema) -> HttpResponse:
        """
        Handle the login form submission.

        Parameters
        ----------
        request : Request
            Incoming HTTP request, used to read the raw submitted payload.
        payload : LoginSchema
            Validated credentials; invalid submissions never reach this method.

        Returns
        -------
        HttpResponse
            Redirect back to the login page, carrying the submitted input
            plus a success message.
        """
        url: str = "/login"

        credentials: dict[str, Any] = await request.data()
        remember: bool = credentials.get("remember", "off") == "on"
        value_cookie: str = payload.email if remember else ""
        max_age_cookie: int = 3600 if remember else 0

        return (
            response.redirect(url)
                .withCookie("usrname", value_cookie, max_age=max_age_cookie)
                .withInput(credentials)
                .withFlash("success", "Credentials received.")
        )
