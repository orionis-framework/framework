# ruff: noqa: TC001, BLE001
# Resolve annotations at runtime; report failures without exposing backend details.
"""Handle the built-in account-registration endpoints."""

from typing import cast
from app.models.user import User
from orionis.auth import MustVerifyEmail
from orionis.background.task import BackgroundTask
from orionis.failure.runtime import capture
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.default.schemas.register import RegisterSchema
from orionis.http.request import Request
from orionis.mail.entities.content import Content
from orionis.mail.entities.result import MailResult
from orionis.support.facades import DB, Hash, Mail
from orionis.support.facades.encrypter import Crypt
from orionis.support.facades.lang import Lang


class RegisterController(BaseController):
    """Handle the built-in account-registration endpoints."""

    REGISTER_VIEW_NAME: str = "auth.register"
    """Register view name identifier: ``auth.register``."""
    REGISTER_REDIRECT_PATH: str = "/login"
    """Register redirect path identifier: ``/login``."""
    VERIFY_VIEW_NAME: str = "auth.verify-email"
    """Verify view name identifier: ``auth.verify-email``."""
    VERIFY_PARAM_NAME: str = "id"
    """Verify param name identifier: ``id``."""

    async def index(
        self,
    ) -> HttpResponse:
        """
        Return the registration page response.

        Returns
        -------
        orionis.http.Response
            Rendered response for the registration page.
        """
        return await response.view(self.REGISTER_VIEW_NAME)

    async def register(
        self,
        payload: RegisterSchema,
        request: Request,
    ) -> HttpResponse:
        """
        Handle the registration form submission.

        Parameters
        ----------
        payload : orionis.http.default.schemas.register.RegisterSchema
            Incoming request carrying the submitted account data.

        request : orionis.http.Request
            Current request and its trusted execution context.

        Returns
        -------
        orionis.http.Response
            Redirect after committing the account, or render generic form errors.

        Raises
        ------
        asyncio.CancelledError
            If the request is cancelled, after the transaction rolls back.
        """
        try:
            hashed: str = await Hash.make(payload.password)
            async with DB.transaction():
                user = User()
                user.name = payload.name.strip()
                user.email = payload.email.strip().lower()
                user.password = hashed

                if isinstance(user, MustVerifyEmail):
                    user.active = False

                if not await user.save():
                    error_msg = "User persistence was vetoed"
                    raise RuntimeError(error_msg)
        except Exception as e:
            await capture(e, flow="http", phase="registration")
            return (  # NOSONAR(S1110) - Await the complete fluent expression.
                await response.view(self.REGISTER_VIEW_NAME)
                .withErrors(
                    {
                        "registration": (  # NOSONAR(S1110) - Multiline value.
                            "The account could not be created. Please try again."
                        ),
                    },
                )
                .withInput(payload.toDict())
            )

        # Runs after commit: a delivery failure must never trigger a rollback.
        if isinstance(user, MustVerifyEmail):
            return response.redirect(
                url=self.REGISTER_REDIRECT_PATH,
                background=BackgroundTask(
                    self.sendVerificationEmail,
                    request.baseUrl,
                    user,
                ),
            ).withFlash(
                "success",
                "Account created. Check your email to activate it.",
            )

        return response.redirect(self.REGISTER_REDIRECT_PATH).withFlash(
            "success",
            "Account created successfully. Please log in.",
        )

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
        user : ``app.models.user.User``
            The user to whom the verification email will be sent.

        Returns
        -------
        orionis.mail.entities.MailResult
            The result of the email sending operation.
        """
        crypt_id: str = Crypt.encrypt(str(user.id))
        verification_url: str = f"{base_url}/verify-email?id={crypt_id}"

        return await (
            Mail.to(user.email)
            .subject(Lang.get("Verify Your Email"))
            .send(
                Content(
                    view="emails.verify-email",
                    data={
                        "user_name": user.name,
                        "verification_url": verification_url,
                    },
                ),
            )
        )

    async def verifyEmail(
        self,
        request: Request,
    ) -> HttpResponse:
        """
        Activate the account addressed by a verification link.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming request carrying the encrypted identifier in its query
            string.

        Returns
        -------
        orionis.http.Response
            Rendered outcome page reporting the verification state.

        Raises
        ------
        RuntimeError
            If the model refuses to persist the verification update.
        """
        user: User | None = await self.__resolveUser(
            request.queryParams.get(self.VERIFY_PARAM_NAME),
        )

        # A missing, tampered or stale link never discloses why it failed.
        if user is None:
            return await response.view(self.VERIFY_VIEW_NAME, state="invalid")

        if user.email_verified_at is not None:
            return await response.view(
                self.VERIFY_VIEW_NAME,
                state="already_verified",
            )

        user.active = True
        user.email_verified_at = user.freshTimestamp()
        if not await user.save():
            error_msg = "The email address could not be verified."
            raise RuntimeError(error_msg)

        return await response.view(self.VERIFY_VIEW_NAME, state="verified")

    async def __resolveUser(
        self,
        encrypted_id: str | None,
    ) -> User | None:
        """
        Resolve the account referenced by an encrypted verification link.

        Parameters
        ----------
        encrypted_id : str | None
            Encrypted identifier extracted from the verification link.

        Returns
        -------
        ``app.models.user.User`` | None
            Matching user, or ``None`` when the link is absent, forged or
            points to an account that no longer exists.
        """
        if not encrypted_id:
            return None

        # Only the application key can produce a payload this call accepts.
        try:
            identifier = int(Crypt.decrypt(encrypted_id))
        except (TypeError, ValueError, RuntimeError) as error:
            await capture(error, flow="http", phase="email.verification", expected=True)
            return None

        return cast("User | None", await User.find(identifier))
