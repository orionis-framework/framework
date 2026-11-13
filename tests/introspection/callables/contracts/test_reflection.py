# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectionCallable contract against its implementation."""

import inspect
from abc import ABC
from orionis.introspection.callables.contracts.reflection import IReflectionCallable
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.test import TestCase


def _target(value: int = 1) -> int:
    """Return a value through a concrete callable target."""
    return value


class _Partial(IReflectionCallable):
    """Implement one operation while leaving the rest abstract."""

    def clearCache(self) -> None:
        """Implement one operation without completing the contract."""


class TestIReflectionCallable(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectionCallable, ABC))
        self.assertTrue(inspect.isabstract(IReflectionCallable))
        with self.assertRaises(TypeError):
            IReflectionCallable()
        with self.assertRaises(TypeError):
            _Partial()

    def testRequiredOperations(self) -> None:
        """Preserve the complete public abstract surface."""
        expected = {
            "getCallable",
            "getName",
            "getModuleName",
            "getModuleWithCallableName",
            "getDocstring",
            "getSourceCode",
            "getFile",
            "getSignature",
            "getDependencies",
            "clearCache",
        }
        self.assertEqual(IReflectionCallable.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectionCallable))
        reflected = ReflectionCallable(_target)
        self.assertIsInstance(reflected, IReflectionCallable)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectionCallable.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectionCallable, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectionCallable, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
