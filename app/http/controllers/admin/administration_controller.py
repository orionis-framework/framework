from orionis.http import HTMLResponse, response
from orionis.http.base import BaseController

class AdministrationController(BaseController):

    async def roles(self) -> HTMLResponse:
        """
        Render the roles placeholder inside the authenticated layout.

        Returns
        -------
        HTMLResponse
            Rendered roles page inside the authenticated layout.
        """
        return await response.view("admin.roles.index")

    async def users(self) -> HTMLResponse:
        """
        Render the users placeholder inside the authenticated layout.

        Returns
        -------
        HTMLResponse
            Rendered users page inside the authenticated layout.
        """
        return await response.view("admin.users.index")
