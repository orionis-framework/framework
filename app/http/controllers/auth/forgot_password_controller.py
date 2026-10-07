from app.http.schemas.auth.forgot_password import ForgotPasswordSchema
from orionis.auth.passwords.broker import PasswordBroker
from orionis.http.default.controllers.forgot_password_controller import \
    ForgotPasswordController as BaseForgotPasswordController
from orionis.http import HTMLResponse, HttpResponse
from orionis.http.request import Request

class ForgotPasswordController(BaseForgotPasswordController):

    async def index(self) -> HTMLResponse:
        """
        Render the forgot-password page.

        Returns
        -------
        HTMLResponse
            Rendered forgot-password page response.
        """
        return await super().index()

    async def sendResetLinkEmail(
        self,
        payload: ForgotPasswordSchema,
        request: Request,
        broker: PasswordBroker,
    ) -> HttpResponse:
        """
        Queue a password-reset message without revealing account existence.

        Parameters
        ----------
        payload : ForgotPasswordSchema
            Validated email address submitted by the requester.
        request : Request
            Current HTTP request used to build the reset URL.
        broker : PasswordBroker
            Service that issues and validates reset tokens.

        Returns
        -------
        HttpResponse
            Private redirect response returned before account lookup.
        """
        return await super().sendResetLinkEmail(payload, request, broker)

    async def showResetForm(
        self,
        request: Request,
        broker: PasswordBroker,
    ) -> HTMLResponse:
        """
        Display a reset form for an unconsumed link.

        Parameters
        ----------
        request : Request
            Current HTTP request containing the email and token query values.
        broker : PasswordBroker
            Service that validates the reset token.

        Returns
        -------
        HTMLResponse
            Reset form response with the link validity state.
        """
        return await super().showResetForm(request, broker)

    async def resetPassword(
        self,
        request: Request,
        broker: PasswordBroker,
    ) -> HttpResponse:
        """
        Reset the password without flashing credentials or tokens.

        Parameters
        ----------
        request : Request
            Current HTTP request containing the reset form payload.
        broker : PasswordBroker
            Service that validates and consumes the reset token.

        Returns
        -------
        HttpResponse
            Reset form response for invalid input, or a private login redirect
            after a successful reset.
        """
        return await super().resetPassword(request, broker)
