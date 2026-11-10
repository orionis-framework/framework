"""Keep custom failure handlers limited to the two observation entry points."""

from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.test import TestCase


class TestIBaseExceptionHandlerContract(TestCase):
    """Verify migration does not require legacy logging or transport hooks."""

    async def testCustomHandlerRequiresOnlyTwoObservationHooks(self) -> None:
        """A direct implementation can return plans without inheriting Base."""
        recorded = []

        class Handler(IBaseExceptionHandler):
            async def handleFailure(self, exception, context):
                recorded.append((exception, context))
                return FailureHandling()

            async def handleResult(self, value, context):
                recorded.append((value, context))

        handler = Handler()
        context = FailureContext(flow="queue")
        error = ValueError("original")
        self.assertIsInstance(
            await handler.handleFailure(error, context), FailureHandling,
        )
        self.assertIsNone(await handler.handleResult(7, context))
        self.assertEqual(recorded, [(error, context), (7, context)])
        self.assertEqual(
            IBaseExceptionHandler.__abstractmethods__,
            {"handleFailure", "handleResult"},
        )

    def testIncompleteHandlerCannotBeInstantiated(self) -> None:
        """Both exceptions and explicit failed results require a policy hook."""
        class Handler(IBaseExceptionHandler):
            async def handleFailure(self, _exception, _context):
                return None

        with self.assertRaises(TypeError):
            Handler()

    def testRemovedHooksCannotReenterTheHandler(self) -> None:
        """Neither the contract nor Base retains obsolete invocation paths."""
        for handler in (IBaseExceptionHandler, BaseExceptionHandler):
            for name in ("report", "handleHTTP", "handleCLI"):
                with self.subTest(handler=handler, name=name):
                    self.assertFalse(hasattr(handler, name))
