from app.http.schemas.auth.register import RegisterSchema
from app.models.user import User
from orionis.http import HttpResponse
from orionis.http.default.controllers.register_controller import \
    RegisterController as BaseRegisterController
from orionis.http.request import Request
from orionis.mail.entities.result import MailResult

class RegisterController(BaseRegisterController):

    async def index(
        self,
    ) -> HttpResponse:
        """
        Return the registration page response.

        Returns
        -------
        HttpResponse
            Rendered response for the registration page.
        """
        return await super().index()

    async def register(
        self,
        payload: RegisterSchema,
        request: Request,
    ) -> HttpResponse:
        """
        Handle the registration form submission.

        Parameters
        ----------
        payload : RegisterSchema
            Incoming request carrying the submitted account data.

        request : Request
            Current request and its trusted execution context.

        Returns
        -------
        HttpResponse
            Redirect to login after the account is created.
        """
        return await super().register(payload, request)

    async def sendVerificationEmail(
        self,
        base_url: str,
        user: User,
    ) -> MailResult:
        """
        Send a verification email to the newly registered user.

        Parameters
        ----------
        base_url : str
            The base URL of the application, used to construct the verification link.
        user : User
            The user to whom the verification email will be sent.

        Returns
        -------
        MailResult
            The result of the email sending operation.
        """
        return await super().sendVerificationEmail(base_url, user)

    async def verifyEmail(
        self,
        request: Request,
    ) -> HttpResponse:
        """
        Activate the account addressed by a verification link.

        Parameters
        ----------
        request : Request
            Incoming request carrying the encrypted identifier in its query
            string.

        Returns
        -------
        HttpResponse
            Rendered outcome page reporting the verification state.
        """
        return await super().verifyEmail(request)
