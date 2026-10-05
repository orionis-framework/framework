import asyncio
import gc
import weakref
from collections.abc import AsyncIterator  # noqa: TC003 - Runtime reflection.
from typing import TYPE_CHECKING, Annotated, cast
from unittest.mock import patch
import msgspec
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.realtime import Hub, remote
from orionis.realtime.errors import RPCError
from orionis.realtime.metadata import compile_hub
from orionis.schemas.constraints import StrongPassword
from orionis.schemas.schema import Schema
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping
    from orionis.realtime.metadata import RemoteMethod

class _Service:
    """Provide an injectable dependency unrelated to client payloads."""

class _Payload(Schema):
    """Require both a typed value and an existing Orionis custom rule."""

    count: int
    password: Annotated[str, StrongPassword()]

class _Envelope(msgspec.Struct):
    """Contain Orionis schemas inside an ordinary Struct."""

    values: list[_Payload]

class _SchemaCollection(Schema):
    """Contain schema collections requiring explicit traversal."""

    values: list[_Payload]

class _MethodsHub(Hub):
    """Exercise dispatch, schemas, defaults and container parameters together."""

    def __init__(self, service: _Service) -> None:
        """
        Retain constructor-injected scoped state.

        Parameters
        ----------
        service : _Service
            Service resolved from the active invocation scope.

        Returns
        -------
        None
            Preserve the injected instance for assertions.
        """
        self.service = service

    @remote(name="sum")
    async def add(self, first: int, service: _Service, second: int = 2) -> int:
        """
        Return an integer after checking method and constructor DI agree.

        Parameters
        ----------
        first : int
            Client operand.
        service : _Service
            Container operand that cannot be supplied by the client.
        second : int, optional
            Defaulted client operand.

        Returns
        -------
        int
            Sum of validated operands.

        Raises
        ------
        RuntimeError
            If method and constructor injection resolve different services.
        """
        if service is not self.service:
            message = "Scoped dependency changed inside invocation"
            raise RuntimeError(message)
        return first + second

    @remote
    def sync(self, value: str, *, upper: bool = False) -> str:
        """
        Return a synchronous result from explicitly typed client arguments.

        Parameters
        ----------
        value : str
            Client text.
        upper : bool, optional
            Named client option.

        Returns
        -------
        str
            Original or uppercase text.
        """
        return value.upper() if upper else value

    @remote
    def payload(self, value: _Payload | None = None) -> _Payload | None:
        """
        Return a typed schema without accessing any HTTP request.

        Parameters
        ----------
        value : _Payload | None, optional
            Schema or explicitly nullable default.

        Returns
        -------
        _Payload | None
            Validated input.
        """
        return value

    @remote
    def dependency(self, service: _Service | None = None) -> _Service | None:
        """
        Keep a defaulted service parameter under container ownership.

        Parameters
        ----------
        service : _Service | None, optional
            Injected service despite its nullable declared default.

        Returns
        -------
        _Service | None
            Injected value.
        """
        return service

    @remote
    async def stream(self) -> AsyncIterator[int]:
        """
        Yield items without buffering the invocation result.

        Yields
        ------
        int
            One streamed item.
        """
        yield 1

    def helper(self) -> str:
        """
        Represent a public method that is not remotely exposed.

        Returns
        -------
        str
            Local helper result.
        """
        return "private to application"

class TestRemoteMetadata(TestCase):
    """Verify that client data never becomes executable metadata or DI input."""

    def testOnlyDecoratedMethodsAreExposedAndPlanIsCached(self) -> None:
        """
        Exclude every undeclared helper and reuse immutable dispatch metadata.

        Returns
        -------
        None
            Alias and cache assertions hold.
        """
        methods = compile_hub(_MethodsHub)
        self.assertEqual(
            set(methods), {"sum", "sync", "payload", "dependency", "stream"},
        )
        self.assertEqual(methods["sum"].method_name, "add")
        self.assertTrue(methods["stream"].is_stream)
        self.assertFalse(methods["sum"].is_stream)
        with patch("orionis.realtime.metadata.get_type_hints") as reflection:
            self.assertIs(methods, compile_hub(_MethodsHub))
            reflection.assert_not_called()
        with self.assertRaises(TypeError):
            mutable = cast("MutableMapping[str, RemoteMethod]", methods)
            mutable["helper"] = methods["sum"]

    def testArgumentsExcludeDependenciesAndCannotOverrideThem(self) -> None:
        """
        Interpret positional indexes only across client-bound parameters.

        Returns
        -------
        None
            DI override, excess and duplicate arguments are rejected.
        """
        method = compile_hub(_MethodsHub)["sum"]
        self.assertEqual(method.dependencies, {"service": _Service})
        self.assertEqual(method.bind([3, 4], {}), {"first": 3, "second": 4})
        self.assertEqual(method.bind([], {"first": 3}), {"first": 3, "second": 2})
        cases = [
            ([3], {"service": "malicious"}),
            ([3, "malicious", 4], {}),
            ([3], {"first": 4}),
            ([], {}),
            ([3], {"unknown": 1}),
        ]
        for args, kwargs in cases:
            with (
                self.subTest(args=args, kwargs=kwargs),
                self.assertRaises(RPCError) as exc,
            ):
                method.bind(args, kwargs)
            self.assertEqual(exc.exception.code, "invalid_arguments")

    def testDefaultsRetainAnnotationsAndDoNotCoerceClientTypes(self) -> None:
        """
        Prevent strings or booleans from replacing integer parameters.

        Returns
        -------
        None
            Defaults and strict msgspec conversion remain enforced.
        """
        method = compile_hub(_MethodsHub)["sum"]
        for args in (["3"], [True], [3, "4"]):
            with self.subTest(args=args), self.assertRaises(RPCError) as exc:
                method.bind(list(args), {})
            self.assertEqual(exc.exception.code, "validation_error")
        dependency = compile_hub(_MethodsHub)["dependency"]
        self.assertEqual(dependency.dependencies, {"service": _Service})
        self.assertEqual(dependency.bind([], {}), {})
        with self.assertRaises(RPCError):
            dependency.bind([], {"service": None})

    def testKeywordOnlyParametersCannotConsumePositionalArguments(self) -> None:
        """
        Keep keyword-only parameters explicit on the wire.

        Returns
        -------
        None
            Positional values cannot override keyword-only defaults.
        """
        method = compile_hub(_MethodsHub)["sync"]
        self.assertEqual(
            method.bind(["a"], {"upper": True}), {"value": "a", "upper": True},
        )
        with self.assertRaises(RPCError):
            method.bind(["a", True], {})

    def testSchemasUseFrameworkConversionAndCustomRules(self) -> None:
        """
        Reuse schema rules with RPC values without resolving Request.data().

        Returns
        -------
        None
            The nullable default and framework password rule are respected.
        """
        method = compile_hub(_MethodsHub)["payload"]
        self.assertEqual(method.bind([], {}), {"value": None})
        data = {"count": 2, "password": "CorrectHorse9!Battery"}
        bound = method.bind([data], {})
        value = bound["value"]
        if not isinstance(value, _Payload):
            self.fail("Expected a converted payload schema")
        self.assertEqual(value.count, 2)
        with self.assertRaises(RPCError) as exc:
            method.bind([{"count": 2, "password": "weak"}], {})
        self.assertEqual(exc.exception.code, "validation_error")

    def testSchemaCollectionsCannotBypassCustomValidationRules(self) -> None:
        """
        Apply custom rules to schemas nested inside RPC data collections.

        Returns
        -------
        None
            Typed collection wrapping cannot bypass an Orionis schema rule.
        """
        class CollectionHub(Hub):
            @remote
            def many(self, values: list[_Payload]) -> None:
                """
                Declare a collection requiring contained schema validation.

                Parameters
                ----------
                values : list[_Payload]
                    Client schemas whose nested rules must be enforced.

                Returns
                -------
                None
                    Provide a typed no-op endpoint for binding assertions.
                """

            @remote
            def wrapped(self, value: _Envelope) -> None:
                """
                Wrap schema rules inside an ordinary msgspec Struct.

                Parameters
                ----------
                value : _Envelope
                    Struct containing schemas with custom rules.

                Returns
                -------
                None
                    Provide a typed no-op endpoint for traversal assertions.
                """

            @remote
            def collection(self, value: _SchemaCollection) -> None:
                """
                Wrap schema rules inside another schema's collection field.

                Parameters
                ----------
                value : _SchemaCollection
                    Schema containing a collection of other schemas.

                Returns
                -------
                None
                    Provide a typed no-op endpoint for nested rule assertions.
                """

        method = compile_hub(CollectionHub)["many"]
        with self.assertRaises(RPCError) as exc:
            method.bind([[{"count": 1, "password": "weak"}]], {})
        self.assertEqual(exc.exception.code, "validation_error")
        self.assertEqual(method.bind([[]], {}), {"values": []})
        for name in ("wrapped", "collection"):
            with self.subTest(name=name), self.assertRaises(RPCError) as exc:
                compile_hub(CollectionHub)[name].bind([
                    {"values": [{"count": 1, "password": "weak"}]},
                ], {})
            self.assertEqual(exc.exception.code, "validation_error")

    async def testFreshContainerScopesPreserveConstructorAndMethodInjection(
        self,
    ) -> None:
        """
        Resolve a different scoped service for simultaneous invocations.

        Returns
        -------
        None
            Container calls preserve validated data and isolated dependencies.
        """
        container = object.__new__(Container)
        Container.__init__(container)
        container.scoped(_Service, _Service)
        method = compile_hub(_MethodsHub)["sum"]

        async def invoke() -> tuple[object, int]:
            """
            Build and invoke one hub in an independent scope.

            Returns
            -------
            tuple[object, int]
                The invocation's own service and remote result.
            """
            async with container.beginScope():
                hub = await container.build(_MethodsHub)
                bound = method.bind([3, 4], {})
                for name, service in method.dependencies.items():
                    bound[name] = await container.make(service)
                await asyncio.sleep(0)
                result = await container.call(hub, method.method_name, **bound)
                return hub.service, result

        async with container.beginScope() as parent:
            first, second = await asyncio.gather(invoke(), invoke())
            self.assertIsNot(first[0], second[0])
            self.assertEqual((first[1], second[1]), (7, 7))
            self.assertIs(ScopedContext.getCurrentScope(), parent)

    def testCachedMetadataDoesNotRetainHubInstances(self) -> None:
        """
        Keep bound receivers out of long-lived metadata caches.

        Returns
        -------
        None
            A hub is collected while its method metadata remains cached.
        """
        hub = _MethodsHub(_Service())
        reference = weakref.ref(hub)
        compile_hub(type(hub))
        del hub
        gc.collect()
        self.assertIsNone(reference())

    def testDecoratorDoesNotWrapTheFunction(self) -> None:
        """
        Retain the exact callable identity when marking it remote.

        Returns
        -------
        None
            No wrapper or second layer of invocation is introduced.
        """
        def local(self: object) -> None:
            """
            Represent an undecorated method for identity comparison.

            Returns
            -------
            None
                Provide the unchanged callable used by decorator assertions.
            """
        self.assertIs(remote(local), local)
        with self.assertRaises(ValueError):
            remote(local)

    def testDecoratorRejectsPrivateAndInvalidAliases(self) -> None:
        """
        Reject every alias capable of implying private or dotted lookup.

        Returns
        -------
        None
            Invalid names and noncallable objects fail during registration.
        """
        for name in ("", "_secret", "__class__", "module.target", "a" * 129):
            with self.subTest(name=name), self.assertRaises(ValueError):
                remote(name=name)
        with self.assertRaises(TypeError):
            remote(cast("Callable", 5))

    def testDuplicateAliasesFailDuringRegistration(self) -> None:
        """
        Reject alias collisions before any network request can use them.

        Returns
        -------
        None
            A duplicate dispatch name cannot silently replace a method.
        """
        class Duplicate(Hub):
            @remote(name="same")
            def first(self) -> None:
                """
                Expose the first conflicting alias.

                Returns
                -------
                None
                    Provide the first no-op endpoint with the shared alias.
                """

            @remote(name="same")
            def second(self) -> None:
                """
                Expose the second conflicting alias.

                Returns
                -------
                None
                    Provide the second no-op endpoint with the shared alias.
                """

        with self.assertRaises(ValueError):
            compile_hub(Duplicate)

    def testUndecoratedOverridesRemoveInheritedExposure(self) -> None:
        """
        Treat the subclass descriptor as the authoritative exposure decision.

        Returns
        -------
        None
            Inherited methods cannot bypass an explicitly undecorated override.
        """
        class Override(_MethodsHub):
            async def stream(self) -> AsyncIterator[int]:
                """
                Replace an inherited remote with a local-only method.

                Yields
                ------
                int
                    Local stream value that must not be remotely exposed.
                """
                yield 0

        self.assertNotIn("stream", compile_hub(Override))

    def testUnsafeSignaturesFailAtRegistration(self) -> None:
        """
        Reject static methods, unresolved types, variadics and mixed unions.

        Returns
        -------
        None
            Unsupported signatures never reach the runtime binder.
        """
        class Variadic(Hub):
            @remote
            def method(self, *values: int) -> None:
                """
                Represent a forbidden variadic signature.

                Parameters
                ----------
                *values : int
                    Variadic client values rejected during Hub compilation.

                Returns
                -------
                None
                    Provide a no-op endpoint with an unsupported signature.
                """

        class Mixed(Hub):
            @remote
            def method(self, value: int | _Service) -> None:
                """
                Represent an ambiguous client/service union.

                Parameters
                ----------
                value : int | _Service
                    Ambiguous client data or injected service annotation.

                Returns
                -------
                None
                    Provide a no-op endpoint with an unsupported union.
                """

        class Missing(Hub):
            @remote
            def method(self, value: object) -> None:
                """
                Represent an annotation unavailable at registration.

                Parameters
                ----------
                value : object
                    Parameter whose annotation is replaced with an unknown type.

                Returns
                -------
                None
                    Provide a no-op endpoint for unresolved annotation assertions.
                """

        class Static(Hub):
            @staticmethod
            @remote
            def method() -> None:
                """
                Represent an unsupported static descriptor.

                Returns
                -------
                None
                    Provide a static no-op endpoint rejected by Hub compilation.
                """

        Missing.method.__annotations__["value"] = "MissingService"
        for hub in (Variadic, Mixed, Missing, Static):
            with self.subTest(hub=hub), self.assertRaises(TypeError):
                compile_hub(hub)
