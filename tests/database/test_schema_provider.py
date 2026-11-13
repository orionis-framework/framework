# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.contracts.schema import ISchema
from orionis.database.schema.schema import Schema
from orionis.database.schema_provider import SchemaProvider
from orionis.test import TestCase


class _CaptureApp:
    """Application stub capturing transient and singleton registrations."""

    def __init__(self) -> None:
        """Initialize the test double.

        Returns
        -------
        None
            No return value.
        """
        self.transient_bindings: list[tuple[type, type]] = []
        self.singleton_bindings: list[tuple[type, type]] = []

    def transient(self, contract: type, implementation: type) -> None:
        """Record a transient service registration.

        Parameters
        ----------
        contract : type
            Value supplied for ``contract``.
        implementation : type
            Value supplied for ``implementation``.

        Returns
        -------
        None
            No return value.
        """
        self.transient_bindings.append((contract, implementation))

    def singleton(self, contract: type, implementation: type) -> None:
        """Record a singleton service registration.

        Parameters
        ----------
        contract : type
            Value supplied for ``contract``.
        implementation : type
            Value supplied for ``implementation``.

        Returns
        -------
        None
            No return value.
        """
        self.singleton_bindings.append((contract, implementation))


class TestSchemaProvider(TestCase):
    def testProviderInheritsFrameworkBase(self) -> None:
        """Extend the framework ServiceProvider base.

        Validates the provider class hierarchy.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(SchemaProvider, ServiceProvider))

    def testRegisterBindsSchemaAsTransient(self) -> None:
        """Bind ISchema to Schema using a transient lifetime.

        Validates that no state leaks between resolutions, since Schema
        retains an explicit connection selection between operations.

        Returns
        -------
        None
            No return value.
        """
        app = _CaptureApp()
        provider = SchemaProvider(app)  # type: ignore[arg-type]
        provider.register()
        self.assertEqual(app.transient_bindings, [(ISchema, Schema)])
        self.assertEqual(app.singleton_bindings, [])

    async def testBootIsANoOpInheritedFromTheBase(self) -> None:
        """Perform no additional wiring during boot.

        Validates that SchemaProvider relies entirely on the inherited
        no-op boot implementation and does not register extra bindings.

        Returns
        -------
        None
            No return value.
        """
        app = _CaptureApp()
        provider = SchemaProvider(app)  # type: ignore[arg-type]
        provider.register()
        result = await provider.boot()
        self.assertIsNone(result)
        self.assertEqual(app.transient_bindings, [(ISchema, Schema)])
        self.assertEqual(app.singleton_bindings, [])
