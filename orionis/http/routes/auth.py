from typing import TYPE_CHECKING
from orionis.http.default.controllers.forgot_password_controller import ForgotPasswordController
from orionis.auth.middleware.authenticate import AuthenticateSessionMiddleware
from orionis.auth.middleware.guest import GuestMiddleware
from orionis.http.default.controllers.login_controller import LoginController
from orionis.http.default.controllers.register_controller import RegisterController

if TYPE_CHECKING:
    from orionis.http.routes.contracts.router import IRouter

# ruff: noqa: E501

# Register the framework's default authentication routes.
def build_auth_routes(
    router: IRouter,
    login_controller: type | None = None,
    register_controller: type | None = None,
    forgot_password_controller: type | None = None,
) -> None:
    """
    Register the authentication routes on the given router.

    Parameters
    ----------
    router : IRouter
        Router that receives the authentication routes.
    login_controller : type | None, optional
        Controller type used for login and logout routes.
    register_controller : type | None, optional
        Controller type used for registration and email verification routes.
    forgot_password_controller : type | None, optional
        Controller type used for password recovery and reset routes.

    Returns
    -------
    None
        Register the routes in place and return nothing.
    """
    login: type = (
        login_controller
        if login_controller is not None
        else LoginController
    )

    register: type = (
        register_controller
        if register_controller is not None
        else RegisterController
    )

    forgot: type = (
        forgot_password_controller
        if forgot_password_controller is not None
        else ForgotPasswordController
    )

    router.group(middleware=GuestMiddleware, routes=[
        router.get("/login", [login, "index"]),
        router.post("/login", [login, "login"]).name("login"),
        router.get("/sign-up", [register, "index"]),
        router.post("/sign-up", [register, "register"]).name("register"),
        router.get("/forgot-password", [forgot, "index"]),
        router.post("/forgot-password", [forgot, "sendResetLinkEmail"]).name("forgot-password"),
        router.get("/reset-password", [forgot, "showResetForm"]).name("password.reset"),
        router.post("/reset-password", [forgot, "resetPassword"]).name("password.update"),
    ])

    router.get("/verify-email", [register, "verifyEmail"]).name("verify-email")

    router.group(middleware=AuthenticateSessionMiddleware, routes=[
        router.post("/logout", [login, "logout"]).name("logout"),
    ])
