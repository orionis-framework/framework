import asyncio
from app.models.user import User
from app.http.schemas.auth.register import RegisterSchema
from orionis.http import response, HttpResponse
from orionis.http.base import BaseController
from orionis.support.facades import DB, Hash

class RegisterController(BaseController):

    async def index(self) -> HttpResponse:
        """
        Return the registration page response.

        Returns
        -------
        HttpResponse
            Rendered response for the registration page.
        """
        return await response.view("auth.register")

    async def register(self, request: RegisterSchema) -> HttpResponse:
        """
        Handle the registration form submission.

        Parameters
        ----------
        request : RegisterSchema
            Incoming request carrying the submitted account data.

        Returns
        -------
        HttpResponse
            Redirect to login after the account is created.
        """
        hashed = await asyncio.to_thread(Hash.make, request.password)
        async with DB.transaction():
            await User.create({
                "name": request.name.strip(),
                "email": request.email.strip().lower(),
                "password": hashed,
            })
        return response.redirect("/login").withFlash(
            "success", "Account created successfully. Please log in.",
        )
