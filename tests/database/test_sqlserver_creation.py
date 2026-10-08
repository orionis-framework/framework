"""Cancellation safety of the SQL Server native client creation boundary."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from orionis.database.dialect import _AsyncNativeCreator, configure_engine
from orionis.test import TestCase


class TestSQLServerNativeCreation(TestCase):
    """Preserve native parameters and close late resources after cancellation."""

    async def testNativeCreatorPreservesArgumentsAndActualClient(self) -> None:
        """
        Verify that native creation preserves arguments and client identity.

        Returns
        -------
        None
            Confirm unchanged ODBC arguments and the original client instance.
        """
        observed = []
        client = object()

        async def create(*args: object, **kwargs: object) -> object:
            """
            Record the factory arguments and return the selected client.

            Parameters
            ----------
            *args : object
                Positional arguments recorded without modification.
            **kwargs : object
                Keyword arguments recorded without modification.

            Returns
            -------
            object
                The preselected client instance.
            """
            observed.append((args, kwargs))
            return client

        returned = await _AsyncNativeCreator(create)(
            "owned-dsn", timeout=5, autocommit=True,
        )
        self.assertIs(returned, client)
        self.assertEqual(
            observed, [(("owned-dsn",), {"timeout": 5, "autocommit": True})],
        )

    async def testRepeatedCancellationDrainsCreationAndLateClientClose(self) -> None:
        """
        Verify that repeated cancellation waits for late client cleanup.

        Returns
        -------
        None
            Confirm cancellation propagates only after asynchronous close ends.
        """
        entered, connected, closing, closed = [asyncio.Event() for _ in range(4)]

        async def close() -> None:
            """
            Wait for the simulated client close to be released.

            Returns
            -------
            None
                Signal close entry and finish when the release event is set.
            """
            closing.set()
            await closed.wait()

        client = SimpleNamespace(close=close)

        async def create() -> object:
            """
            Wait for connection release and return the late client.

            Returns
            -------
            SimpleNamespace
                The simulated client with an asynchronous close method.
            """
            entered.set()
            await connected.wait()
            return client

        task = asyncio.create_task(_AsyncNativeCreator(create)())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            connected.set()
            await asyncio.wait_for(closing.wait(), 1)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            closed.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
        finally:
            connected.set()
            closed.set()
            await asyncio.gather(task, return_exceptions=True)

    async def testFailureAfterCancellationIsCollectedWithoutUnhandledTask(self) -> None:
        """
        Verify that cancellation collects a delayed native creation failure.

        Returns
        -------
        None
            Confirm cancellation takes precedence without unhandled task errors.
        """
        entered, release = asyncio.Event(), asyncio.Event()
        loop = asyncio.get_running_loop()
        previous = loop.get_exception_handler()
        errors = []

        def capture_error(current_loop, context):
            """
            Record the exception context and delegate to the active handler.

            Parameters
            ----------
            current_loop : asyncio.AbstractEventLoop
                Event loop reporting the unhandled exception.
            context : dict[str, object]
                Exception context to record and forward.

            Returns
            -------
            None
                Invoke the previous handler or the loop's default handler.
            """
            errors.append(context)
            if previous:
                previous(current_loop, context)
            else:
                current_loop.default_exception_handler(context)

        loop.set_exception_handler(capture_error)

        async def create() -> object:
            """
            Raise a native creation failure after explicit release.

            Raises
            ------
            RuntimeError
                Always raised once the release event is set.
            """
            entered.set()
            await release.wait()
            message = "Expected native creation failure."
            raise RuntimeError(message)

        task = asyncio.create_task(_AsyncNativeCreator(create)())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
            await asyncio.sleep(0)
            self.assertEqual(errors, [])
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
            loop.set_exception_handler(previous)

    def testDoConnectWrapsCustomCreatorOnceWithoutChangingUrlParameters(self) -> None:
        """
        Verify that custom creators wrap once without changing URL parameters.

        Returns
        -------
        None
            Confirm wrapper identity and unchanged timeout and autocommit values.
        """
        engine = SimpleNamespace(
            sync_engine=SimpleNamespace(dialect=SimpleNamespace(driver="aioodbc")),
        )
        listeners = []

        def capture(_engine: object, name: str):
            """
            Build a recording decorator for the requested engine event.

            Parameters
            ----------
            _engine : object
                Engine supplied to the registrar; unused by this double.
            name : str
                Event name associated with the recorded callback.

            Returns
            -------
            callable
                Decorator that records and returns the supplied callback.
            """

            def decorate(callback):
                """
                Record the listener without replacing its callback.

                Parameters
                ----------
                callback : callable
                    Listener to associate with the captured event name.

                Returns
                -------
                callable
                    The original callback, unchanged.
                """
                listeners.append((name, callback))
                return callback
            return decorate

        async def custom() -> object:
            """
            Return a placeholder client from the custom asynchronous creator.

            Returns
            -------
            object
                A new placeholder client instance.
            """
            return object()

        with patch("orionis.database.dialect.event.listens_for", capture):
            configure_engine(engine, {"driver": "sqlserver"})
        self.assertEqual([name for name, _callback in listeners], ["do_connect"])
        callback = listeners[0][1]
        parameters = {"async_creator_fn": custom, "timeout": 5, "autocommit": True}
        callback(None, None, ["owned-dsn"], parameters)
        wrapped = parameters["async_creator_fn"]
        callback(None, None, ["owned-dsn"], parameters)
        self.assertIs(parameters["async_creator_fn"], wrapped)
        self.assertIs(wrapped._creator, custom)
        self.assertEqual(parameters["timeout"], 5)
        self.assertIs(parameters["autocommit"], True)
