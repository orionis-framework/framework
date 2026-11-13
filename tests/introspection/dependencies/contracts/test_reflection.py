# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectDependencies contract against its implementation."""

import inspect
from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.introspection.dependencies.entities.signature import Signature
from orionis.introspection.dependencies.contracts.reflection import IReflectDependencies
from orionis.introspection.dependencies.reflection import ReflectDependencies
from orionis.test import TestCase


def _target(value: int = 1) -> int:
    """Return a value through a concrete callable target."""
    return value


class _Partial(IReflectDependencies):
    """Implement one operation while leaving the rest abstract."""

    def callableSignature(self) -> Signature:
        """Delegate callable reflection while leaving other operations abstract."""
        return ReflectDependencies(_target).callableSignature()


class TestIReflectDependencies(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectDependencies, ABC))
        self.assertTrue(inspect.isabstract(IReflectDependencies))
        with self.assertRaises(TypeError):
            IReflectDependencies()
        with self.assertRaises(TypeError):
            _Partial()

    def testRequiredOperations(self) -> None:
        """Preserve the complete public abstract surface."""
        expected = {
            "constructorSignature",
            "methodSignature",
            "callableSignature",
        }
        self.assertEqual(IReflectDependencies.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectDependencies))
        reflected = ReflectDependencies(_target)
        self.assertIsInstance(reflected, IReflectDependencies)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectDependencies.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectDependencies, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectDependencies, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
