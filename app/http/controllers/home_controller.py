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

    async def health(self) -> JSONResponse:
        """
        Return the health status of the API.

        Returns
        -------
        JSONResponse
            A JSON response containing the queried data from the "vigia.rates" table.
        """
        return response.json({
            "message": "Orionis API is working",
            "status": "healthy",
        })
