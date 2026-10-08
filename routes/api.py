from app.http.controllers.home_controller import HomeController
from orionis.support.facades import Route

Route.group(prefix="/api", routes=[
    Route.get("/health", [HomeController, "health"]),
])
