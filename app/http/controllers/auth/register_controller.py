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
            Rendered registration page including the submitted data.
        """
        await DB.beginTransaction()

        try:

            user = User()
            user.name = request.name.strip()
            user.email = request.email.strip().lower()
            user.password = Hash.make(request.password.strip())
            await user.save()

            await DB.commit()
            return (
                response.redirect("/login")
                        .withFlash(
                            "success", "Account created successfully. Please log in.",
                        )
            )

        except Exception as e:

            await DB.rollback()
            return await (
                response.view("auth.register")
                        .withErrors({
                            "registration": str(e),
                        })
                        .withInput(request.toDict())
            )
