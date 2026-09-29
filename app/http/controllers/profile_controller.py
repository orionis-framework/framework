from typing import cast
from app.http.schemas.profile.change_password import ChangePasswordSchema
from app.models.user import User
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.manager import IAuthManager
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.http import HTMLResponse, RedirectResponse, response
from orionis.http.base import BaseController

class ProfileController(BaseController):

    async def index(self, auth: IAuthManager) -> HTMLResponse:
        """
        Render the profile page with the authenticated account data.

        Parameters
        ----------
        auth : IAuthManager
            Authentication service holding the identity resolved for the
            current request.

        Returns
        -------
        HTMLResponse
            Rendered profile page exposing only public account attributes.
        """
        # Read and cast the identity to the expected User model.
        identity: User = cast("User", auth.user())

        # Hand the template a minimal projection of the account.
        return await response.view(
            "profile.index",
            user={
                "name": identity.name,
                "email": identity.email,
            },
        )

    async def changePassword(
        self,
        payload: ChangePasswordSchema,
        auth: IAuthManager,
        identities: IIdentityProvider,
        hashing: IHashManager,
    ) -> RedirectResponse:
        """
        Verify the current secret, save a hash and rotate the active session.

        Credential verification uses the same provider as login. Hashing runs
        off the event loop; submitted passwords are never flashed or logged.
        Only the identity established by authentication middleware is updated.

        Parameters
        ----------
        payload : ChangePasswordSchema
            Validated payload; invalid submissions never reach this method.
        auth : IAuthManager
            Authentication service owning the identity of the current request.
        identities : IIdentityProvider
            Identity provider used to verify the submitted current password.
        hashing : IHashManager
            Hash manager used to derive the stored password hash.

        Returns
        -------
        RedirectResponse
            Redirect back to the profile page, carrying either a field error
            or a success message.
        """
        # Every outcome of this action returns to the same page.
        redirect_to: str = "/profile"

        # Update only the identity established by the authentication layer.
        user: User = cast("User", auth.user())

        # Verify the current password off the event loop, as login does.
        valid: bool = await identities.validateCredentials(
            identity=user,
            credentials={"password": payload.current_password},
        )

        # Reject the change without disclosing anything about the stored hash.
        if not valid:
            return response.redirect(redirect_to).withErrors({
                "current_password": "The current password is incorrect.",
            })

        # Hash off the event loop and persist the new credential.
        try:
            user.password = await hashing.make(payload.password)
            user.remember_token = None
            saved: bool = await user.save()
        except Exception:
            # Never send ORM parameters, password hashes or backend errors back.
            saved = False

        # Report a generic failure when the new hash could not be stored.
        if not saved:
            return response.redirect(redirect_to).withErrors({
                "password": "The password could not be updated. Please try again.",
            })

        # The session guard rotates both the session identifier and CSRF token.
        await auth.login(user)

        # Confirm the change with a flash message on the profile page.
        return response.redirect(redirect_to).withFlash(
            "success", "Your password has been updated.",
        )
