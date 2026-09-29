from app.http.controllers.home_controller import HomeController
from app.http.controllers.administration_controller import AdministrationController
from app.http.controllers.profile_controller import ProfileController
from orionis.auth.middleware import AuthenticateMiddleware
from orionis.support.facades.router import Route

Route.view("/", "welcome")

Route.auth()

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
