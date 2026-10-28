import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from orionis.console.debug.contracts.dumper import IDumper
from orionis.console.debug.dumper import Dumper
from orionis.console.debug.provider import DumperProvider
from orionis.container.container import Container
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.core_providers import CORE_PROVIDER_METADATA
from orionis.support.facades.debug import Debug
from orionis.test import TestCase

class TestDumperProvider(TestCase):

    def testIsAnEagerCoreProvider(self) -> None:
        """
        Verify that the dumper is an eager core provider with asynchronous boot.

        Returns
        -------
        None
            This test does not return a value.
        """
        self.assertTrue(issubclass(DumperProvider, ServiceProvider))
        self.assertFalse(issubclass(DumperProvider, DeferrableProvider))
        self.assertTrue(inspect.iscoroutinefunction(DumperProvider.boot))
        self.assertIn(
            ("orionis.console.debug.provider", "DumperProvider"),
            CORE_PROVIDER_METADATA,
        )

    def testRegistersTheContractAndFacadeAliasAsASingleton(self) -> None:
        """
        Verify singleton registration and consistency with the facade alias.

        Returns
        -------
        None
            This test does not return a value.
        """
        app = MagicMock(spec=IApplication)

        DumperProvider(app).register()

        app.singleton.assert_called_once_with(
            IDumper, Dumper, alias="x-orionis-IDumper",
        )
        self.assertEqual(Debug.getFacadeAccessor(), "x-orionis-IDumper")

    async def testBootPinsTheRegisteredSingletonForSynchronousCalls(self) -> None:
        """
        Verify that boot pins the registered singleton for synchronous calls.

        Returns
        -------
        None
            This test does not return a value.
        """
        container = Container()
        app = MagicMock(spec=IApplication)
        app.isBooted = True
        app.singleton.side_effect = container.singleton
        app.make = AsyncMock(side_effect=container.make)
        provider = DumperProvider(app)
        provider.register()

        service = await container.make(IDumper)
        self.assertIsInstance(service, Dumper)
        self.assertIs(
            await container.make(Debug.getFacadeAccessor()), service,
        )

        with (
            patch.object(Debug, "_application", app),
            patch.object(Debug, "_pinned_instance", None),
        ):
            await provider.boot()

            self.assertIs(Debug._pinned_instance, service)
            self.assertIs(Debug.dump, Dumper.dump)
            self.assertIs(Debug.dd, Dumper.dd)
            self.assertFalse(inspect.iscoroutinefunction(Debug.dump))
            self.assertFalse(inspect.iscoroutinefunction(Debug.dd))

        app.make.assert_awaited_once_with(Debug.getFacadeAccessor())
        app.singleton.assert_called_once()

    async def testBootPropagatesResolutionErrors(self) -> None:
        """
        Verify that boot propagates facade initialization errors.

        Returns
        -------
        None
            This test does not return a value.
        """
        app = MagicMock(spec=IApplication)
        with (
            patch.object(
                Debug,
                "pin",
                new_callable=AsyncMock,
                side_effect=RuntimeError("dumper unavailable"),
            ),
            self.assertRaisesRegex(RuntimeError, "dumper unavailable"),
        ):
            await DumperProvider(app).boot()
