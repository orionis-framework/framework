from app.models.user import User
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.default.schemas.register import RegisterSchema
from orionis.support.facades import DB, Hash

class RegisterController(BaseController):

    # ruff: noqa: TC001, BLE001

    REGISTER_VIEW_NAME: str = "auth.register"
    REGISTER_REDIRECT_PATH: str = "/login"

    async def index(
        self,
    ) -> HttpResponse:
        """
        Return the registration page response.

        Returns
        -------
        HttpResponse
            Rendered response for the registration page.
        """
        return await response.view(self.REGISTER_VIEW_NAME)

    async def register(
        self,
        request: RegisterSchema,
    ) -> HttpResponse:
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
        await DB.beginTransaction()

        try:

            hashed: str = await Hash.make(request.password)

            user = User()
            user.name = request.name.strip()
            user.email = request.email.strip().lower()
            user.password = hashed
            await user.save()

            await DB.commit()
            return (
                response.redirect(self.REGISTER_REDIRECT_PATH)
                        .withFlash(
                            "success", "Account created successfully. Please log in.",
                        )
            )

        except Exception as e:

            await DB.rollback()
            return await (
                response.view(self.REGISTER_VIEW_NAME)
                        .withErrors({
                            "registration": str(e),
                        })
                        .withInput(request.toDict())
            )
