from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.enums.actions import ArgumentAction
from orionis.foundation.contracts.application import IApplication
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.enums.status import TestStatus

# Values considered truthy for boolean CLI/config arguments
_TRUTHY_VALUES: frozenset = frozenset({1, "1", "true", "True"})

# Valid verbosity levels accepted by the test runner
_VALID_VERBOSITY: frozenset = frozenset({0, 1, 2})

# Test result statuses that indicate a non-passing outcome
_FAILURE_STATUSES: frozenset[TestStatus] = frozenset({
    TestStatus.FAILED,
    TestStatus.ERRORED,
})

class TestCommand(BaseCommand):

    # ruff: noqa: TC001

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "test"

    # Command description
    description: str = "Executes test cases defined in the project."

    # List of Argument instances defining command-line options and arguments
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--verbosity", "-v"],
            type_=int,
            required=False,
            help=(
                "Level of detail in test output. 0: silent, 1: standard, "
                "2: detailed. Defaults to 2 (detailed)."
            ),
            dest="verbosity",
        ),
        Argument(
            name_or_flags=["--fail-fast", "-f"],
            type_=int,
            required=False,
            help=(
                "1: Stop on first failure. 0: Continue running all tests. "
                "Defaults to 0 (continue)."
            ),
            dest="fail_fast",
        ),
        Argument(
            name_or_flags=["--start-dir", "-s"],
            type_=str,
            required=False,
            help=(
                "Directory to search for tests. Defaults to 'tests'."
            ),
            dest="start_dir",
        ),
        Argument(
            name_or_flags=["--file-pattern"],
            type_=str,
            required=False,
            help=(
                "Filename pattern to identify test files. Defaults to 'test_*.py'."
            ),
            dest="file_pattern",
        ),
        Argument(
            name_or_flags=["--method-pattern"],
            type_=str,
            required=False,
            help=(
                "Pattern to filter specific test methods. Defaults to 'test*'."
            ),
            dest="method_pattern",
        ),
        Argument(
            name_or_flags=["--panel"],
            action=ArgumentAction.STORE_TRUE,
            default=True,
            help="Show Rich panels for test execution (default).",
            dest="with_panel",
        ),
        Argument(
            name_or_flags=["--no-panel"],
            action=ArgumentAction.STORE_FALSE,
            help="Disable Rich panels for test execution.",
            dest="with_panel",
        ),
    ]

    def __resolveVerbosity(self, cli_value: object, app: IApplication) -> int | None:
        """
        Resolve the verbosity level requested for this run.

        Parameters
        ----------
        cli_value : object
            Value supplied through the --verbosity flag, or None when absent.
        app : IApplication
            Application instance providing the configured fallback.

        Returns
        -------
        int | None
            The validated verbosity level, or None when neither the CLI nor
            the configuration provide one.

        Raises
        ------
        ValueError
            If the resolved verbosity is not 0, 1 or 2.
        """
        # Fall back to the application configuration when the flag is absent
        verbosity = cli_value
        if verbosity is None:
            verbosity = app.config("testing.verbosity")

        # Leave the decision to the engine when nothing was configured
        if verbosity is None:
            return None

        # Ensure verbosity is an integer and validate its value
        verbosity = int(verbosity)
        if verbosity not in _VALID_VERBOSITY:
            error_message = (
                "Invalid verbosity level. Allowed values are 0 (silent), "
                "1 (standard), 2 (detailed)."
            )
            raise ValueError(error_message)

        return verbosity

    async def handle(
        self,
        app: IApplication,
        test_engine: ITestingEngine,
    ) -> int:
        """
        Execute the test command with configured parameters.

        Every option resolves from the CLI first and from the application
        configuration afterwards. An option that resolves to nothing is left
        untouched so the engine keeps the default it already computed.

        Parameters
        ----------
        app : IApplication
            Application instance providing configuration and context.
        test_engine : ITestingEngine
            Testing engine resolved by the container and driven by this command.

        Returns
        -------
        int
            Exit code indicating success (0) or failure (1).

        Raises
        ------
        ValueError
            If the resolved verbosity is not 0, 1 or 2.
        """
        # Retrieve all parsed command-line arguments
        cli_args: dict = self.getArguments()
        _get = cli_args.get

        # Resolve verbosity from CLI args or fall back to the app configuration
        verbosity = self.__resolveVerbosity(_get("verbosity"), app)
        if verbosity is not None:
            test_engine.setVerbosity(verbosity)

        # Resolve fail_fast from CLI args or fall back to the app configuration.
        # The CLI wins even when it supplies a falsy value such as --fail-fast=0.
        fail_fast = _get("fail_fast")
        if fail_fast is None:
            fail_fast = app.config("testing.fail_fast")
        test_engine.setFailFast(fail_fast=fail_fast in _TRUTHY_VALUES)

        # Resolve the test discovery directory from CLI args or app configuration
        start_dir = _get("start_dir") or app.config("testing.start_dir")
        if start_dir:
            test_engine.setStartDir(start_dir)

        # Resolve the file pattern for test discovery from CLI args or app configuration
        file_pattern = _get("file_pattern") or app.config("testing.file_pattern")
        if file_pattern:
            test_engine.setFilePattern(file_pattern)

        # Resolve the method pattern for test filtering from CLI args or app config
        method_pattern = _get("method_pattern") or app.config("testing.method_pattern")
        if method_pattern:
            test_engine.setMethodPattern(method_pattern)

        # The parser always resolves this flag through --panel / --no-panel
        if _get("with_panel") is False:
            test_engine.withoutPanel()

        # Run the tests and collect results
        results = await test_engine.run()

        # Return 1 if any result indicates a failure or error, otherwise 0
        for result in results:
            if result.status in _FAILURE_STATUSES:
                return 1

        return 0
