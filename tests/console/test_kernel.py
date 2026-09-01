import inspect
from orionis.console.contracts.kernel import IKernelCLI
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.kernel import KernelCLI
from orionis.test import TestCase

# Interpreter flags the kernel must strip before routing a command.
_INTERPRETER_FLAGS: tuple[str, ...] = ("-B", "-c", "-i", "-m", "-q", "-v")

# Tokens routed to the general command listing.
_HELP_TOKENS: tuple[str, ...] = ("help", "--help", "-h")

# Message reported when the argument list has the wrong type.
_TYPE_ERROR_MESSAGE = "Arguments must be provided as a list."


class _RecordingReactor:
    """Reactor double recording every dispatched signature."""

    __slots__ = ("calls", "exit_code")

    def __init__(self, exit_code: int = 0) -> None:
        """
        Initialise the call log and the exit code to report.

        Parameters
        ----------
        exit_code : int, optional
            Value returned by every ``call`` invocation.

        Returns
        -------
        None
        """
        self.calls: list[tuple[str, list[str] | None]] = []
        self.exit_code = exit_code

    async def call(
        self,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """
        Record a dispatch and report the configured exit code.

        Parameters
        ----------
        signature : str
            Command signature received from the kernel.
        args : list of str or None, optional
            Arguments forwarded together with the signature.

        Returns
        -------
        int
            The configured exit code.
        """
        self.calls.append((signature, args))
        return self.exit_code


class _StubApp:
    """Application double resolving the reactor contract."""

    __slots__ = ("reactor", "requested")

    def __init__(self, reactor: _RecordingReactor) -> None:
        """
        Store the reactor to hand out and the log of resolved contracts.

        Parameters
        ----------
        reactor : _RecordingReactor
            Instance returned by every ``make`` invocation.

        Returns
        -------
        None
        """
        self.reactor = reactor
        self.requested: list[object] = []

    async def make(self, abstract: object) -> _RecordingReactor:
        """
        Record a resolution request and return the reactor double.

        Parameters
        ----------
        abstract : object
            Contract the kernel asks the container for.

        Returns
        -------
        _RecordingReactor
            The reactor double held by this application.
        """
        self.requested.append(abstract)
        return self.reactor


async def boot_kernel(exit_code: int = 0) -> tuple[KernelCLI, _RecordingReactor]:
    """
    Build a kernel already booted against a recording reactor.

    Parameters
    ----------
    exit_code : int, optional
        Exit code reported by the recording reactor.

    Returns
    -------
    tuple of (KernelCLI, _RecordingReactor)
        The booted kernel and the reactor it dispatches to.
    """
    reactor = _RecordingReactor(exit_code)
    kernel = KernelCLI()
    await kernel.boot(_StubApp(reactor))  # type: ignore[arg-type]
    return kernel, reactor


class TestKernelCliDefinition(TestCase):

    def testImplementsTheKernelContract(self) -> None:
        """
        Implement the console kernel contract.

        Validates the class hierarchy the application relies on to resolve
        the CLI entry point.
        """
        self.assertTrue(issubclass(KernelCLI, IKernelCLI))
        self.assertIsInstance(KernelCLI(), IKernelCLI)

    def testDeclaresBothEntryPointsAsCoroutines(self) -> None:
        """
        Declare boot and handle as asynchronous methods.

        Validates that both entry points can await the reactor resolution
        and the command dispatch.
        """
        self.assertTrue(inspect.iscoroutinefunction(KernelCLI.boot))
        self.assertTrue(inspect.iscoroutinefunction(KernelCLI.handle))

    def testIgnoreFlagsHoldsTheInterpreterTokens(self) -> None:
        """
        Expose the ignored tokens as a frozen set.

        Validates the constant time membership check performed for every
        leading token of the argument list.
        """
        self.assertIsInstance(KernelCLI.IGNORE_FLAGS, frozenset)
        self.assertIn("reactor", KernelCLI.IGNORE_FLAGS)
        for flag in _INTERPRETER_FLAGS:
            self.assertIn(flag, KernelCLI.IGNORE_FLAGS)

    def testHelpFlagsHoldsTheThreeDocumentedTokens(self) -> None:
        """
        Expose the help tokens as a frozen set.

        Validates the exact set of tokens routed to the general listing.
        """
        self.assertIsInstance(KernelCLI._HELP_FLAGS, frozenset)
        self.assertEqual(KernelCLI._HELP_FLAGS, frozenset(_HELP_TOKENS))

    def testContractDeclaresEmptySlots(self) -> None:
        """
        Keep the contract free of instance storage.

        Validates the declaration that lets the implementation drop its
        instance dictionary.
        """
        self.assertEqual(IKernelCLI.__slots__, ())

    def testStoresTheReactorInASlot(self) -> None:
        """
        Store the reactor in a slot instead of an instance dictionary.

        Validates the memory layout required by the framework convention
        for stateful classes.
        """
        self.assertEqual(KernelCLI.__slots__, ("__reactor",))
        self.assertFalse(hasattr(KernelCLI(), "__dict__"))


class TestKernelCliBoot(TestCase):

    async def testResolvesTheReactorFromTheApplication(self) -> None:
        """
        Resolve the reactor contract through the application container.

        Validates that the kernel never builds a reactor by itself.
        """
        reactor = _RecordingReactor()
        app = _StubApp(reactor)
        kernel = KernelCLI()

        await kernel.boot(app)  # type: ignore[arg-type]

        self.assertEqual(app.requested, [IReactor])
        self.assertIs(kernel._KernelCLI__reactor, reactor)

    async def testDispatchesThroughTheReactorStoredAtBoot(self) -> None:
        """
        Dispatch commands through the reactor captured during boot.

        Validates that the instance stored by boot is the one receiving
        every later command.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["migrate"])

        self.assertEqual(reactor.calls, [("migrate", [])])


class TestKernelCliArgumentValidation(TestCase):

    async def testRejectsArgumentsThatAreNotAList(self) -> None:
        """
        Reject any argument container that is not a list.

        Validates that scalars and other iterables raise a descriptive
        TypeError before any command is dispatched.
        """
        kernel, reactor = await boot_kernel()

        for invalid in ("not-a-list", {"cmd": "test"}, 42):
            with self.assertRaises(TypeError) as captured:
                await kernel.handle(invalid)  # type: ignore[arg-type]
            self.assertEqual(str(captured.exception), _TYPE_ERROR_MESSAGE)

        self.assertEqual(reactor.calls, [])


class TestKernelCliHelpFallback(TestCase):

    async def testTreatsMissingArgumentsAsTheListingRequest(self) -> None:
        """
        Fall back to the listing when no argument is supplied.

        Validates that both the omitted and the empty argument list show
        the general help.
        """
        kernel, reactor = await boot_kernel()

        self.assertEqual(await kernel.handle(None), 0)
        self.assertEqual(await kernel.handle([]), 0)

        self.assertEqual(reactor.calls, [("list", None), ("list", None)])

    async def testTreatsEveryHelpTokenAsTheListingRequest(self) -> None:
        """
        Route every documented help token to the listing.

        Validates that the bare keyword and both flag spellings behave
        identically.
        """
        for token in _HELP_TOKENS:
            kernel, reactor = await boot_kernel()

            await kernel.handle([token])

            self.assertEqual(reactor.calls, [("list", None)])

    async def testFallsBackToTheListingWhenOnlyFlagsRemain(self) -> None:
        """
        Fall back to the listing when every token is stripped.

        Validates the empty argument list produced after removing the
        leading interpreter flags.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["-B", "-q"])

        self.assertEqual(reactor.calls, [("list", None)])

    async def testFallsBackToTheListingWhenOnlyTheScriptNameIsGiven(self) -> None:
        """
        Fall back to the listing when only the script name is supplied.

        Validates the empty argument list left after dropping the leading
        script token.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["reactor"])

        self.assertEqual(reactor.calls, [("list", None)])


class TestKernelCliDispatch(TestCase):

    async def testRoutesALoneCommandWithAnEmptyArgumentList(self) -> None:
        """
        Route a command that carries no trailing arguments.

        Validates that the reactor receives an empty list instead of None.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["migrate"])

        self.assertEqual(reactor.calls, [("migrate", [])])

    async def testForwardsTheRemainingTokensAsCommandArguments(self) -> None:
        """
        Forward every token after the signature as command arguments.

        Validates the split between the command signature and its own
        argument list.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["make:command", "Deploy", "--force"])

        self.assertEqual(reactor.calls, [("make:command", ["Deploy", "--force"])])

    async def testDropsTheScriptNameTokenBeforeRouting(self) -> None:
        """
        Drop a leading token that names the reactor script.

        Validates the entry point invoked as ``reactor <command>``.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["reactor", "migrate"])

        self.assertEqual(reactor.calls, [("migrate", [])])

    async def testDropsAScriptPathContainingTheReactorName(self) -> None:
        """
        Drop a leading token that embeds the reactor script path.

        Validates the entry point invoked through an absolute path, where
        the first token only contains the script name.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["/usr/local/bin/reactor", "migrate"])

        self.assertEqual(reactor.calls, [("migrate", [])])

    async def testStripsEveryLeadingInterpreterFlag(self) -> None:
        """
        Strip the whole run of leading interpreter flags.

        Validates that several ignored tokens in a row are removed in a
        single pass.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["-B", "-q", "serve", "--port=8000"])

        self.assertEqual(reactor.calls, [("serve", ["--port=8000"])])

    async def testStopsStrippingAtTheFirstCommandToken(self) -> None:
        """
        Stop stripping once a non ignored token is found.

        Validates that an ignored token placed after the signature is kept
        as a command argument.
        """
        kernel, reactor = await boot_kernel()

        await kernel.handle(["db:seed", "-B"])

        self.assertEqual(reactor.calls, [("db:seed", ["-B"])])

    async def testPropagatesTheExitCodeReturnedByTheReactor(self) -> None:
        """
        Propagate the exit code produced by the reactor.

        Validates the value the CLI entry point hands over to ``sys.exit``.
        """
        kernel, _ = await boot_kernel(exit_code=42)

        self.assertEqual(await kernel.handle(["failing:command"]), 42)

    async def testConsumesTheArgumentListItReceives(self) -> None:
        """
        Consume the received list in place while normalising it.

        Validates the documented side effect on ``sys.argv``, whose leading
        tokens are removed instead of copied.
        """
        kernel, reactor = await boot_kernel()
        argv = ["reactor", "-B", "serve"]

        await kernel.handle(argv)

        self.assertEqual(argv, ["serve"])
        self.assertEqual(reactor.calls, [("serve", [])])
