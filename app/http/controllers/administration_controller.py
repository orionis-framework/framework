from orionis.auth.contracts.manager import IAuthManager
from orionis.http import HTMLResponse, response
from orionis.http.base import BaseController


class AdministrationController(BaseController):
    """Expose the initial administration screens without data operations."""

    async def roles(self, auth: IAuthManager) -> HTMLResponse:
        """Render the roles placeholder inside the authenticated layout."""
        identity = auth.user()
        return await response.view(
            "admin.roles.index",
            user={"name": identity.name, "email": identity.email},
        )

    async def users(self, auth: IAuthManager) -> HTMLResponse:
        """Render the users placeholder inside the authenticated layout."""
        identity = auth.user()
        return await response.view(
            "admin.users.index",
            user={"name": identity.name, "email": identity.email},
        )
