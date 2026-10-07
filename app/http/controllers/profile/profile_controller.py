from app.http.schemas.profile.change_password import ChangePasswordSchema
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.manager import IAuthManager
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.http import HTMLResponse, RedirectResponse
from orionis.http.default.controllers.profile_controller import \
    ProfileController as BaseProfileController

class ProfileController(BaseProfileController):

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
        return await super().index(auth=auth)

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
        return await super().changePassword(
            payload=payload,
            auth=auth,
            identities=identities,
            hashing=hashing,
        )
