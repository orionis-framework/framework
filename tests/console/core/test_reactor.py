from __future__ import annotations
import argparse
import inspect
from unittest.mock import AsyncMock, MagicMock
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.core.reactor import Reactor
from orionis.console.entities.command import Command
from orionis.console.fluent.contracts.command import ICommand
from orionis.failure.enums.kernel_type import KernelContext
from orionis.test import TestCase

def _make_mock_command(
    signature: str = "test:cmd",
    description: str = "A test command",
    *,
    timestamps: bool = True,
    args: argparse.ArgumentParser | None = None,
) -> Command:
    """
    Build a Command dataclass instance for use in tests.

    Parameters
    ----------
    signature : str
        Command signature string.
    description : str
        Human-readable command description.
    timestamps : bool
        Whether the command emits timestamp output.
    args : argparse.ArgumentParser or None
        Optional argument parser for the command.

    Returns
    -------
    Command
        Populated Command instance.
    """
    obj = MagicMock()
    return Command(
        obj=obj,
        method="handle",
        signature=signature,
        description=description,
        timestamps=timestamps,
        args=args,
    )

def _make_reactor() -> tuple[
    Reactor,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    """
    Construct a Reactor instance with fully mocked dependencies.

    Returns
    -------
    tuple
        A tuple of (reactor, mock_app, mock_loader, mock_executer,
        mock_logger, mock_catch, mock_performance_counter).
    """
    # Scope mock — used inside beginScope async context manager
    mock_scope = MagicMock()
    mock_scope.set = MagicMock()

    # Async context manager returned by beginScope
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_scope)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    # Application mock
    mock_app = MagicMock()
    mock_app.beginScope.return_value = mock_ctx
    mock_app.instance = MagicMock()
    mock_app.build = AsyncMock(return_value=MagicMock())
    mock_app.call = AsyncMock()

    # Loader mock
    mock_loader = MagicMock()
    mock_loader.addFluentCommand = MagicMock(return_value=MagicMock())
    mock_loader.all = AsyncMock(return_value={})
    mock_loader.get = AsyncMock(return_value=None)

    # Executor mock
    mock_executer = MagicMock()

    # Logger mock
    mock_logger = MagicMock()

    # Catch mock
    mock_catch = MagicMock()
    mock_catch.exception = AsyncMock()

    # Performance counter mock
    mock_perf = MagicMock()
    mock_perf.astart = AsyncMock()
    mock_perf.astop = AsyncMock()
    mock_perf.agetSeconds = AsyncMock(return_value=0.5)

    reactor = Reactor(
        app=mock_app,
        loader=mock_loader,
        executer=mock_executer,
        logger=mock_logger,
        catch=mock_catch,
        performance_counter=mock_perf,
    )
    return (
        reactor,
        mock_app,
        mock_loader,
        mock_executer,
        mock_logger,
        mock_catch,
        mock_perf,
    )

class TestReactor(TestCase):
    """Test suite for the Reactor console command dispatcher."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method.

        Creates a Reactor instance with fully mocked dependencies so that
        each test runs in complete isolation.

        Returns
        -------
        None
            Completes the operation described above.
        """
        (
            self.reactor,
            self.mock_app,
            self.mock_loader,
            self.mock_executer,
            self.mock_logger,
            self.mock_catch,
            self.mock_perf,
        ) = _make_reactor()

    # ------------------------------------------------------------------ #
    #  Interface & instantiation                                         #
    # ------------------------------------------------------------------ #

    def testInheritsFromIReactor(self) -> None:
        """Verify that Reactor inherits from IReactor.

        Ensures the implementation follows the expected class hierarchy
        and satisfies the abstract interface contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Reactor, IReactor))
        self.assertIsInstance(self.reactor, IReactor)

    def testCanBeInstantiated(self) -> None:
        """Verify that Reactor can be instantiated with valid dependencies.

        Confirms that object construction succeeds without raising exceptions
        when all required dependencies are provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(self.reactor, Reactor)

    def testHasRequiredMethods(self) -> None:
        """Verify that Reactor exposes all required public methods.

        Checks that the command, info, and call methods are present
        and callable on the Reactor instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(self.reactor.command))
        self.assertTrue(callable(self.reactor.hasCommand))
        self.assertTrue(callable(self.reactor.info))
        self.assertTrue(callable(self.reactor.call))

    def testInfoAndCallAreAsyncMethods(self) -> None:
        """Verify that info and call are declared as coroutine functions.

        Ensures the async contract defined in IReactor is fulfilled
        by the concrete Reactor implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(self.reactor.info))
        self.assertTrue(inspect.iscoroutinefunction(self.reactor.call))

    def testHasCommandIsAsyncMethod(self) -> None:
        """Verify that hasCommand is declared as a coroutine function.

        Returns
        -------
        None
            Confirms that signature lookup follows the asynchronous loader API.
        """
        self.assertTrue(inspect.iscoroutinefunction(self.reactor.hasCommand))

    def testCommandIsNotAsync(self) -> None:
        """Verify that the command registration method is synchronous.

        Ensures that command registration does not require an event loop,
        maintaining consistency with the interface definition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(inspect.iscoroutinefunction(self.reactor.command))

    def testInternalStateIsInitialized(self) -> None:
        """Verify that internal state attributes are set correctly on init.

        Checks that the cache, app, loader, executer, logger, catch, and
        performance counter are stored as private attributes after construction.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(self.reactor._Reactor__cache_info)
        self.assertIs(self.reactor._Reactor__app, self.mock_app)
        self.assertIs(self.reactor._Reactor__loader, self.mock_loader)
        self.assertIs(self.reactor._Reactor__executer, self.mock_executer)
        self.assertIs(self.reactor._Reactor__logger, self.mock_logger)
        self.assertIs(self.reactor._Reactor__catch, self.mock_catch)
        self.assertIs(self.reactor._Reactor__performance_counter, self.mock_perf)

    # ------------------------------------------------------------------ #
    #  command() method                                                  #
    # ------------------------------------------------------------------ #

    def testCommandDelegatesToLoader(self) -> None:
        """Verify that command() proxies to the loader's addFluentCommand.

        Ensures that calling reactor.command() with a signature and handler
        invokes the loader and returns its result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = MagicMock()
        self.mock_loader.addFluentCommand.return_value = expected
        handler = [MagicMock(), "handle"]

        result = self.reactor.command("greet", handler)

        self.mock_loader.addFluentCommand.assert_called_once_with("greet", handler)
        self.assertIs(result, expected)

    def testCommandReturnsICommandInstance(self) -> None:
        """Verify that command() returns whatever the loader returns.

        Ensures the return value from the loader is passed back to the
        caller without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_icommand = MagicMock(spec=ICommand)
        self.mock_loader.addFluentCommand.return_value = mock_icommand

        result = self.reactor.command("make:thing", [MagicMock()])

        self.assertIs(result, mock_icommand)

    # ------------------------------------------------------------------ #
    #  info() method                                                     #
    # ------------------------------------------------------------------ #

    async def testHasCommandUsesDirectLoaderLookup(self) -> None:
        """Look up one signature without requesting the full command list.

        Returns
        -------
        None
            Verifies the targeted loader call and its boolean result.
        """
        self.mock_loader.get = AsyncMock(return_value=_make_mock_command())

        result = await self.reactor.hasCommand("test:cmd")

        self.assertTrue(result)
        self.mock_loader.get.assert_awaited_once_with("test:cmd")
        self.mock_loader.all.assert_not_awaited()

    async def testHasCommandReturnsFalseForUnknownSignature(self) -> None:
        """Return false when the loader cannot resolve a signature.

        Returns
        -------
        None
            Verifies an absent command is reported without listing commands.
        """
        self.mock_loader.get = AsyncMock(return_value=None)

        result = await self.reactor.hasCommand("unknown:cmd")

        self.assertFalse(result)
        self.mock_loader.get.assert_awaited_once_with("unknown:cmd")
        self.mock_loader.all.assert_not_awaited()

    async def testInfoReturnsEmptyListWhenNoCommands(self) -> None:
        """Verify that info() returns an empty list when no commands are loaded.

        Ensures that an empty registry produces an empty result set
        without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.mock_loader.all = AsyncMock(return_value={})
        result = await self.reactor.info()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    async def testInfoIncludesNormalCommands(self) -> None:
        """Verify that info() includes commands with regular signatures.

        Ensures that commands whose signatures do not start and end with
        double underscores are included in the result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="greet", description="Say hello")
        self.mock_loader.all = AsyncMock(return_value={"greet": cmd})

        result = await self.reactor.info()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["signature"], "greet")
        self.assertEqual(result[0]["description"], "Say hello")

    async def testInfoSkipsInternalCommands(self) -> None:
        """Verify that info() excludes internal commands delimited by dunder syntax.

        Ensures that commands whose signatures are both prefixed and suffixed
        with double underscores are filtered out from the result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        internal = _make_mock_command(signature="__internal__")
        normal = _make_mock_command(signature="normal:cmd")
        self.mock_loader.all = AsyncMock(return_value={
            "__internal__": internal,
            "normal:cmd": normal,
        })

        result = await self.reactor.info()

        signatures = [item["signature"] for item in result]
        self.assertNotIn("__internal__", signatures)
        self.assertIn("normal:cmd", signatures)

    async def testInfoReturnsSortedBySignature(self) -> None:
        """Verify that info() returns commands sorted alphabetically by signature.

        Ensures the result list is ordered consistently regardless of the
        internal dict insertion order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.mock_loader.all = AsyncMock(return_value={
            "z:cmd": _make_mock_command(signature="z:cmd"),
            "a:cmd": _make_mock_command(signature="a:cmd"),
            "m:cmd": _make_mock_command(signature="m:cmd"),
        })

        result = await self.reactor.info()

        signatures = [item["signature"] for item in result]
        self.assertEqual(signatures, sorted(signatures))

    async def testInfoCachesResultsOnSecondCall(self) -> None:
        """Verify that info() caches its result and avoids redundant loader calls.

        Ensures that the loader's all() method is only invoked once across
        multiple calls to info() on the same Reactor instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="cached:cmd")
        self.mock_loader.all = AsyncMock(return_value={"cached:cmd": cmd})

        first = await self.reactor.info()
        second = await self.reactor.info()

        self.assertEqual(first, second)
        self.mock_loader.all.assert_called_once()

    async def testInfoResultContainsExpectedKeys(self) -> None:
        """Verify that each item returned by info() contains the expected keys.

        Ensures that the information dictionary per command exposes all
        required metadata fields for downstream consumption.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="check:keys")
        self.mock_loader.all = AsyncMock(return_value={"check:keys": cmd})

        result = await self.reactor.info()

        self.assertEqual(len(result), 1)
        item = result[0]
        for key in (
            "timestamps",
            "signature",
            "description",
            "arguments",
            "object",
            "method",
        ):
            self.assertIn(key, item)

    # ------------------------------------------------------------------ #
    #  call() — success paths                                            #
    # ------------------------------------------------------------------ #

    async def testCallReturnsZeroOnSuccessfulExecution(self) -> None:
        """Verify that call() returns 0 when a command executes successfully.

        Ensures the success exit code convention is honoured for commands
        that run without raising exceptions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="hello", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.call = AsyncMock(return_value=None)

        result = await self.reactor.call("hello")

        self.assertEqual(result, 0)

    async def testCallLogsSuccessMessage(self) -> None:
        """Verify that call() logs an info message after successful execution.

        Ensures the logger's info() method is invoked exactly once when
        a command finishes without errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="log:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        await self.reactor.call("log:cmd")

        self.mock_logger.info.assert_called_once()

    async def testCallDoesNotRecreateClearedLogs(self) -> None:
        """Leave log files absent after the log cleanup command completes.

        Returns
        -------
        None
            The reactor does not write a new completion log entry.
        """
        command = _make_mock_command(signature="clear:logs", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=command)

        result = await self.reactor.call("clear:logs")

        self.assertEqual(result, 0)
        self.mock_logger.info.assert_not_called()

    async def testCallBuildsCommandInstanceViaApp(self) -> None:
        """Verify that call() uses the app container to build the command instance.

        Ensures that app.build() is invoked with the command's class object
        so that dependency injection is applied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="di:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        await self.reactor.call("di:cmd")

        self.mock_app.build.assert_awaited_once_with(cmd.obj)

    async def testCallInvokesCommandViaApp(self) -> None:
        """Verify that call() delegates command execution to app.call().

        Ensures that the resolved command instance and method are passed to
        the application container for actual execution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="exec:cmd", timestamps=False)
        instance = MagicMock()
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.build = AsyncMock(return_value=instance)

        await self.reactor.call("exec:cmd")

        self.mock_app.call.assert_awaited_once_with(instance, cmd.method)

    async def testCallWithTimestampsEmitsRunningAndDone(self) -> None:
        """Verify that call() emits running and done output when timestamps enabled.

        Ensures that the executer's running() and done() methods are called
        when a command has timestamps=True and no help flag is passed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="ts:cmd", timestamps=True)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        await self.reactor.call("ts:cmd")

        self.mock_executer.running.assert_called_once_with(program="ts:cmd")
        self.mock_executer.done.assert_called_once()

    async def testCallWithTimestampsHelpFlagSuppressesOutput(self) -> None:
        """Verify that help flag suppresses timestamp output during call().

        Ensures that passing -h or --help prevents the running/done
        executer calls even when timestamps are enabled on the command.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="ts:help", timestamps=True)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        await self.reactor.call("ts:help", args=["-h"])

        self.mock_executer.running.assert_not_called()

    async def testCallStartsAndStopsPerformanceCounter(self) -> None:
        """Verify that call() starts and stops the performance counter.

        Ensures that astart() and astop() are both invoked during a
        command execution cycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="perf:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        await self.reactor.call("perf:cmd")

        self.mock_perf.astart.assert_awaited_once()
        self.mock_perf.astop.assert_awaited_once()

    async def testCallSetsKernelContextOnScope(self) -> None:
        """Verify that call() sets the kernel context on the scope.

        Ensures that the console kernel type is stored in the scope
        at the start of each command execution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="scope:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)

        # Extract the scope mock through the ctx manager
        scope_mock = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=scope_mock)
        ctx.__aexit__ = AsyncMock(return_value=False)
        self.mock_app.beginScope.return_value = ctx

        await self.reactor.call("scope:cmd")

        scope_mock.set.assert_called_once_with("kernel", KernelContext.CONSOLE)

    # ------------------------------------------------------------------ #
    #  call() — failure / error paths                                    #
    # ------------------------------------------------------------------ #

    async def testCallReturnsOneWhenCommandNotFound(self) -> None:
        """Verify that call() returns 1 when the command signature is not registered.

        Ensures the failure exit code is returned and the exception handler
        is invoked when the loader returns None for the given signature.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.mock_loader.get = AsyncMock(return_value=None)

        result = await self.reactor.call("nonexistent:cmd")

        self.assertEqual(result, 1)
        self.mock_catch.exception.assert_awaited_once()

    async def testCallLogsErrorOnFailure(self) -> None:
        """Verify that call() logs an error message when execution fails.

        Ensures the logger's error() method is called when an exception
        occurs during command dispatching, with the exception raised after
        the command object has already been resolved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="crash:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.build = AsyncMock(side_effect=RuntimeError("boom"))

        await self.reactor.call("crash:cmd")

        self.mock_logger.error.assert_called_once()

    async def testCallDelegatesExceptionToCatch(self) -> None:
        """Verify that call() delegates exceptions to the catch service.

        Ensures that any unhandled exception during execution is passed
        to catch.exception() for centralised error handling, with the
        exception raised after the command object has been resolved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        error = RuntimeError("fatal")
        cmd = _make_mock_command(signature="error:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.build = AsyncMock(side_effect=error)

        await self.reactor.call("error:cmd")

        self.mock_catch.exception.assert_awaited_once_with(error)

    async def testCallEmitsFailOutputOnExceptionWithTimestamps(self) -> None:
        """Verify that call() emits fail output when a command with timestamps errors.

        Ensures the executer's fail() is called when a registered command
        that has timestamps=True raises an exception during execution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="fail:cmd", timestamps=True)
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.build = AsyncMock(side_effect=RuntimeError("build error"))

        await self.reactor.call("fail:cmd")

        self.mock_executer.fail.assert_called_once()

    async def testCallStopsPerformanceCounterOnFailure(self) -> None:
        """Verify that call() stops the performance counter even when execution fails.

        Ensures that astop() is always called so that the timer is properly
        cleaned up regardless of success or failure, with the exception
        raised after command resolution so the except block runs cleanly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="stop:cmd", timestamps=False)
        self.mock_loader.get = AsyncMock(return_value=cmd)
        self.mock_app.build = AsyncMock(side_effect=RuntimeError("stop me"))

        await self.reactor.call("stop:cmd")

        self.mock_perf.astop.assert_awaited_once()

    # ------------------------------------------------------------------ #
    #  __parseCommandArgs() — private method via direct access           #
    # ------------------------------------------------------------------ #

    def testParseCommandArgsReturnsEmptyDictWhenNoParser(self) -> None:
        """Verify that __parseCommandArgs returns an empty dict without a parser.

        Ensures that commands without an ArgumentParser configured yield
        an empty argument dict without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="no:args", args=None)
        result = self.reactor._Reactor__parseCommandArgs(cmd, [])
        self.assertEqual(result, {})

    def testParseCommandArgsReturnsEmptyDictForNoneArgs(self) -> None:
        """Verify that __parseCommandArgs handles None args gracefully.

        Ensures that passing None as the args parameter does not raise
        an error when the command also has no ArgumentParser.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = _make_mock_command(signature="none:args", args=None)
        result = self.reactor._Reactor__parseCommandArgs(cmd, None)
        self.assertEqual(result, {})

    def testParseCommandArgsWithValidParser(self) -> None:
        """Verify that __parseCommandArgs correctly parses known arguments.

        Ensures that when a command has an ArgumentParser with defined
        arguments, they are parsed and returned as a dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("--name", type=str, default="world")
        cmd = _make_mock_command(signature="greet:args", args=parser)

        result = self.reactor._Reactor__parseCommandArgs(cmd, ["--name", "alice"])

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("name"), "alice")

    def testParseCommandArgsWithDefaultValues(self) -> None:
        """Verify that __parseCommandArgs returns default argument values.

        Ensures that missing optional arguments are populated with their
        configured default values from the ArgumentParser.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("--count", type=int, default=42)
        cmd = _make_mock_command(signature="count:args", args=parser)

        result = self.reactor._Reactor__parseCommandArgs(cmd, [])

        self.assertEqual(result.get("count"), 42)

    def testParseCommandArgsExitsOnInvalidArgument(self) -> None:
        """Verify that __parseCommandArgs triggers SystemExit on unrecognised options.

        Ensures that argparse raises SystemExit when an unknown flag is
        passed, which is then re-raised as a SystemExit by the method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("--valid", type=str)
        cmd = _make_mock_command(signature="strict:args", args=parser)

        with self.assertRaises(SystemExit):
            self.reactor._Reactor__parseCommandArgs(cmd, ["--unknown"])
