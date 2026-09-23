from collections.abc import Sequence
from orionis.container.contracts.facade import IFacade
from orionis.http.routes.contracts.router import IRouter
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.group import RouteGroup
from orionis.http.routes.types import MiddlewareInput, RouteAction

class Route(IRouter, IFacade):

    @classmethod
    def auth(
        cls,
        login_controller: type | None = None,
        register_controller: type | None = None,
    ) -> None: ...

    @classmethod
    def view(
        cls,
        path: str,
        view: str,
    ) -> FluentRoute: ...

    @classmethod
    def post(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def get(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def query(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def put(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def delete(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def patch(
        cls,
        path: str,
        action: RouteAction | None = None,
    ) -> FluentRoute: ...

    @classmethod
    def fallback(
        cls,
        action: RouteAction,
    ) -> None: ...

    @classmethod
    def group(
        cls,
        *,
        prefix: str | None = None,
        middleware: MiddlewareInput | None = None,
        without_middleware: MiddlewareInput | None = None,
        routes: Sequence[FluentRoute | RouteGroup] | None = None,
    ) -> RouteGroup: ...

    @classmethod
    def export(cls) -> dict: ...
