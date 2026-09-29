from types import SimpleNamespace
from typing import ClassVar
from orionis.test import TestCase
from orionis.container.container import Container
from orionis.container.entities.invocation import (
    _callable_plan,
    constructor_plan,
    warm_controller_plan,
)
from orionis.http.kernel import KernelHTTP
from orionis.http.responses import Response
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.route_resolver import RouteResolver
from orionis.introspection.dependencies.reflection import (
    _get_resolved_signature,
    _get_signature,
)

def function_handler(item: int = 2) -> Response:
    """Return the value resolved from route parameters.

    Parameters
    ----------
    item : int, optional
        Value supplied through the container.

    Returns
    -------
    Response
        Response containing the selected value.
    """
    return Response(str(item))

def invalid_signature_handler() -> Response:
    """Represent a function whose exposed signature cannot be inspected.

    Returns
    -------
    Response
        Response used only if signature validation is bypassed.
    """
    return Response()

invalid_signature_handler.__signature__ = "invalid"

class _Controller:
    """Expose instance, class, and static actions with constructor metadata."""

    constructions: ClassVar[int] = 0

    def __init__(self, label: str = "constructor") -> None:
        """Record construction without resolving external services.

        Parameters
        ----------
        label : str, optional
            Constructor argument resolved by the container.

        Returns
        -------
        None
            The controller stores its independent constructor value.
        """
        type(self).constructions += 1
        self.label = label

    def instanceAction(self, item: int = 2) -> Response:
        """Return the instance action's explicit argument.

        Parameters
        ----------
        item : int, optional
            Route parameter supplied by the container.

        Returns
        -------
        Response
            Response containing the selected value.
        """
        return Response(str(item))

    @classmethod
    def classAction(cls, item: int = 2) -> Response:
        """Return the class action's explicit argument.

        Parameters
        ----------
        item : int, optional
            Route parameter supplied by the container.

        Returns
        -------
        Response
            Response containing the selected value.
        """
        return Response(str(item))

    @staticmethod
    def staticAction(item: int = 2) -> Response:
        """Return the static action's explicit argument.

        Parameters
        ----------
        item : int, optional
            Route parameter supplied by the container.

        Returns
        -------
        Response
            Response containing the selected value.
        """
        return Response(str(item))

class _DynamicAction:
    """Count descriptor execution before returning a controller action."""

    calls: ClassVar[int] = 0

    def __get__(self, instance: object | None, owner: type | None = None) -> object:
        """Return a callable only when Python resolves the dynamic action.

        Parameters
        ----------
        instance : object | None
            Bound controller instance, if any.
        owner : type | None, optional
            Class receiving the descriptor access.

        Returns
        -------
        Callable
            Function invoked by the container at request time.
        """
        type(self).calls += 1
        return function_handler

class _DynamicController:
    """Provide an action whose descriptor must remain lazy."""

    action = _DynamicAction()

class _DynamicConstructor:
    """Reject any descriptor execution during constructor plan warmup."""

    def __get__(self, instance: object | None, owner: type | None = None) -> object:
        """Fail if warmup tries to bind a custom constructor descriptor.

        Parameters
        ----------
        instance : object | None
            Instance receiving the descriptor access.
        owner : type | None, optional
            Class receiving the descriptor access.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        AssertionError
            Always; descriptor execution is forbidden during this test.
        """
        message = "Custom constructor descriptors must remain lazy."
        raise AssertionError(message)

class _CustomConstructorController:
    """Keep constructor descriptor execution outside metadata warmup."""

    __init__ = _DynamicConstructor()
    action = staticmethod(function_handler)

class _Request:
    """Supply route parameters to the real kernel dispatch stage."""

    @staticmethod
    def routeParams() -> dict[str, int]:
        """Return the explicit action argument.

        Returns
        -------
        dict[str, int]
            Parameters supplied to every fixture route.
        """
        return {"item": 7}

def make_route(handler: str, method: str | None = None) -> CompiledRoute:
    """Create a route descriptor consumed by handler preloading.

    Parameters
    ----------
    handler : str
        Module-level function or controller class name.
    method : str | None, optional
        Controller method, or None for a function route.

    Returns
    -------
    CompiledRoute
        Route suitable for the real resolver and dispatch tables.
    """
    action = {"module": __name__}
    if method is None:
        action["function"] = handler
    else:
        action.update({"class": handler, "method": method})
    return CompiledRoute(
        path=f"/{handler}/{method}", method="GET",
        type=RouteType.FUNCTION if method is None else RouteType.CONTROLLER,
        action=action, name=None, regex=None, segment_count=2,
    )

class TestHandlerPlanWarmup(TestCase):
    """Exercise real kernel preloading and invocation with bounded DI caches."""

    def setUp(self) -> None:
        """Clear metadata caches and create an independent container.

        Returns
        -------
        None
            Each test starts with cold signatures and plan caches.
        """
        _callable_plan.cache_clear()
        constructor_plan.cache_clear()
        _get_resolved_signature.cache_clear()
        _get_signature.cache_clear()
        self.container = object.__new__(Container)
        Container.__init__(self.container)
        self.kernel = KernelHTTP(self.container, None)

    async def testFirstRequestsReusePreparedDescriptorPlans(self) -> None:
        """Preload all standard action kinds without constructing controllers.

        Returns
        -------
        None
            First requests add no signature or invocation-plan cache misses.
        """
        routes = [make_route("function_handler")]
        routes.extend(make_route("_Controller", method) for method in (
            "instanceAction", "classAction", "staticAction",
        ))
        _Controller.constructions = 0 # NOSONAR
        self.kernel._KernelHTTP__routes = RouteResolver(routes={
            "GET": {"static": {route.path: route for route in routes}, "dynamic": []},
        })
        await self.kernel._KernelHTTP__preloadHandlers()
        self.assertEqual(_Controller.constructions, 0)
        signature_misses = _get_signature.cache_info().misses
        callable_misses = _callable_plan.cache_info().misses
        constructor_misses = constructor_plan.cache_info().misses
        self.assertGreater(signature_misses, 0)
        for route in routes:
            response = await self.kernel._KernelHTTP__callHandler(
                SimpleNamespace(route=route), _Request(),
            )
            self.assertEqual(response.getBody(), b"7")
        self.assertEqual(_Controller.constructions, 3)
        self.assertEqual(_get_signature.cache_info().misses, signature_misses)
        self.assertEqual(_callable_plan.cache_info().misses, callable_misses)
        self.assertEqual(constructor_plan.cache_info().misses, constructor_misses)

    async def testCustomActionDescriptorRunsOnlyDuringDispatch(self) -> None:
        """Leave a dynamic action untouched until the request obtains it.

        Returns
        -------
        None
            One request evaluates its custom descriptor exactly once.
        """
        route = make_route("_DynamicController", "action")
        _DynamicAction.calls = 0 # NOSONAR
        self.kernel._KernelHTTP__routes = RouteResolver(routes={
            "GET": {"static": {route.path: route}, "dynamic": []},
        })
        await self.kernel._KernelHTTP__preloadHandlers()
        self.assertEqual(_DynamicAction.calls, 0)
        response = await self.kernel._KernelHTTP__callHandler(
            SimpleNamespace(route=route), _Request(),
        )
        self.assertEqual(response.getBody(), b"7")
        self.assertEqual(_DynamicAction.calls, 1)

    def testCustomConstructorDescriptorRemainsLazy(self) -> None:
        """Skip a custom constructor while warming a standard static action.

        Returns
        -------
        None
            No constructor plan is built and its descriptor is not evaluated.
        """
        callable_misses = _callable_plan.cache_info().misses
        warm_controller_plan(_CustomConstructorController, "action")
        self.assertEqual(constructor_plan.cache_info().misses, 0)
        self.assertEqual(_callable_plan.cache_info().misses, callable_misses + 1)

    async def testInvalidSignatureFailsBeforeDispatchTablesArePublished(self) -> None:
        """Reject invalid standard function metadata during readiness.

        Returns
        -------
        None
            Boot reports the reflection error without publishing partial tables.
        """
        route = make_route("invalid_signature_handler")
        self.kernel._KernelHTTP__routes = RouteResolver(routes={
            "GET": {"static": {route.path: route}, "dynamic": []},
        })
        with self.assertRaisesRegex(ValueError, "Unable to inspect signature"):
            await self.kernel._KernelHTTP__preloadHandlers()
        self.assertFalse(hasattr(self.kernel, "_KernelHTTP__fn_dispatch"))
