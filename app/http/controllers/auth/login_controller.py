from app.http.schemas.auth.login import LoginSchema
from orionis.auth.contracts.manager import IAuthManager
from orionis.http import HttpResponse
from orionis.http.default.controllers.login_controller import \
    LoginController as BaseLoginController
from orionis.http.request import Request

class LoginController(BaseLoginController):

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
        return await super().index()

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
        return await super().login(request, payload, auth)

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
        return await super().logout(auth)
