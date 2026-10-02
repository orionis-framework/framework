import time
from io import StringIO
from typing import Never
from rich.console import Console
from orionis.foundation.lifespan import startup
from orionis.test import TestCase

class _ImmediateConsole(Console):
    __slots__ = ()

    def screen(self, *_args: object, **_kwargs: object) -> Never:
        """Reject timed alternate-screen splash panels.

        Returns
        -------
        Never
            Never enter an alternate-screen context.

        Raises
        ------
        AssertionError
            If a lifecycle panel attempts to use a timed splash screen.
        """
        message = "Lifecycle panels must remain visible while hooks run."
        raise AssertionError(message)

class _LifespanApplication:
    __slots__ = ("_debug", "_production", "_start_at")

    def __init__(self, *, debug: bool = True, production: bool = False) -> None:
        """Store the lifecycle display policy and startup timestamp.

        Parameters
        ----------
        debug : bool, optional
            Enable lifecycle display in non-production environments.
        production : bool, optional
            Suppress display in production.

        Returns
        -------
        None
            Initialize an independent display policy.
        """
        self._debug = debug
        self._production = production
        self._start_at = time.time_ns()

    def isDebug(self) -> bool:
        """Return the configured debug flag.

        Returns
        -------
        bool
            Whether debug display is enabled.
        """
        return self._debug

    def isProduction(self) -> bool:
        """Return the configured production flag.

        Returns
        -------
        bool
            Whether production display rules apply.
        """
        return self._production

    @property
    def startAt(self) -> int:
        """Return the recorded startup timestamp.

        Returns
        -------
        int
            Startup epoch in nanoseconds.
        """
        return self._start_at

class TestStartupDisplay(TestCase):
    def setUp(self) -> None:
        """Capture lifecycle output without entering an alternate screen.

        Returns
        -------
        None
            Install an independent recording console.
        """
        self.output = StringIO()
        self.original_console = startup._console
        startup._console = _ImmediateConsole(file=self.output, width=100)

    def tearDown(self) -> None:
        """Restore the process console after each test.

        Returns
        -------
        None
            Leave the runtime console unchanged for other tests.
        """
        startup._console = self.original_console

    def testStartupPanelRemainsVisibleWithoutATimedScreen(self) -> None:
        """Print the initial panel directly to the lifecycle console.

        Returns
        -------
        None
            The startup message is present without using a splash screen.
        """
        startup.before_startup_orionis_generator()
        self.assertIn("Starting the Orionis server", self.output.getvalue())

    def testGeneratorPreservesBothDisplayPhases(self) -> None:
        """Display the initial message before yielding and readiness afterward.

        Returns
        -------
        None
            Display order remains paired with the lifecycle generator.
        """
        generator = startup.startup_orionis_generator(_LifespanApplication())
        self.assertIsNone(next(generator))
        self.assertIn("Starting the Orionis server", self.output.getvalue())
        self.assertNotIn("has started successfully", self.output.getvalue())
        with self.assertRaises(StopIteration):
            next(generator)
        self.assertIn("has started successfully", self.output.getvalue())

    def testProductionAndDisabledDebugRemainSilent(self) -> None:
        """Suppress both panels when runtime policy disables lifecycle display.

        Returns
        -------
        None
            Production and non-debug startup produce no console output.
        """
        for app in (
            _LifespanApplication(debug=False),
            _LifespanApplication(production=True),
        ):
            generator = startup.startup_orionis_generator(app)
            next(generator)
            with self.assertRaises(StopIteration):
                next(generator)
        self.assertEqual(self.output.getvalue(), "")
