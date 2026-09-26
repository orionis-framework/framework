import logging
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

_logger = logging.getLogger(__name__)
_MAX_EMAIL_LENGTH = 255
_TOKEN_LENGTH = 43


class ForgotPasswordController(BaseController):
    """Request a reset link and accept a new password after email ownership."""

    # ruff: noqa: TC001, BLE001, TRY400 (Never log credential-bearing exceptions)

    SENT_MESSAGE = (
        "If an account matches that email, you will receive a password reset link."
    )

    async def index(self) -> HTMLResponse:
        """
        Return the forgot password page response.

        Returns
        -------
        HTMLResponse
            Rendered response for the forgot password page.
        """
        return self._private(await response.view("auth.forgot-password"))

    async def sendResetLinkEmail(
        self,
        payload: ForgotPasswordSchema,
        request: Request,
        broker: PasswordBroker,
    ) -> HttpResponse:
        """Return the same response before account lookup and mail delivery."""
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
        """Issue and deliver after the response, keeping backend errors private."""
        try:
            issued = await broker.issue(email)
            if issued is None:
                return
            user, token = issued
            reset_url = (
                f"{base_url.rstrip('/')}/reset-password?"
                + urlencode({"email": user.email, "token": token})
            )
            await Mail.to(user.email).subject(
                Lang.get("Reset your password"),
            ).send(Content(view="emails.reset-password", data={
                "user_name": getattr(user, "name", ""),
                "reset_url": reset_url,
                "expires_minutes": broker.settings.expiration,
            }))
        except Exception:
            # Exceptions may contain SQL bindings or mail bodies with secrets.
            _logger.error("Password reset email could not be delivered.")

    async def showResetForm(
        self, request: Request, broker: PasswordBroker,
    ) -> HTMLResponse:
        """Display an unconsumed link; GET never changes the account."""
        email = request.queryParams.get("email", "")
        token = request.queryParams.get("token", "")
        valid = (
            isinstance(email, str) and len(email) <= _MAX_EMAIL_LENGTH
            and isinstance(token, str) and len(token) == _TOKEN_LENGTH
            and await broker.valid(email, token)
        )
        return await self._form(email, token, valid=valid)

    async def resetPassword(
        self, request: Request, broker: PasswordBroker,
    ) -> HttpResponse:
        """Validate in place so passwords and reset tokens are never flashed."""
        data = await request.data()
        email = data.get("email", "")
        token = data.get("token", "")
        if (
            not isinstance(email, str) or len(email) > _MAX_EMAIL_LENGTH
            or not isinstance(token, str) or len(token) != _TOKEN_LENGTH
            or not await broker.valid(email, token)
        ):
            return await self._form("", "", valid=False)
        try:
            payload = Validator.validate(data, ResetPasswordSchema)
        except ValidationException as exc:
            return await self._form(email, token, valid=True, errors=exc)
        try:
            user = await broker.reset(email, token, payload.password)
        except Exception:
            _logger.error("Password reset could not be completed.")
            return await self._form(email, token, valid=True, errors={
                "password": "The password could not be updated. Please try again.",
            })
        if user is None:
            return await self._form("", "", valid=False)
        return self._private(response.redirect(
            "/login",
            background=BackgroundTask(self._sendConfirmation, user.email),
        ).withFlash(
            "success", Lang.get("Your password has been reset. Please log in."),
        ))

    async def _sendConfirmation(self, email: str) -> None:
        """Notify the owner after commit without including any credential."""
        try:
            await Mail.to(email).subject(Lang.get("Your password was reset")).raw(
                Lang.get(
                    "Your password has been reset. If you did not make this "
                    "change, contact support immediately.",
                ),
            )
        except Exception:
            _logger.error("Password reset confirmation could not be delivered.")

    async def _form(
        self, email: str, token: str, *, valid: bool,
        errors: dict[str, str] | ValidationException | None = None,
    ) -> HTMLResponse:
        """Render errors with no password values or secret-bearing flash input."""
        pending = response.view(
            "auth.reset-password", valid=valid,
            email=email if valid else "", token=token if valid else "",
        )
        if errors is not None:
            pending = pending.withErrors(errors)
        rendered = await pending
        if not valid:
            rendered.status_code = 400
        return self._private(rendered)

    @staticmethod
    def _private(result: HttpResponse) -> HttpResponse:
        """Prevent browser caching and reset URL leakage through referrers."""
        result.setHeader("Cache-Control", "no-store")
        result.setHeader("Referrer-Policy", "no-referrer")
        result.setHeader("X-Robots-Tag", "noindex, nofollow")
        return result
