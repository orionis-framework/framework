# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify Catch's abstract surface and runtime-compatible implementation."""

import inspect

from orionis.container.container import Container
from orionis.failure.catch import Catch
from orionis.failure.contracts.catch import ICatch
from orionis.test import TestCase


class TestICatchContract(TestCase):
    """Keep optional capture and required presentation compatible."""

    def testAbstractSurfaceRequiresException(self) -> None:
        """Reject the interface and subclasses missing presentation."""
        self.assertEqual(ICatch.__abstractmethods__, frozenset({"exception"}))
        incomplete = type("IncompleteCatch", (ICatch,), {})
        for implementation in (ICatch, incomplete):
            with (
                self.subTest(implementation=implementation),
                self.assertRaises(TypeError),
            ):
                implementation()

    def testConcreteImplementationSatisfiesContract(self) -> None:
        """Construct the real Catch service with an isolated container."""
        app = object.__new__(Container)
        Container.__init__(app)
        self.assertIsInstance(Catch(app), ICatch)

    def testRuntimeAnnotationsPreserveImplementationParameters(self) -> None:
        """Resolve runtime type hints and retain public call parameters."""
        for name in ("capture", "exception"):
            with self.subTest(method=name):
                contract = inspect.signature(getattr(ICatch, name), eval_str=True)
                implementation = inspect.signature(getattr(Catch, name), eval_str=True)
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
