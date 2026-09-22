from typing import Any

from orionis.auth.contracts.manager import IAuthManager
from orionis.foundation.contracts.application import IApplication
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.default.schemas.login import LoginSchema
from orionis.http.request import Request


class LoginController(BaseController):

    # ruff: noqa: TC001

    HOME_REDIRECT_PATH: str = "/home"
    DEFAULT_LOGIN_PATH: str = "/login"
    LOGOUT_REDIRECT_PATH: str = "/"
    LOGIN_VIEW_NAME: str = "auth.login"
    REMEMBER_COOKIE_MAX_AGE: int = 259200
    REMEMBER_COOKIE_NAME: str = "usrname"

    def __init__(
        self,
        application: IApplication,
    ) -> None:
        """
        Configure the controller from the session authentication settings.

        Web login uses the session guard through ``Auth.attempt()`` regardless
        of the guard configured as the application's default.

        Parameters
        ----------
        application : IApplication
            Application instance used to read the ``auth`` configuration.

        """
        # Cache the destination used after a valid session login.
        self.redirect_to: str = (
            application.config("auth.session.home") or self.HOME_REDIRECT_PATH
        )

    async def index(
        self,
    ) -> HttpResponse:
        """
        Return the login page response.

        Returns
        -------
        HttpResponse
            Rendered response for the login page.
        """
        # Render the template through the view factory.
        return await response.view(self.LOGIN_VIEW_NAME)

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
            Redirect to the dashboard, or back with a generic credential error.
        """
        # Keep the raw payload so it can be flashed back when login fails.
        credentials: dict[str, Any] = await request.data()

        # Delegate the credential verification to the session guard.
        authenticated: bool = await auth.attempt({
            "email": payload.email, "password": payload.password,
        })

        # Report a generic error so existing emails are never disclosed.
        if not authenticated:
            return (
                response.redirect(self.DEFAULT_LOGIN_PATH)
                        .withInput(credentials)
                        .withErrors({
                            "email": "These credentials do not match our records.",
                        })
            )

        # Persist the email in a cookie only when the checkbox was ticked.
        remember: bool = credentials.get("remember", "off") == "on"
        value_cookie: str = payload.email if remember else ""
        max_age_cookie: int = self.REMEMBER_COOKIE_MAX_AGE if remember else 0

        return (
            response.redirect(self.redirect_to)
                    .withCookie(
                        self.REMEMBER_COOKIE_NAME,
                        value_cookie,
                        max_age=max_age_cookie,
                    )
        )

    async def logout(
        self,
        auth: IAuthManager,
    ) -> HttpResponse:
        """
        Invalidate the current session and return to the public welcome page.

        Parameters
        ----------
        auth : IAuthManager
            Authentication service bound to the current request.

        Returns
        -------
        HttpResponse
            Redirect whose session cookie is cleared by the web middleware.
        """
        # Drop the authenticated identity before leaving the private area.
        await auth.logout()
        return response.redirect(self.LOGOUT_REDIRECT_PATH)
