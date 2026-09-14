from app.http.controllers.auth.login_controller import LoginController
from app.http.controllers.auth.register_controller import RegisterController
from app.http.controllers.auth.forgot_password_controller import (
    ForgotPasswordController,
)
from app.http.controllers.home_controller import HomeController
from orionis.auth.middleware import (
    AuthenticateSessionMiddleware,
    GuestMiddleware,
    ResolveIdentityMiddleware,
)
from orionis.support.facades.router import Route

Route.get("/", [HomeController, "index"]).middleware(ResolveIdentityMiddleware)
Route.get("/login", [LoginController, "index"]).middleware(GuestMiddleware)
Route.post("/login", [LoginController, "login"]).name("login").middleware(
    GuestMiddleware,
)
Route.get("/sign-up", [RegisterController, "index"]).middleware(GuestMiddleware)
Route.post("/sign-up", [RegisterController, "register"]).name("register").middleware(
    GuestMiddleware,
)
Route.post("/logout", [LoginController, "logout"]).name("logout").middleware(
    AuthenticateSessionMiddleware,
)
Route.get("/forgot-password", [ForgotPasswordController, "index"])
Route.post("/forgot-password", [ForgotPasswordController, "sendResetLink"]).name(
    "forgot-password",
)
