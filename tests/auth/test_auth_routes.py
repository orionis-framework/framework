from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.default.controllers.forgot_password_controller import (
    ForgotPasswordController,
)
from orionis.http.default.controllers.login_controller import LoginController
from orionis.http.default.controllers.register_controller import RegisterController
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import make_router

if TYPE_CHECKING:
    from orionis.http.routes.router import Router

class CustomLoginController(LoginController):
    """Mark application-provided login route handlers."""

class CustomRegisterController(RegisterController):
    """Mark application-provided registration route handlers."""

class CustomForgotPasswordController(ForgotPasswordController):
    """Mark application-provided password recovery route handlers."""

class TestAuthRouteControllers(TestCase):
    """Allow each controller family in the web auth routes to be replaced."""

    @staticmethod
    def _routesByPath(router: Router) -> dict[tuple[str, str], dict]:
        """Index exported routes by method and path.

        Parameters
        ----------
        router : Router
            Router containing authentication routes.

        Returns
        -------
        dict[tuple[str, str], dict]
            Exported route definitions keyed by method and path.
        """
        return {
            (route["method"], route["path"]): route
            for route in router.export()["routes"]
        }

    def testUsesTheBuiltInDefaultForEachOmittedController(self) -> None:
        """Use framework controllers when overrides are omitted.

        Returns
        -------
        None
            Assert each default authentication controller is retained.
        """
        router = make_router()

        router.auth()

        routes = self._routesByPath(router)
        self.assertIs(routes[("POST", "/login")]["class"], LoginController)
        self.assertIs(routes[("POST", "/sign-up")]["class"], RegisterController)
        self.assertIs(
            routes[("POST", "/forgot-password")]["class"],
            ForgotPasswordController,
        )

    def testUsesEachProvidedControllerForItsRoutes(self) -> None:
        """Apply each custom controller to its authentication routes.

        Returns
        -------
        None
            Assert exported routes preserve all configured overrides.
        """
        router = make_router()

        router.auth(
            login_controller=CustomLoginController,
            register_controller=CustomRegisterController,
            forgot_password_controller=CustomForgotPasswordController,
        )

        routes = self._routesByPath(router)
        expected = {
            ("GET", "/login"): (CustomLoginController, "index"),
            ("POST", "/login"): (CustomLoginController, "login"),
            ("POST", "/logout"): (CustomLoginController, "logout"),
            ("GET", "/sign-up"): (CustomRegisterController, "index"),
            ("POST", "/sign-up"): (CustomRegisterController, "register"),
            ("GET", "/verify-email"): (CustomRegisterController, "verifyEmail"),
            ("GET", "/forgot-password"): (
                CustomForgotPasswordController,
                "index",
            ),
            ("POST", "/forgot-password"): (
                CustomForgotPasswordController,
                "sendResetLinkEmail",
            ),
            ("GET", "/reset-password"): (
                CustomForgotPasswordController,
                "showResetForm",
            ),
            ("POST", "/reset-password"): (
                CustomForgotPasswordController,
                "resetPassword",
            ),
        }

        for key, (controller, handler) in expected.items():
            with self.subTest(route=key):
                self.assertIs(routes[key]["class"], controller)
                self.assertEqual(routes[key]["handler"], handler)

    def testOmittedControllersKeepTheirIndependentDefaults(self) -> None:
        """Keep omitted controller families independent of supplied overrides.

        Returns
        -------
        None
            Assert an override affects only its own controller family.
        """
        router = make_router()

        router.auth(forgot_password_controller=CustomForgotPasswordController)

        routes = self._routesByPath(router)
        self.assertIs(routes[("POST", "/login")]["class"], LoginController)
        self.assertIs(routes[("POST", "/sign-up")]["class"], RegisterController)
        self.assertIs(
            routes[("POST", "/forgot-password")]["class"],
            CustomForgotPasswordController,
        )
        self.assertIs(
            routes[("POST", "/reset-password")]["class"],
            CustomForgotPasswordController,
        )
