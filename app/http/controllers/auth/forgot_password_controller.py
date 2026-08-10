from orionis.http import HTMLResponse
from orionis.http.base import BaseController
from orionis.support.facades import View

class ForgotPasswordController(BaseController):

    async def index(self) -> HTMLResponse:
        """
        Return the forgot password page response.

        Returns
        -------
        HTMLResponse
            Rendered response for the forgot password page.
        """
        return await View.make("auth.forgot-password")

    async def sendResetLink(self) -> HTMLResponse:
        """
        Handle the forgot password form submission.

        Returns
        -------
        HTMLResponse
            Rendered forgot password page.
        """
        return await View.make("auth.forgot-password")
