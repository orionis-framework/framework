# ruff: noqa: TC001
# Runtime handler annotations are inspected by the real container.
"""Provide isolated application handlers for runtime integration tests."""

from orionis.container.container import Container
from orionis.container.context.scope import reset_scope, set_current_scope
from functools import partial
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.entities.context import FailureContext
from orionis.failure.runtime import FailureRuntime, operation
from orionis.test import TestCase


class IsolatedFailureTestCase(TestCase):
    """Keep an isolated fixture outside the test command's runtime and DI scope."""

    def setUp(self) -> None:
        """
        Detach inherited runtime and scope state for this test only.

        Returns
        -------
        None
            Register restoration with unittest cleanup, including failed setup.
        """
        super().setUp()
        self.addCleanup(reset_scope, set_current_scope(None))
        self.enterContext(operation(runtime=FailureRuntime(None)))


class RecordingFailureHandler:
    """Record original failures and results without external logging services."""

    def __init__(self) -> None:
        """Create independent record lists for one runtime fixture."""
        self.failures: list[tuple[BaseException, FailureContext]] = []
        self.reports: list[BaseException] = []
        self.results: list[tuple[object, FailureContext]] = []
        self.rendered: list[BaseException] = []

    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling:
        """Select isolated logging and presentation for the original failure."""
        self.failures.append((exception, context))
        return FailureHandling(
            logging=(
                partial(self.log, exception)
                if not context.expected and context.reporting_allowed
                else None
            ),
            presentation=partial(self.present, exception),
        )

    async def log(self, exception: BaseException) -> None:
        """Record the selected logging effect without external dependencies."""
        self.reports.append(exception)

    async def handleResult(self, value: object, context: FailureContext) -> None:
        """Retain declared failures without manufacturing exceptions."""
        self.results.append((value, context))

    async def present(
        self,
        exception: BaseException,
        *,
        flow: str,
        request: object = None,
    ) -> object:
        """Record rendering separately and return the caller's HTTP response."""
        self.rendered.append(exception)
        return request if flow == "http" else None


def activate_runtime(app: object | None = None) -> tuple:
    """Activate a real coordinator on an isolated DI container for one test."""
    if app is None:
        app = object.__new__(Container)
        Container.__init__(app)
    handler = RecordingFailureHandler()
    runtime = FailureRuntime(app, handler)
    app._failure_runtime = runtime
    runtime.activate(object())
    return app, runtime, handler
