from app.http.controllers.auth.login_controller import LoginController
from app.http.controllers.auth.register_controller import RegisterController
from app.http.controllers.auth.forgot_password_controller import ForgotPasswordController
from app.http.controllers.home_controller import HomeController
from orionis.support.facades.router import Route

Route.get("/", [HomeController, "index"])
Route.get("/login", [LoginController, "index"])
Route.post("/login", [LoginController, "login"]).name("login")
Route.get("/sign-up", [RegisterController, "index"])
Route.post("/sign-up", [RegisterController, "register"]).name("register")
Route.get("/forgot-password", [ForgotPasswordController, "index"])
Route.post("/forgot-password", [ForgotPasswordController, "sendResetLink"]).name("forgot-password")
