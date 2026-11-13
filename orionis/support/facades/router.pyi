# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from collections.abc import Sequence
from orionis.container.contracts.facade import IFacade
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.group import RouteGroup
from orionis.http.routes.types import MiddlewareInput, RouteAction
from orionis.realtime.hub import Hub

class Route(IFacade):
    @classmethod
    def hub(
        cls,
        path: str,
        hub: type[Hub],
        *,
        protocol: str = "json",
    ) -> FluentRoute:
        """Register a Hub endpoint using a fixed JSON or MessagePack codec."""

    @classmethod
    def websocket(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a WebSocket connection handler independently of HTTP routes."""

    @classmethod
    def auth(
        cls,
        login_controller: type | None = None,
        register_controller: type | None = None,
        forgot_password_controller: type | None = None,
    ) -> None:
        """Register the built-in web authentication routes."""

    @classmethod
    def view(
        cls,
        path: str,
        view: str,
    ) -> FluentRoute:
        """Register a GET route that renders a template with no controller."""

    @classmethod
    def post(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a POST route."""

    @classmethod
    def get(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a GET route."""

    @classmethod
    def query(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a QUERY route."""

    @classmethod
    def put(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a PUT route."""

    @classmethod
    def delete(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a DELETE route."""

    @classmethod
    def patch(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute:
        """Register a PATCH route."""

    @classmethod
    def fallback(
        cls,
        action: RouteAction,
    ) -> None:
        """Register the fallback handler for unmatched routes (HTTP 404)."""

    @classmethod
    def group(
        cls,
        *,
        prefix: str | None = None,
        middleware: MiddlewareInput | None = None,
        without_middleware: MiddlewareInput | None = None,
        routes: Sequence[FluentRoute | RouteGroup] | None = None,
        public: bool | None = None,
    ) -> RouteGroup:
        """Compose a group and return its flattened membership for nesting."""

    @classmethod
    def export(cls) -> dict:
        """Export all registered routes and the fallback handler."""
