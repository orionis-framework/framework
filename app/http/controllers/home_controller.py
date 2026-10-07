from orionis.http import HTMLResponse, JSONResponse, response
from orionis.http.base import BaseController

class HomeController(BaseController):

    async def home(self) -> HTMLResponse:
        """
        Render the authenticated home page response.

        Returns
        -------
        HTMLResponse
            The rendered home page for the signed-in user.
        """
        return await response.view("home.index")

    async def api(self) -> JSONResponse:
        """
        Return a JSON response for testing purposes.

        Returns
        -------
        JSONResponse
            A JSON response containing a test message.
        """
        return response.json({
            "message": "Orionis API is working",
        })
