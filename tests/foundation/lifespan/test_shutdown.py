from io import StringIO
from orionis.foundation.lifespan import shutdown
from orionis.test import TestCase
from tests.foundation.lifespan.test_startup import (
    _ImmediateConsole,
    _LifespanApplication,
)

class TestShutdownDisplay(TestCase):
    def setUp(self) -> None:
        """Capture shutdown output without entering an alternate screen.

        Returns
        -------
        None
            Install an independent recording console.
        """
        self.output = StringIO()
        self.original_console = shutdown._console
        shutdown._console = _ImmediateConsole(file=self.output, width=100)

    def tearDown(self) -> None:
        """Restore the process console after each test.

        Returns
        -------
        None
            Leave the runtime console unchanged for other tests.
        """
        shutdown._console = self.original_console

    def testShutdownPanelRemainsVisibleWithoutATimedScreen(self) -> None:
        """Print the stopping panel directly to the lifecycle console.

        Returns
        -------
        None
            The shutdown message is present without using a splash screen.
        """
        shutdown.before_shutdown_orionis_generator()
        self.assertIn("Stopping Orionis server", self.output.getvalue())

    def testGeneratorPreservesTheUptimeSummary(self) -> None:
        """Print the uptime summary only after shutdown hooks complete.

        Returns
        -------
        None
            Display order remains paired with the lifecycle generator.
        """
        generator = shutdown.shutdown_orionis_generator(_LifespanApplication())
        self.assertIsNone(next(generator))
        self.assertIn("Stopping Orionis server", self.output.getvalue())
        self.assertNotIn("Server Uptime", self.output.getvalue())
        with self.assertRaises(StopIteration):
            next(generator)
        self.assertIn("Server Uptime", self.output.getvalue())

    def testProductionAndDisabledDebugRemainSilent(self) -> None:
        """Suppress shutdown display when the runtime policy disables it.

        Returns
        -------
        None
            Production and non-debug shutdown produce no console output.
        """
        for app in (
            _LifespanApplication(debug=False),
            _LifespanApplication(production=True),
        ):
            generator = shutdown.shutdown_orionis_generator(app)
            next(generator)
            with self.assertRaises(StopIteration):
                next(generator)
        self.assertEqual(self.output.getvalue(), "")
