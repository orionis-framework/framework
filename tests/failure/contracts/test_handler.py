# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Keep custom failure handlers limited to the two observation entry points."""

import inspect
from typing import TYPE_CHECKING

from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.failure.entities.context import FailureContext
    from orionis.failure.entities.handling import FailureHandling


class TestIBaseExceptionHandlerContract(TestCase):
    """Verify migration does not require legacy logging or transport hooks."""

    def testTwoObservationHooksDefineTheContract(self) -> None:
        """Require exactly two hooks and accept the real concrete implementation."""
        self.assertEqual(
            IBaseExceptionHandler.__abstractmethods__,
            {"handleFailure", "handleResult"},
        )
        with self.assertRaises(TypeError):
            IBaseExceptionHandler()
        self.assertTrue(issubclass(BaseExceptionHandler, IBaseExceptionHandler))
        self.assertEqual(BaseExceptionHandler.__abstractmethods__, frozenset())

    def testIncompleteHandlerCannotBeInstantiated(self) -> None:
        """Verify incomplete handler cannot be instantiated.

        Both exceptions and explicit failed results require a policy hook.
        """

        class Handler(IBaseExceptionHandler):
            async def handleFailure(
                self,
                _exception: BaseException,
                _context: FailureContext,
            ) -> FailureHandling | None:
                """Select or fail the configured exception policy for this scenario.

                Parameters
                ----------
                _exception : BaseException
                    Original exception supplied to the callback.
                _context : FailureContext
                    Immutable failure metadata supplied by the runtime.
                """
                return None

        with self.assertRaises(TypeError):
            Handler()

    def testLegacyHooksRemainConcreteCompatibilityMethods(self) -> None:
        """Retain legacy calls without requiring them from new implementations."""
        for name in ("report", "handleHTTP", "handleCLI"):
            with self.subTest(method=name):
                self.assertFalse(hasattr(IBaseExceptionHandler, name))
                self.assertTrue(
                    inspect.iscoroutinefunction(getattr(BaseExceptionHandler, name)),
                )

    def testRuntimeAnnotationsPreserveImplementationParameters(self) -> None:
        """Resolve runtime type hints and retain public call parameters."""
        for name in ("handleFailure", "handleResult"):
            with self.subTest(method=name):
                contract = inspect.signature(
                    getattr(IBaseExceptionHandler, name),
                    eval_str=True,
                )
                implementation = inspect.signature(
                    getattr(BaseExceptionHandler, name),
                    eval_str=True,
                )
                self.assertIsNot(contract.return_annotation, inspect.Signature.empty)
                self.assertIsNot(
                    implementation.return_annotation,
                    inspect.Signature.empty,
                )
                self.assertEqual(
                    [(p.name, p.kind, p.default) for p in contract.parameters.values()],
                    [
                        (p.name, p.kind, p.default)
                        for p in implementation.parameters.values()
                    ],
                )
