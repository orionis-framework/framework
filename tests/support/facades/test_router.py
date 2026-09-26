"""Validate Route.auth() through its pinned router, compiler and cache."""
import json
import subprocess
import sys
from pathlib import Path
from orionis.auth.middleware import AuthenticateSessionMiddleware, GuestMiddleware
from orionis.http.default.controllers.forgot_password_controller import (
    ForgotPasswordController,
)
from orionis.http.default.controllers.login_controller import LoginController
from orionis.http.default.controllers.register_controller import RegisterController
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_resolver import RouteResolver
from orionis.support.facades.router import Route
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    compile_router,
    make_router,
    route_handler,
)

_AUTH_ROUTES = (
    ("GET", "/login", LoginController, "index", None, GuestMiddleware),
    ("POST", "/login", LoginController, "login", "login", GuestMiddleware),
    ("GET", "/sign-up", RegisterController, "index", None, GuestMiddleware),
    ("POST", "/sign-up", RegisterController, "register", "register", GuestMiddleware),
    (
        "GET", "/forgot-password", ForgotPasswordController,
        "index", None, GuestMiddleware,
    ),
    (
        "POST", "/forgot-password", ForgotPasswordController,
        "sendResetLinkEmail", "forgot-password", GuestMiddleware,
    ),
    (
        "GET", "/reset-password", ForgotPasswordController,
        "showResetForm", "password.reset", GuestMiddleware,
    ),
    (
        "POST", "/reset-password", ForgotPasswordController,
        "resetPassword", "password.update", GuestMiddleware,
    ),
    ("GET", "/verify-email", RegisterController, "verifyEmail", "verify-email", None),
    (
        "POST", "/logout", LoginController, "logout", "logout",
        AuthenticateSessionMiddleware,
    ),
)


class TestRouteAuth(TestCase):
    """Keep the web authentication helper consistent with normal route registration."""

    def testRegistersExactlyTheCurrentWebFlowOnThePinnedRouter(self) -> None:
        """Check every method, handler, name and middleware on a facade subclass."""
        router = make_router()
        facade = type("AuthRoutes", (Route,), {"_pinned_instance": router})
        initial = len(router.export()["routes"])
        self.assertIsNone(facade.auth())
        self.assertEqual(len(router.export()["routes"]), initial + len(_AUTH_ROUTES))
        resolver = RouteResolver(compile_router(router))
        for method, path, controller, action, name, middleware in _AUTH_ROUTES:
            with self.subTest(method=method, path=path):
                route = resolver.resolve(method, path).route
                self.assertEqual(route.kind, "web")
                self.assertEqual(route.name, name)
                self.assertEqual(route.action["module"], controller.__module__)
                self.assertEqual(route.action["class"], controller.__name__)
                self.assertEqual(route.action["method"], action)
                expected_middleware = (middleware,) if middleware else ()
                self.assertEqual(route.compiled_middlewares, expected_middleware)
        self.assertEqual(resolver.options("/logout"), ["OPTIONS", "POST"])

    def testRejectsApiRegistrationBeforeMutatingRoutes(self) -> None:
        """A misplaced helper must never silently create a session-less API flow."""
        router = make_router()
        router._setKind("api")
        original = router.export()
        facade = type("ApiAuthRoutes", (Route,), {"_pinned_instance": router})
        with self.assertRaisesRegex(ValueError, "web route file"):
            facade.auth()
        self.assertEqual(router.export(), original)
        self.assertEqual(router.get("/api", route_handler).export()["kind"], "api")

    def testAuthRoutesSurviveThePersistentCacheRoundTrip(self) -> None:
        """Restore auth handlers, names and middleware from persistent JSON."""
        router = make_router()
        router.auth()
        cache = RouteCache()
        compiled = compile_router(router)
        encoded = json.dumps(cache.toCache(compiled, None))
        restored, fallback = cache.fromCache(json.loads(encoded))
        resolver = RouteResolver(restored)
        self.assertIsNone(fallback)
        for method, path, _controller, _action, name, middleware in _AUTH_ROUTES:
            route = resolver.resolve(method, path).route
            self.assertEqual(route.action, compiled[method]["static"][path].action)
            self.assertEqual(route.kind, "web")
            self.assertEqual(route.name, name)
            expected_middleware = (middleware,) if middleware else ()
            self.assertEqual(route.compiled_middlewares, expected_middleware)

    def testRepeatedRegistrationUsesTheNormalConflictValidation(self) -> None:
        """Repeated helpers must fail compilation instead of overwriting routes."""
        router = make_router()
        router.auth()
        router.auth()
        with self.assertRaisesRegex(ValueError, "Route conflict"):
            compile_router(router)

    def testExistingHandlersAreNeverSilentlyReplaced(self) -> None:
        """Manual auth routes and generated routes cannot shadow each other."""
        router = make_router()
        router.get("/login", route_handler)
        router.auth()
        with self.assertRaisesRegex(ValueError, "Route conflict"):
            compile_router(router)

    def testFacadeImportDoesNotLoadApplicationAuthCode(self) -> None:
        """Applications that do not use auth must be able to import the route facade."""
        result = subprocess.run(
            [
                sys.executable, "-B", "-c",
                (
                    "import sys; from orionis.support.facades.router import Route; "
                    "print(int('app.models.user' in sys.modules)); "
                    "print(int('orionis.http.default.controllers.login_controller' "
                    "in sys.modules))"
                ),
            ],
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True, text=True, check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["0", "0"])
