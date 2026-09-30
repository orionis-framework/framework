from rich.console import Console
from orionis.console.commands.route.list import RouteListCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.test import TestCase

class _AuthMiddleware:
    """Identify middleware shown in the route table."""

class _RouteLoader:
    """Provide precompiled route buckets to the list command."""

    def __init__(self, routes: dict[str, dict]) -> None:
        """Store compiled routes grouped by HTTP method.

        Parameters
        ----------
        routes : dict[str, dict]
            Route buckets returned by the compiler.

        Returns
        -------
        None
            Store routes for later retrieval.
        """
        self.routes = routes

    def load(self) -> dict[str, dict]:
        """Return the compiled route buckets.

        Returns
        -------
        dict[str, dict]
            Routes grouped by HTTP method and path type.
        """
        return self.routes

def _make_route(  # noqa: PLR0913
    path: str,
    method: str,
    action: dict[str, str],
    *,
    name: str | None = None,
    route_type: RouteType = RouteType.FUNCTION,
    middleware: tuple[type, ...] = (),
) -> CompiledRoute:
    """Build one compiled route for command output tests.

    Parameters
    ----------
    path : str
        URI displayed for the route.
    method : str
        HTTP method displayed for the route.
    action : dict[str, str]
        Compiled action descriptor.
    name : str | None, optional
        Optional route name.
    route_type : RouteType, optional
        Handler category stored on the route.
    middleware : tuple[type, ...], optional
        Effective middleware stack for the route.

    Returns
    -------
    CompiledRoute
        Compiled route fixture used by the command tests.
    """
    return CompiledRoute(
        path=path,
        method=method,
        type=route_type,
        action=action,
        name=name,
        regex=None,
        segment_count=path.count("/"),
        compiled_middlewares=middleware,
    )

class TestRouteListCommand(TestCase):
    """Verify route listing, action formatting, and URI ordering."""

    def testRegistersTheRouteListCommand(self) -> None:
        """Expose the route list command to the reactor.

        Returns
        -------
        None
            Assertions verify the command signature is registered.
        """
        signatures = {command.signature for command in CORE_COMMANDS}

        self.assertIn("route:list", signatures)

    async def testListsActionsAndMiddlewareInAscendingUriOrder(self) -> None:
        """Display compiled routes ordered by their URI.

        Returns
        -------
        None
            Assertions verify route details and URI sort order.
        """
        routes = {
            "POST": {
                "static": {
                    "/zebra": _make_route(
                        "/zebra",
                        "POST",
                        {
                            "module": "app.controllers.inventory",
                            "class": "InventoryController",
                            "method": "store",
                        },
                        name="inventory.store",
                        route_type=RouteType.CONTROLLER,
                        middleware=(_AuthMiddleware,),
                    ),
                },
                "dynamic": [],
            },
            "GET": {
                "static": {
                    "/alpha": _make_route(
                        "/alpha",
                        "GET",
                        {"module": "app.routes", "function": "alpha"},
                    ),
                },
                "dynamic": [
                    _make_route(
                        "/api/{id}",
                        "GET",
                        {"view": "pages.api"},
                        name="api.show",
                        route_type=RouteType.VIEW,
                    ),
                ],
            },
        }
        console = Console(record=True, width=200, color_system=None)

        result = await RouteListCommand().handle(_RouteLoader(routes), console)
        output = console.export_text()

        self.assertEqual(result, 0)
        self.assertLess(output.index("/alpha"), output.index("/api/{id}"))
        self.assertLess(output.index("/api/{id}"), output.index("/zebra"))
        self.assertIn("inventory.store", output)
        self.assertIn("app.controllers.inventory.InventoryController.store", output)
        self.assertIn("View: pages.api", output)
        self.assertIn("_AuthMiddleware", output)
        self.assertIn("Showing [3] routes", output)

    async def testReportsWhenNoRoutesAreRegistered(self) -> None:
        """Report an empty route table with a failing status code.

        Returns
        -------
        None
            Assertions verify the empty-state message and result.
        """
        console = Console(record=True, width=120, color_system=None)
        loader = _RouteLoader({})

        result = await RouteListCommand().handle(loader, console)

        self.assertEqual(result, 1)
        self.assertIn(
            "Your application has no registered routes.",
            console.export_text(),
        )
