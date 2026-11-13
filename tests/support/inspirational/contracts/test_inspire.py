# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify the inspirational service's runtime contract."""

import inspect
from abc import ABC

from orionis.support.inspirational.contracts.inspire import IInspire
from orionis.support.inspirational.inspire import Inspire
from orionis.test import TestCase


class TestIInspireContract(TestCase):
    """Exercise abstract enforcement and the actual implementation."""

    def testAbstractSurfaceRequiresRandom(self) -> None:
        """Reject the contract and subclasses missing the random implementation."""
        self.assertTrue(issubclass(IInspire, ABC))
        self.assertEqual(IInspire.__abstractmethods__, frozenset({"random"}))
        incomplete = type("IncompleteInspire", (IInspire,), {})
        for implementation in (IInspire, incomplete):
            with (
                self.subTest(implementation=implementation),
                self.assertRaises(TypeError),
            ):
                implementation()

    def testConcreteImplementationSatisfiesContract(self) -> None:
        """Instantiate the real service and return its single supplied quote."""
        quote = {"quote": "A test quote.", "author": "Test author"}
        service = Inspire([quote])
        self.assertIsInstance(service, IInspire)
        self.assertEqual(service.random(), quote)

    def testRuntimeSignatureMatchesImplementation(self) -> None:
        """Resolve the contract annotations and preserve its callable signature."""
        signature = inspect.signature(IInspire.random, eval_str=True)
        self.assertEqual(list(signature.parameters), ["self"])
        self.assertIs(signature.return_annotation, dict)
        self.assertEqual(inspect.signature(Inspire.random, eval_str=True), signature)
