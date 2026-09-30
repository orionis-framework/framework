from rich import box
from rich.console import Console
from rich.table import Table
from orionis.console.base.command import BaseCommand
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.loader import RouteLoader

class RouteListCommand(BaseCommand):
    """Display registered HTTP routes in URI order."""

    # ruff: noqa: TC001, TC002

    timestamps: bool = False
    signature: str = "route:list"
    description: str = "List the application's registered HTTP routes."

    def __getAction(self, route: CompiledRoute) -> str:
        """
        Format the route handler as an importable Python name.

        Parameters
        ----------
        route : CompiledRoute
            Route whose action descriptor is displayed.

        Returns
        -------
        str
            Qualified handler name or a dash when no action is available.
        """
        action = route.action
        module = action.get("module")
        class_name = action.get("class")
        if class_name is not None:
            action_name = f"{module}.{class_name}" if module else class_name
            method = action.get("method")
            return f"{action_name}.{method}" if method else action_name

        function = action.get("function")
        if function is not None:
            return f"{module}.{function}" if module else str(function)

        view = action.get("view")
        if view is not None:
            return f"View: {view}"

        return "-"

    def __getMiddleware(self, route: CompiledRoute) -> str:
        """
        Format the middleware stack attached to a route.

        Parameters
        ----------
        route : CompiledRoute
            Route whose effective middleware stack is displayed.

        Returns
        -------
        str
            Comma-separated middleware names or a dash when the stack is empty.
        """
        middlewares = route.compiled_middlewares
        if not middlewares:
            return "-"
        return ", ".join(middleware.__qualname__ for middleware in middlewares)

    def __collectRoutes(self, route_loader: RouteLoader) -> list[CompiledRoute]:
        """
        Flatten compiled method buckets and sort routes by their URI.

        Parameters
        ----------
        route_loader : RouteLoader
            Loader that provides the application's compiled route buckets.

        Returns
        -------
        list[CompiledRoute]
            All registered routes sorted by path in ascending order.
        """
        compiled_routes = route_loader.load()
        routes: list[CompiledRoute] = []
        for method_routes in compiled_routes.values():
            routes.extend(method_routes["static"].values())
            routes.extend(method_routes["dynamic"])
        routes.sort(key=lambda route: route.path)
        return routes

    async def handle(
        self,
        route_loader: RouteLoader,
        console: Console,
    ) -> int:
        """
        Print all application routes as a sorted Rich table.

        Parameters
        ----------
        route_loader : RouteLoader
            Loader that provides the application's compiled route buckets.
        console : Console
            Rich console used to display route information.

        Returns
        -------
        int
            Zero when routes are displayed; one when no routes are registered.
        """
        routes = self.__collectRoutes(route_loader)
        if not routes:
            console.print("[bold red]Your application has no registered routes.[/]")
            return 1

        table = Table(show_lines=False, box=box.SIMPLE_HEAVY)
        table.add_column("Method", style="bold cyan", no_wrap=True)
        table.add_column("URI", style="white", no_wrap=True)
        table.add_column("Name", style="bold yellow")
        table.add_column("Action", style="green", overflow="fold")
        table.add_column("Middleware", style="dim", overflow="fold")

        for route in routes:
            table.add_row(
                route.method,
                route.path,
                route.name or "-",
                self.__getAction(route),
                self.__getMiddleware(route),
            )

        console.print(table)
        console.print(f"Showing [{len(routes)}] routes", style="bold blue")
        return 0
