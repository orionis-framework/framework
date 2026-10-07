from app.http.controllers.home_controller import HomeController
from app.http.controllers.admin.administration_controller import AdministrationController
from app.http.controllers.profile.profile_controller import ProfileController
from app.http.controllers.auth.register_controller import RegisterController
from app.http.controllers.auth.login_controller import LoginController
from app.http.controllers.auth.forgot_password_controller import ForgotPasswordController
from orionis.auth.middleware import AuthenticateMiddleware
from orionis.support.facades import Route

Route.view("/", "welcome")

Route.auth(
    register_controller=RegisterController,
    login_controller=LoginController,
    forgot_password_controller=ForgotPasswordController,
)

Route.group(middleware=AuthenticateMiddleware, routes=[

    Route.get("/home", [HomeController, "home"]).name("home"),

    Route.group(prefix="/profile", routes=[
        Route.get("/", [ProfileController, "index"]).name("profile"),
        Route.post("/password", [ProfileController, "changePassword"]).name("profile.password"),
    ]),

    Route.group(prefix="/admin", routes=[
        Route.get("/roles", [AdministrationController, "roles"]).name("admin.roles"),
        Route.get("/users", [AdministrationController, "users"]).name("admin.users"),
    ]),

])
