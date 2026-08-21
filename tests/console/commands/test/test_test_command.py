from typing import Self
from orionis.console.commands.test.test_command import TestCommand
from orionis.test import TestCase
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus

# Exit codes published by the command.
_SUCCESS: int = 0
_FAILURE: int = 1

class _StubApp:
    """Application double exposing only the configuration reader."""

    __slots__ = ("_config",)

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self._config: dict[str, object] = config or {}

    def config(self, key: str) -> object:
        """Return the configured value, or None when the key is unknown."""
        return self._config.get(key)

class _RecordingEngine:
    """Testing engine double recording every option applied to it."""

    __slots__ = ("applied", "results")

    def __init__(self, results: list[TestResult] | None = None) -> None:
        self.applied: dict[str, object] = {}
        self.results: list[TestResult] = results or []

    def setVerbosity(self, verbosity: int) -> Self:
        """Record the requested verbosity."""
        self.applied["verbosity"] = verbosity
        return self

    def setFailFast(self, *, fail_fast: bool) -> Self:
        """Record the requested fail fast behaviour."""
        self.applied["fail_fast"] = fail_fast
        return self

    def setStartDir(self, start_dir: str) -> Self:
        """Record the requested discovery directory."""
        self.applied["start_dir"] = start_dir
        return self

    def setFilePattern(self, file_pattern: str) -> Self:
        """Record the requested file pattern."""
        self.applied["file_pattern"] = file_pattern
        return self

    def setMethodPattern(self, method_pattern: str) -> Self:
        """Record the requested method pattern."""
        self.applied["method_pattern"] = method_pattern
        return self

    def withoutPanel(self) -> Self:
        """Record that the panels were disabled."""
        self.applied["with_panel"] = False
        return self

    def discover(self) -> None:
        """Return nothing; discovery is not exercised by these scenarios."""
        return

    async def run(self) -> list[TestResult]:
        """Return the predefined reports."""
        return self.results

def _make_result(status: TestStatus) -> TestResult:
    """Build a report carrying the given status."""
    return TestResult(
        id=1,
        name="probe",
        status=status,
        execution_time=0.0,
    )

def _make_command(arguments: dict[str, object] | None = None) -> TestCommand:
    """Build a command instance holding the given parsed arguments."""
    command = TestCommand()
    command.setArguments(arguments or {})
    return command

# Configuration equivalent to a fully declared testing section.
_FULL_CONFIG: dict[str, object] = {
    "testing.verbosity": 2,
    "testing.fail_fast": False,
    "testing.start_dir": "tests",
    "testing.file_pattern": "test_*.py",
    "testing.method_pattern": "test*",
}

class TestTestCommandDefinition(TestCase):

    def testSignatureAndDescriptionAreDeclared(self) -> None:
        """
        Publish the signature consumed by the reactor.

        Validates that the command stays reachable as `reactor test`.
        """
        self.assertEqual(TestCommand.signature, "test")
        self.assertTrue(TestCommand.description)

    def testEveryEngineOptionHasAFlag(self) -> None:
        """
        Expose one flag per option supported by the engine.

        Validates that the command surface matches the engine contract.
        """
        destinations = {argument.dest for argument in TestCommand.arguments}
        self.assertEqual(
            destinations,
            {
                "verbosity",
                "fail_fast",
                "start_dir",
                "file_pattern",
                "method_pattern",
                "with_panel",
            },
        )

class TestTestCommandExitCode(TestCase):

    async def testPassingReportsReturnSuccess(self) -> None:
        """
        Report success when every test passed or was skipped.

        Validates the exit code consumed by continuous integration.
        """
        engine = _RecordingEngine([
            _make_result(TestStatus.PASSED),
            _make_result(TestStatus.SKIPPED),
        ])
        command = _make_command()
        code = await command.handle(_StubApp(_FULL_CONFIG), engine)
        self.assertEqual(code, _SUCCESS)

    async def testFailedReportReturnsFailure(self) -> None:
        """
        Report failure when an assertion did not hold.

        Validates that a failing suite never looks successful.
        """
        engine = _RecordingEngine([_make_result(TestStatus.FAILED)])
        command = _make_command()
        code = await command.handle(_StubApp(_FULL_CONFIG), engine)
        self.assertEqual(code, _FAILURE)

    async def testErroredReportReturnsFailure(self) -> None:
        """
        Report failure when a test raised an unexpected exception.

        Validates that errored outcomes are not mistaken for successful
        runs, which happens when statuses are compared as free text.
        """
        engine = _RecordingEngine([_make_result(TestStatus.ERRORED)])
        command = _make_command()
        code = await command.handle(_StubApp(_FULL_CONFIG), engine)
        self.assertEqual(code, _FAILURE)

    async def testEmptyReportReturnsSuccess(self) -> None:
        """
        Report success when the run produced no test at all.

        Validates that an empty suite is a supported outcome.
        """
        command = _make_command()
        code = await command.handle(_StubApp(_FULL_CONFIG), _RecordingEngine())
        self.assertEqual(code, _SUCCESS)

class TestTestCommandOptionResolution(TestCase):

    async def _apply(
        self,
        arguments: dict[str, object] | None = None,
        config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run the command and return the options applied to the engine."""
        engine = _RecordingEngine()
        await _make_command(arguments).handle(_StubApp(config), engine)
        return engine.applied

    async def testConfigurationValuesReachTheEngine(self) -> None:
        """
        Apply the configured options when no flag is supplied.

        Validates the default path of a plain `reactor test` invocation.
        """
        applied = await self._apply(config=_FULL_CONFIG)
        self.assertEqual(applied["verbosity"], 2)
        self.assertEqual(applied["start_dir"], "tests")
        self.assertEqual(applied["file_pattern"], "test_*.py")
        self.assertEqual(applied["method_pattern"], "test*")

    async def testCommandLineValuesOverrideTheConfiguration(self) -> None:
        """
        Prefer the flags supplied on the command line.

        Validates that a run can be narrowed without touching the
        configuration files.
        """
        applied = await self._apply(
            arguments={
                "verbosity": 1,
                "start_dir": "tests/app",
                "file_pattern": "check_*.py",
                "method_pattern": "check*",
            },
            config=_FULL_CONFIG,
        )
        self.assertEqual(applied["verbosity"], 1)
        self.assertEqual(applied["start_dir"], "tests/app")
        self.assertEqual(applied["file_pattern"], "check_*.py")
        self.assertEqual(applied["method_pattern"], "check*")

    async def testSilentVerbosityIsForwarded(self) -> None:
        """
        Forward the silent level even though it is a falsy value.

        Validates that zero is treated as a requested level.
        """
        applied = await self._apply(arguments={"verbosity": 0})
        self.assertEqual(applied["verbosity"], 0)

    async def testMissingOptionsKeepTheEngineDefaults(self) -> None:
        """
        Leave the engine untouched when nothing resolves an option.

        Validates that an absent testing section never overwrites the
        defaults the engine already computed.
        """
        applied = await self._apply()
        self.assertNotIn("verbosity", applied)
        self.assertNotIn("start_dir", applied)
        self.assertNotIn("file_pattern", applied)
        self.assertNotIn("method_pattern", applied)

    async def testInvalidVerbosityIsRejected(self) -> None:
        """
        Reject verbosity levels outside the supported range.

        Validates that a typo never reaches the result processor.
        """
        with self.assertRaises(ValueError):
            await self._apply(arguments={"verbosity": 7})

    async def testFailFastFlagEnablesTheEarlyExit(self) -> None:
        """
        Enable the early exit when the flag requests it.

        Validates the documented truthy representations.
        """
        applied = await self._apply(arguments={"fail_fast": 1})
        self.assertIs(applied["fail_fast"], True)

    async def testFailFastFlagOverridesAnEnabledConfiguration(self) -> None:
        """
        Disable the early exit when the flag explicitly asks for it.

        Validates that a falsy flag is not mistaken for a missing one.
        """
        applied = await self._apply(
            arguments={"fail_fast": 0},
            config={"testing.fail_fast": True},
        )
        self.assertIs(applied["fail_fast"], False)

    async def testFailFastDefaultsToDisabled(self) -> None:
        """
        Keep the early exit disabled when nothing configures it.

        Validates the conservative default of a plain invocation.
        """
        applied = await self._apply()
        self.assertIs(applied["fail_fast"], False)

    async def testPanelsStayEnabledByDefault(self) -> None:
        """
        Render the decorative panels unless they are disabled.

        Validates the default presentation of the command.
        """
        applied = await self._apply(arguments={"with_panel": True})
        self.assertNotIn("with_panel", applied)

    async def testNoPanelFlagDisablesThePanels(self) -> None:
        """
        Disable the decorative panels when the flag requests it.

        Validates the option used by embedded or piped runs.
        """
        applied = await self._apply(arguments={"with_panel": False})
        self.assertIs(applied["with_panel"], False)
