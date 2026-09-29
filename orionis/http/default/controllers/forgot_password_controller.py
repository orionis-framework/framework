from urllib.parse import urlencode
from orionis.auth.passwords.broker import PasswordBroker
from orionis.background.task import BackgroundTask
from orionis.http import HTMLResponse, HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.default.schemas.forgot_password import ForgotPasswordSchema
from orionis.http.default.schemas.reset_password import ResetPasswordSchema
from orionis.http.request import Request
from orionis.mail.entities.content import Content
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.validator import Schema as Validator
from orionis.support.facades import Mail
from orionis.support.facades.lang import Lang

_MAX_EMAIL_LENGTH = 255
_TOKEN_LENGTH = 43

class ForgotPasswordController(BaseController):

    # ruff: noqa: TC001, BLE001

    SENT_MESSAGE = (
        "If an account matches that email, you will receive a password reset link."
    )

    async def index(self) -> HTMLResponse:
        """
        Render the forgot-password page.

        Returns
        -------
        HTMLResponse
            Rendered forgot-password page response.
        """
        # Render the forgot-password page without exposing any sensitive information.
        return self._private(await response.view("auth.forgot-password"))

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
        # Immediately return a private redirect response while the reset
        # link is sent in the background.
        return self._private(response.redirect(
            "/forgot-password",
            background=BackgroundTask(
                self._sendLink,
                payload.email,
                request.baseUrl,
                broker,
            ),
        ).withFlash("success", Lang.get(self.SENT_MESSAGE)))

    async def _sendLink(
        self,
        email: str,
        base_url: str,
        broker: PasswordBroker,
    ) -> None:
        """
        Issue and deliver a reset link after the response.

        Parameters
        ----------
        email : str
            Email address submitted for password recovery.
        base_url : str
            Application base URL used to construct the link.
        broker : PasswordBroker
            Service that issues the reset token and loads the account.

        Returns
        -------
        None
            Completes after delivery or when no matching account is found.
        """
        # Attempt to issue a reset token for the provided email.
        issued = await broker.issue(email)
        if issued is None:
            return
        user, token = issued

        # Construct the reset URL using the base URL and issued token.
        reset_url = (
            f"{base_url.rstrip('/')}/reset-password?"
            + urlencode({"email": user.email, "token": token})
        )

        # Send the password reset email to the user.
        await Mail.to(user.email).subject(
                Lang.get("Reset your password"),
            ).send(
                Content(
                    view="emails.reset-password",
                    data={
                        "user_name": getattr(user, "name", ""),
                        "reset_url": reset_url,
                        "expires_minutes": broker.settings.expiration,
                    },
                ),
            )

    # Validate the reset link without consuming its token.
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
        # Extract the email and token from the query parameters.
        email = request.queryParams.get("email", "")
        token = request.queryParams.get("token", "")
        valid = (
            isinstance(email, str) and len(email) <= _MAX_EMAIL_LENGTH
            and isinstance(token, str) and len(token) == _TOKEN_LENGTH
            and await broker.valid(email, token)
        )

        # Prepare the pending response for the reset form.
        return await self._form(email, token, valid=valid)

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
        # Extract and validate the reset form data.
        data = await request.data()
        email = data.get("email", "")
        token = data.get("token", "")
        if (
            not isinstance(email, str) or len(email) > _MAX_EMAIL_LENGTH
            or not isinstance(token, str) or len(token) != _TOKEN_LENGTH
            or not await broker.valid(email, token)
        ):
            return await self._form("", "", valid=False)

        # Validate the reset form data against the schema.
        try:
            payload = Validator.validate(data, ResetPasswordSchema)
        except ValidationException as exc:
            return await self._form(email, token, valid=True, errors=exc)

        # Attempt to reset the password using the broker.
        try:
            user = await broker.reset(email, token, payload.password)
        except Exception:
            return await self._form(email, token, valid=True, errors={
                "password": "The password could not be updated. Please try again.",
            })

        # Handle the case where the broker did not return a user.
        if user is None:
            return await self._form("", "", valid=False)

        # Redirect to the login page with a success message and
        # background confirmation email.
        return self._private(
            response.redirect(
                "/login",
                background=BackgroundTask(
                    self._sendConfirmation,
                    user.email,
                ),
            ).withFlash(
                "success", Lang.get("Your password has been reset. Please log in."),
            ),
        )

    async def _sendConfirmation(self, email: str) -> None:
        """
        Notify the account owner after the password reset commits.

        Parameters
        ----------
        email : str
            Account email address that receives the notification.

        Returns
        -------
        None
            Completes after the reset notification is sent.
        """
        await (
            Mail.to(email)
                .subject(Lang.get("Your password was reset"))
                .raw(
                    Lang.get(
                        "Your password has been reset. If you did not make this "
                        "change, contact support immediately.",
                    ),
                )
        )

    async def _form(
        self,
        email: str,
        token: str,
        *,
        valid: bool,
        errors: dict[str, str] | ValidationException | None = None,
    ) -> HTMLResponse:
        """
        Render the reset form without exposing password values.

        Parameters
        ----------
        email : str
            Email value retained only when the link is valid.
        token : str
            Reset token retained only when the link is valid.
        valid : bool
            Whether the reset link passed token validation.
        errors : dict[str, str] | ValidationException | None, optional
            Validation errors to display on the form.

        Returns
        -------
        HTMLResponse
            Private reset form response with optional validation errors.
        """
        # Prepare the pending response for the reset form.
        pending = response.view(
            "auth.reset-password",
            valid=valid,
            email=email if valid else "",
            token=token if valid else "",
        )

        # Attach validation errors if present.
        if errors is not None:
            pending = pending.withErrors(errors)

        # Render the final response for the reset form.
        rendered = await pending

        # Mark the response as private to prevent caching and referrer leakage.
        if not valid:
            rendered.status_code = 400

        # Apply privacy headers to the response before returning it.
        return self._private(rendered)

    # Apply headers that prevent caching and referrer-based token leakage.
    @staticmethod
    def _private(
        result: HttpResponse,
    ) -> HttpResponse:
        """
        Mark a response as private and prevent reset URL referrers.

        Parameters
        ----------
        result : HttpResponse
            Response whose security headers are updated.

        Returns
        -------
        HttpResponse
            The same response with privacy and indexing headers applied.
        """
        # Set headers to prevent caching and referrer leakage.
        result.setHeader("Cache-Control", "no-store")
        result.setHeader("Referrer-Policy", "no-referrer")
        result.setHeader("X-Robots-Tag", "noindex, nofollow")

        # Return the response with updated privacy headers.
        return result
